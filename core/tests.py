from datetime import date
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase, Client
from django.urls import reverse

from .models import Driver, DriverEmploymentPeriod
from .pagination import PaginationResult, paginate_queryset
from .ratelimit import check_rate_limit, get_client_ip, parse_rate, ratelimit
from .templatetags.pagination_tags import url_replace


class WorkforceTests(TestCase):
    def test_driver_can_have_separate_historical_rehire_periods(self):
        driver = Driver.objects.create(name='Arun Kumar')
        first = DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2023, 9, 1), left_on=date(2024, 11, 30))
        second = DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2025, 9, 1))
        self.assertEqual(driver.employment_periods.count(), 2)
        self.assertEqual(str(first), 'Arun Kumar (2023-09-01 - 2024-11-30)')
        with self.assertRaises(ValidationError):
            DriverEmploymentPeriod.objects.create(driver=driver, joined_on=date(2026, 1, 1)).full_clean()


class PaginationEngineTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.sample_data = list(range(1, 101))  # 100 items

    def test_paginate_queryset_basic(self):
        request = self.factory.get('/items/?page=1&page_size=10')
        result = paginate_queryset(self.sample_data, request, default_page_size=10)
        self.assertEqual(result.total_count, 100)
        self.assertEqual(result.total_pages, 10)
        self.assertEqual(result.current_page, 1)
        self.assertTrue(result.has_next)
        self.assertFalse(result.has_previous)
        self.assertEqual(len(result.records), 10)
        self.assertEqual(result.records[0], 1)
        self.assertEqual(result.records[-1], 10)

    def test_paginate_queryset_out_of_bounds_page_returns_last_page(self):
        request = self.factory.get('/items/?page=999&page_size=10')
        result = paginate_queryset(self.sample_data, request, default_page_size=10)
        self.assertEqual(result.current_page, 10)
        self.assertFalse(result.has_next)
        self.assertTrue(result.has_previous)
        self.assertEqual(result.records[-1], 100)

    def test_paginate_queryset_invalid_page_defaults_to_first(self):
        request = self.factory.get('/items/?page=invalid_string&page_size=10')
        result = paginate_queryset(self.sample_data, request, default_page_size=10)
        self.assertEqual(result.current_page, 1)

    def test_paginate_queryset_max_page_size_capping(self):
        request = self.factory.get('/items/?page_size=5000')
        result = paginate_queryset(self.sample_data, request, default_page_size=10, max_page_size=50)
        self.assertEqual(result.page_size, 50)
        self.assertEqual(len(result.records), 50)

    def test_pagination_result_page_range_with_ellipsis(self):
        # Middle page in 10 pages -> ellipsis on both sides
        request = self.factory.get('/items/?page=5&page_size=10')
        result = paginate_queryset(self.sample_data, request, default_page_size=10)
        expected_range = [1, '...', 3, 4, 5, 6, 7, '...', 10]
        self.assertEqual(result.page_range, expected_range)

    def test_pagination_result_as_dict(self):
        request = self.factory.get('/items/?page=2&page_size=5')
        result = paginate_queryset(self.sample_data, request, default_page_size=5)
        api_dict = result.as_dict()
        self.assertTrue(api_dict["success"])
        self.assertEqual(api_dict["pagination"]["count"], 100)
        self.assertEqual(api_dict["pagination"]["current_page"], 2)
        self.assertEqual(api_dict["pagination"]["page_size"], 5)
        self.assertEqual(api_dict["pagination"]["total_pages"], 20)
        self.assertEqual(len(api_dict["results"]), 5)


class PaginationTemplateTagsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_url_replace_preserves_query_params(self):
        request = self.factory.get('/bookings/?status=confirmed&tab=fleet&page=1')
        context = {'request': request}
        output = url_replace(context, page=3)
        self.assertIn('status=confirmed', output)
        self.assertIn('tab=fleet', output)
        self.assertIn('page=3', output)

    def test_url_replace_removes_empty_params(self):
        request = self.factory.get('/bookings/?status=confirmed&tab=fleet&page=1')
        context = {'request': request}
        output = url_replace(context, tab='', page=2)
        self.assertIn('status=confirmed', output)
        self.assertIn('page=2', output)
        self.assertNotIn('tab=', output)

    def test_url_replace_no_request_in_context(self):
        context = {}
        output = url_replace(context, page=5, sort='date')
        self.assertIn('page=5', output)
        self.assertIn('sort=date', output)


class RateLimiterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def tearDown(self):
        cache.clear()

    def test_parse_rate(self):
        self.assertEqual(parse_rate('60/m'), (60, 60))
        self.assertEqual(parse_rate('5/s'), (5, 1))
        self.assertEqual(parse_rate('100/h'), (100, 3600))
        self.assertEqual(parse_rate('1000/d'), (1000, 86400))
        with self.assertRaises(ValueError):
            parse_rate('invalid_format')
        with self.assertRaises(ValueError):
            parse_rate('100/unknown_unit')

    def test_get_client_ip(self):
        # Direct REMOTE_ADDR
        req1 = self.factory.get('/')
        req1.META['REMOTE_ADDR'] = '192.168.1.10'
        self.assertEqual(get_client_ip(req1), '192.168.1.10')

        # Forwarded for reverse proxy
        req2 = self.factory.get('/')
        req2.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.195, 70.41.3.18, 150.172.238.178'
        self.assertEqual(get_client_ip(req2), '203.0.113.195')

        # Real IP header
        req3 = self.factory.get('/')
        req3.META['HTTP_X_REAL_IP'] = '198.51.100.44'
        self.assertEqual(get_client_ip(req3), '198.51.100.44')

    def test_check_rate_limit_allows_and_throttles(self):
        key = 'user_test_bucket_123'
        rate = '3/m'

        # 1st request
        limited, count, limit, retry = check_rate_limit(key, rate)
        self.assertFalse(limited)
        self.assertEqual(count, 1)

        # 2nd request
        limited, count, limit, retry = check_rate_limit(key, rate)
        self.assertFalse(limited)
        self.assertEqual(count, 2)

        # 3rd request (at limit)
        limited, count, limit, retry = check_rate_limit(key, rate)
        self.assertFalse(limited)
        self.assertEqual(count, 3)

        # 4th request (exceeds limit)
        limited, count, limit, retry = check_rate_limit(key, rate)
        self.assertTrue(limited)
        self.assertEqual(count, 4)

    def test_ratelimit_decorator_blocks_requests(self):
        @ratelimit(rate='2/m', key='ip', block=True)
        def sample_view(request):
            return JsonResponse({'message': 'ok'})

        req = self.factory.get('/test/')
        req.META['REMOTE_ADDR'] = '10.0.0.99'

        res1 = sample_view(req)
        self.assertEqual(res1.status_code, 200)

        res2 = sample_view(req)
        self.assertEqual(res2.status_code, 200)

        # 3rd request from same IP should get HTTP 429 Too Many Requests
        res3 = sample_view(req)
        self.assertEqual(res3.status_code, 429)


class ApiDocsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_api_docs_view_status_200(self):
        url = reverse('api-docs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/api_docs.html')
        self.assertIn('categories', response.context)
        self.assertGreater(response.context['total_endpoints'], 0)

    def test_api_schema_json_view(self):
        url = reverse('api-docs-schema')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data.get('openapi'), '3.0.3')
        self.assertIn('info', data)
        self.assertIn('endpoints', data)
        self.assertIsInstance(data['endpoints'], list)
        self.assertGreater(len(data['endpoints']), 0)


class ModularizedRoutingTests(TestCase):
    def test_modular_routes_reverse_correctly(self):
        expected_mappings = {
            'api-docs': '/docs/',
            'api-docs-alias': '/api/docs/',
            'api-schema-json': '/api/docs/schema.json',
            'api-docs-schema': '/api/docs/schema.json',
            'fleet-vehicles-roster': '/fleet/vehicles/',
            'client-pricing-studio': '/pricing/',
            'dispatch-console': '/dispatch/',
            'booking-list': '/bookings/',
            'booking-create': '/bookings/create/',
            'operations-whatsapp-bot': '/operations/whatsapp-bot/',
            'operations-border-permits': '/operations/border-permits/',
            'fleet-live': '/fleet/live/',
        }
        for name, expected_path in expected_mappings.items():
            reversed_path = reverse(name)
            self.assertEqual(reversed_path, expected_path, f"Route name '{name}' failed reversal.")


class ResetSequencesCommandTests(TestCase):
    def test_reset_sequences_command_executes_successfully(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('reset_sequences', stdout=out)
        output = out.getvalue()
        self.assertTrue('aligned' in output or 'only required for PostgreSQL' in output or 'sequences found' in output)
