from django.urls import path
from . import htmx_views

app_name = 'htmx_packages'

urlpatterns = [
    path('category-intel/', htmx_views.package_category_intel, name='category-intel'),
    path('unit-economics/', htmx_views.package_unit_economics, name='unit-economics'),
    path('tariff-calculate/', htmx_views.package_tariff_calculate, name='tariff-calculate'),
    path('whatsapp-briefing/', htmx_views.package_whatsapp_briefing, name='whatsapp-briefing'),
    path('proposal-preview/', htmx_views.package_proposal_preview_modal, name='proposal-preview'),
]
