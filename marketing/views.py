import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum

from .models import PromotionCampaign, Coupon, EmailCampaign
from .campaign_engine import (
    CAMPAIGN_TEMPLATES,
    get_audience_recipients,
    generate_campaign_dispatches
)


@staff_member_required
def campaign_studio_view(request):
    """
    Marketing & Promotions Campaign Control Studio:
    Broadcast seasonal offers to past tourists, corporate managers, and cold CRM leads.
    """
    campaigns = PromotionCampaign.objects.select_related('coupon').order_by('-created_at')

    # Metrics
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(status='active').count()
    coupons = Coupon.objects.filter(is_active=True).order_by('-id')
    total_coupons_used = coupons.aggregate(total=Sum('used_count'))['total'] or 0

    context = {
        'campaigns': campaigns[:25],
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'coupons': coupons,
        'total_coupons_used': total_coupons_used,
        'templates': CAMPAIGN_TEMPLATES,
    }
    return render(request, 'marketing/campaign_studio.html', context)


@require_GET
def api_audience_count(request):
    """
    Returns live recipient headcount for a selected target cohort.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    audience = request.GET.get('audience', 'all_tourists')
    recipients = get_audience_recipients(audience)
    return JsonResponse({
        'audience': audience,
        'count': len(recipients),
        'sample_recipients': recipients[:3]
    })


@csrf_exempt
@require_POST
def api_create_campaign(request):
    """
    Creates a new campaign, resolves target audience, and returns personalized dispatches.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        headline = data.get('headline', '').strip()
        body = data.get('message_body', '').strip()
        channel = data.get('channel', 'whatsapp')
        target_audience = data.get('target_audience', 'all_tourists')
        coupon_id = data.get('coupon_id')

        if not name or not body:
            return JsonResponse({'error': 'Campaign name and message body are required.'}, status=400)

        coupon = Coupon.objects.filter(pk=coupon_id).first() if coupon_id else None

        campaign = PromotionCampaign.objects.create(
            name=name,
            headline=headline or name,
            channel=channel,
            target_audience=target_audience,
            message_body=body,
            coupon=coupon,
            status='active'
        )

        dispatches = generate_campaign_dispatches(campaign)

        return JsonResponse({
            'success': True,
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'target_count': campaign.target_count,
            'dispatches': dispatches[:15],
            'message': f"Campaign '{campaign.name}' activated for {campaign.target_count} recipients."
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
