import re
import datetime
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from django.urls import path

from .models import (
    Inquiry, CustomerPreference, CommunicationLog,
    CouponProxy, EmailCampaignProxy, UpsellRecommendationProxy,
    InquiryFollowUp, HotelMaster, MonumentEntranceMaster,
    ActivityMaster, GuideChargeMaster, Quotation, QuotationDay, QuotationItem,
    PartnerProfile, PartyContactPerson, B2CCustomerProfile,
    SupplierProfile, SupplierContractedRate, SupplierServiceVoucher,
    DmcTask,
    FlightMaster, DmcDocument, TravelComplaint, SupplierPaymentRequisition,
    DmcInvoice, StaffNotification,
)
from .services import generate_quotation_pdf
from operations.models import Booking


# ==========================================================================
#  Bulk Actions
# ==========================================================================

@admin.action(description="🎯 Mark selected as Quoted")
def mark_as_quoted(modeladmin, request, queryset):
    updated = queryset.filter(status='new').update(status='quoted')
    modeladmin.message_user(request, f"{updated} inquiry(s) marked as Quoted.")


@admin.action(description="❌ Mark selected as Lost")
def mark_as_lost(modeladmin, request, queryset):
    updated = queryset.exclude(status='won').update(status='lost')
    modeladmin.message_user(request, f"{updated} inquiry(s) marked as Lost.")


@admin.action(description="📄 Clone selected Inquiry (creates fresh lead)")
def clone_inquiry(modeladmin, request, queryset):
    cloned = 0
    for original in queryset[:5]:  # Limit to 5 at a time
        original.pk = None
        original.id = None
        original.inquiry_number = ''
        original.status = 'new'
        original.created_at = None
        original.tat_deadline = None
        original.converted_booking = None
        original.converted_trip = None
        original.lost_reason = ''
        original.competitor_name = ''
        original.objection_notes = ''
        original.win_loss_rating = None
        original.assigned_to = request.user
        original.pickup_date = timezone.now().date()
        original.save()
        cloned += 1
    modeladmin.message_user(request, f"📄 {cloned} inquiry(s) cloned as fresh leads.")


@admin.action(description="👥 Reassign selected inquiries to me")
def mass_reassign_to_me(modeladmin, request, queryset):
    updated = queryset.update(assigned_to=request.user)
    modeladmin.message_user(request, f"✅ {updated} inquiry(s) reassigned to {request.user.username}.")
    StaffNotification.push(
        notification_type='system',
        title=f'{updated} leads reassigned to {request.user.get_full_name() or request.user.username}',
        body='Performed via admin bulk action.',
        recipient=request.user,
    )


# ==========================================================================
#  Custom Filters
# ==========================================================================

class PipelineStageFilter(admin.SimpleListFilter):
    title = 'Pipeline Stage'
    parameter_name = 'pipeline_stage'

    def lookups(self, request, model_admin):
        return [
            ('hot_leads', '🔥 Hot Leads (< 3 days old)'),
            ('stale', '❄️ Stale Leads (> 7 days)'),
            ('high_value', '💎 High Value (> ₹25,000)'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now()
        if self.value() == 'hot_leads':
            return queryset.filter(
                status='new',
                created_at__gte=today - datetime.timedelta(days=3)
            )
        elif self.value() == 'stale':
            return queryset.filter(
                status__in=['new', 'quoted'],
                created_at__lte=today - datetime.timedelta(days=7)
            )
        elif self.value() == 'high_value':
            return queryset.filter(quoted_price__gte=25000)
        return queryset


# ==========================================================================
#  1. Inquiry Admin — Sales Pipeline
# ==========================================================================

class InquiryFollowUpInline(TabularInline):
    model = InquiryFollowUp
    extra = 1
    fields = ('scheduled_at', 'interaction_type', 'notes', 'next_action', 'performed_by', 'is_done')


class InquiryDocumentAttachmentInline(TabularInline):
    model = DmcDocument
    fk_name = 'related_inquiry'
    extra = 1
    fields = ('title', 'category', 'document_file', 'description', 'uploaded_by')


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    autocomplete_fields = ['party', 'vehicle_type']
    list_display = (
        'inquiry_number_display', 'guest_display', 'party_link',
        'priority_badge', 'tat_countdown_badge', 'assigned_to',
        'journey_badge', 'route_display', 'vehicle_badge',
        'pickup_date', 'quoted_price_display',
        'pipeline_status_badge', 'age_display', 'quick_actions'
    )
    list_filter = (PipelineStageFilter, 'status', 'priority', 'source', 'journey_type', 'pickup_date')
    list_select_related = ('party', 'assigned_to', 'vehicle_type')
    search_fields = ('inquiry_number', 'guest_name', 'guest_phone', 'party__name', 'destination', 'pickup_location', 'notes')
    readonly_fields = ('inquiry_number', 'created_at', 'tat_deadline', 'client_profile_snapshot', 'client_comm_history')
    actions = ['convert_to_booking', 'download_quotation', mark_as_quoted, mark_as_lost, clone_inquiry, mass_reassign_to_me]
    inlines = [InquiryFollowUpInline, InquiryDocumentAttachmentInline]
    date_hierarchy = 'pickup_date'
    change_list_template = 'admin/crm/inquiry/change_list.html'

    fieldsets = (
        ('1. Lead Identification & SLA Governance', {
            'fields': (
                ('inquiry_number', 'status'),
                ('priority', 'source'),
                ('assigned_to', 'target_tat_hours', 'tat_deadline'),
                ('party', 'guest_name'),
                ('guest_phone', 'guest_email'),
                'client_profile_snapshot',
            )
        }),
        ('2. Circuit Route & Schedule', {
            'fields': (
                ('destination_dropdown', 'destination'),
                ('pickup_location', 'journey_type'),
                ('pickup_date', 'pickup_time', 'drop_date'),
                ('adult_count', 'child_count'),
            )
        }),
        ('3. Fleet Allocation & Commercial Quotation', {
            'fields': (
                ('vehicle_type', 'estimated_km', 'quoted_price'),
                'special_requirements',
                'notes',
            )
        }),
        ('4. Customer Communication History', {
            'fields': ('client_comm_history',),
            'classes': ('collapse',),
            'description': 'Recent WhatsApp and Email interactions with this client.'
        }),
        ('5. 🔴 Objection Management (Fill when Lost)', {
            'fields': (
                ('lost_reason', 'competitor_name'),
                'objection_notes',
                'win_loss_rating',
            ),
            'classes': ('collapse',),
            'description': '⚠️ Fill this section when marking a lead as Lost. Helps analyse objection patterns and improve conversion rates.'
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_leads = Inquiry.objects.count()
        three_days_ago = timezone.now() - datetime.timedelta(days=3)
        hot_leads = Inquiry.objects.filter(status='new', created_at__gte=three_days_ago).count()
        won_count = Inquiry.objects.filter(status='won').count()
        win_rate = f"{(won_count / total_leads * 100):.1f}" if total_leads else "0"
        pipeline_sum = Inquiry.objects.filter(status__in=['new', 'quoted']).aggregate(sum=Sum('quoted_price'))['sum'] or 0

        extra_context['kpi_metrics'] = {
            'total_leads': total_leads,
            'hot_leads': hot_leads,
            'won_count': won_count,
            'win_rate': win_rate,
            'pipeline_val': f"{pipeline_sum:,.0f}",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:inquiry_id>/pdf/', self.admin_site.admin_view(self.download_single_pdf), name='crm_inquiry_pdf'),
        ]
        return custom_urls + urls

    def download_single_pdf(self, request, inquiry_id):
        inquiry = self.get_object(request, inquiry_id)
        if not inquiry:
            messages.error(request, "Inquiry not found.")
            return HttpResponse(status=404)
        pdf_bytes = generate_quotation_pdf(inquiry)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Quotation_{inquiry.inquiry_number}.pdf"'
        return response

    @admin.display(description='Inquiry #')
    def inquiry_number_display(self, obj):
        return format_html(
            '<span style="color: #38bdf8; font-weight: 700; font-size: 13px;">'
            '<i class="fas fa-hashtag mr-1"></i>{}'
            '</span>',
            obj.inquiry_number
        )

    @admin.display(description='Guest')
    def guest_display(self, obj):
        phone = f' | {obj.guest_phone}' if obj.guest_phone else ''
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">{}</span>'
            '<br><small style="color: #94a3b8;">{}</small>',
            obj.guest_name, phone
        )

    @admin.display(description='Party / Client')
    def party_link(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 500;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.party.id, obj.party.name
        )

    @admin.display(description='Journey')
    def journey_badge(self, obj):
        styles = {
            'local': ('#10b981', 'fas fa-city', 'Local'),
            'outstation': ('#3b82f6', 'fas fa-road', 'Outstation'),
            'airport': ('#8b5cf6', 'fas fa-plane', 'Airport'),
            'round_trip': ('#f59e0b', 'fas fa-sync-alt', 'Round Trip'),
            'one_way': ('#64748b', 'fas fa-arrow-right', 'One Way'),
        }
        color, icon, label = styles.get(obj.journey_type, ('#64748b', 'fas fa-car', obj.journey_type))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Route')
    def route_display(self, obj):
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;">{}</span>'
            ' <i class="fas fa-arrow-right" style="color: #38bdf8; font-size: 10px; margin: 0 4px;"></i> '
            '<span style="color: #f8fafc; font-weight: 600; font-size: 12px;">{}</span>',
            obj.pickup_location[:24], obj.destination[:28]
        )

    @admin.display(description='Vehicle')
    def vehicle_badge(self, obj):
        if not obj.vehicle_type:
            return mark_safe('<span style="color: #64748b;">—</span>')
        cap = f"({obj.vehicle_type.seating_capacity} seats)" if hasattr(obj.vehicle_type, 'seating_capacity') and obj.vehicle_type.seating_capacity else ""
        return format_html(
            '<span style="color: #e2e8f0; font-size: 11.5px; font-weight: 500;">'
            '<i class="fas fa-bus mr-1" style="color: #38bdf8;"></i>{} <small style="color: #94a3b8;">{}</small>'
            '</span>',
            obj.vehicle_type.name, cap
        )

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        styles = {
            'low': ('#64748b', 'Low'),
            'medium': ('#3b82f6', 'Medium'),
            'high': ('#f59e0b', 'High'),
            'urgent': ('#ef4444', '🔥 Urgent / VIP'),
        }
        color, label = styles.get(obj.priority, ('#64748b', obj.priority))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 8px; font-size: 11px; font-weight: 600;">{}</span>',
            color, label
        )

    @admin.display(description='Response TAT')
    def tat_countdown_badge(self, obj):
        if obj.status in ['won', 'lost', 'quoted']:
            return mark_safe('<span style="color: #10b981; font-size: 11px;"><i class="fas fa-check-circle mr-1"></i>Completed</span>')
        rem = obj.tat_remaining_hours
        if rem is None:
            return mark_safe('<span style="color: #64748b;">—</span>')
        if rem <= 0:
            return format_html('<span class="badge" style="background-color: #ef4444; color: #fff; padding: 3px 6px; font-size: 10px; font-weight: 700;">🚨 SLA Breached ({}h)</span>', f"{abs(rem):.1f}")
        elif rem <= 4:
            return format_html('<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 3px 6px; font-size: 10px; font-weight: 700;">⏱️ {}h left</span>', f"{rem:.1f}")
        else:
            return format_html('<span style="color: #94a3b8; font-size: 11px;">⏱️ {}h left</span>', f"{rem:.1f}")

    @admin.display(description='Quoted Price')
    def quoted_price_display(self, obj):
        if not obj.quoted_price:
            return mark_safe('<span class="badge" style="background-color: #1e293b; color: #f59e0b; padding: 3px 6px; font-size: 11px;">Not Quoted</span>')
        return format_html(
            '<span style="color: #10b981; font-weight: 700; font-size: 13px;">₹{}</span>',
            f"{obj.quoted_price:,.0f}"
        )

    @admin.display(description='Pipeline Status')
    def pipeline_status_badge(self, obj):
        styles = {
            'new': ('#3b82f6', 'fas fa-bolt', '🆕 New Lead'),
            'quoted': ('#f59e0b', 'fas fa-file-invoice', '📋 Quoted'),
            'won': ('#10b981', 'fas fa-trophy', '🏆 Won'),
            'lost': ('#ef4444', 'fas fa-times', '❌ Lost'),
        }
        color, icon, label = styles.get(obj.status, ('#64748b', 'fas fa-question', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 5px 10px; font-size: 12px; font-weight: 600;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Age')
    def age_display(self, obj):
        delta = timezone.now() - obj.created_at
        days = delta.days
        if days == 0:
            label = 'Today'
            color = '#10b981'
        elif days <= 3:
            label = f'{days}d ago'
            color = '#10b981'
        elif days <= 7:
            label = f'{days}d ago'
            color = '#f59e0b'
        else:
            label = f'{days}d ago'
            color = '#ef4444'
        return format_html(
            '<span style="color: {}; font-weight: 600; font-size: 11px;">{}</span>',
            color, label
        )

    @admin.display(description='Quick Actions')
    def quick_actions(self, obj):
        phone_digits = re.sub(r'\D', '', obj.guest_phone or '')
        wa_link = f"https://wa.me/{phone_digits}?text=Hello%20{obj.guest_name},%20regarding%20your%20inquiry%20{obj.inquiry_number}%20for%20{obj.destination}%20with%20Sivagayathiri%20Travels" if phone_digits else "#"
        wa_target = '_blank' if phone_digits else '_self'
        pdf_url = f"/admin/crm/inquiry/{obj.id}/pdf/"

        return format_html(
            '<div style="display: flex; gap: 6px; align-items: center;">'
            '<a href="{}" target="{}" title="Send WhatsApp Message" style="background: #25D366; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; display: inline-flex; align-items: center;">'
            '<i class="fab fa-whatsapp"></i>'
            '</a>'
            '<a href="{}" title="Download Quotation PDF" style="background: #0284c7; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; display: inline-flex; align-items: center;">'
            '<i class="fas fa-file-pdf"></i>'
            '</a>'
            '</div>',
            wa_link, wa_target, pdf_url
        )

    @admin.display(description='Client Profile & Preferences Snapshot')
    def client_profile_snapshot(self, obj):
        if not obj.party:
            return mark_safe('<span style="color: #94a3b8;">No client attached.</span>')
        pref = getattr(obj.party, 'preferences', None)
        vt_name = pref.preferred_vehicle_type.name if pref and pref.preferred_vehicle_type else 'Not Specified'
        diet = pref.dietary_requirements if pref and pref.dietary_requirements else 'Standard / No Special Diet'
        wa_opt = '✅ Opted-in' if pref and pref.whatsapp_opt_in else '❌ Opted-out'
        em_opt = '✅ Opted-in' if pref and pref.email_opt_in else '❌ Opted-out'

        return format_html(
            '<div style="background: #1e293b; border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 6px; margin-top: 6px;">'
            '<div style="font-weight: 700; color: #f8fafc; margin-bottom: 6px;"><i class="fas fa-id-badge mr-1" style="color: #38bdf8;"></i> Client Preferences: {}</div>'
            '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 12px; color: #cbd5e1;">'
            '<div><strong>Preferred Vehicle:</strong> <span style="color: #93c5fd;">{}</span></div>'
            '<div><strong>Catering Standard:</strong> <span style="color: #fef08a;">{}</span></div>'
            '<div><strong>WhatsApp Consent:</strong> {}</div>'
            '<div><strong>Email Consent:</strong> {}</div>'
            '</div>'
            '</div>',
            obj.party.name, vt_name, diet, wa_opt, em_opt
        )

    @admin.display(description='Recent Communication History')
    def client_comm_history(self, obj):
        if not obj.party:
            return mark_safe('<span style="color: #94a3b8;">No client history.</span>')
        logs = CommunicationLog.objects.filter(client=obj.party).order_by('-sent_at')[:6]
        if not logs.exists():
            return mark_safe('<span style="color: #94a3b8;">No communications logged yet for this client.</span>')
        
        rows = []
        for l in logs:
            badge_color = '#25D366' if l.comm_type == 'whatsapp' else '#3b82f6'
            icon = 'fab fa-whatsapp' if l.comm_type == 'whatsapp' else 'fas fa-envelope'
            sent_str = l.sent_at.strftime('%d/%m/%Y %H:%M') if l.sent_at else '—'
            msg_snippet = escape(l.message_content[:90] + ('...' if len(l.message_content) > 90 else ''))
            rows.append(
                f'<tr style="border-bottom: 1px solid #334155; font-size: 12px;">'
                f'<td style="padding: 6px 10px;"><span class="badge" style="background-color: {badge_color}; color: #fff;"><i class="{icon} mr-1"></i>{l.comm_type.title()}</span></td>'
                f'<td style="padding: 6px 10px; color: #94a3b8;">{sent_str}</td>'
                f'<td style="padding: 6px 10px; color: #cbd5e1;">{msg_snippet}</td>'
                f'<td style="padding: 6px 10px;"><span class="badge" style="background: #10b981; color: #fff;">{l.status}</span></td>'
                f'</tr>'
            )
        table_html = (
            '<table style="width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 6px; overflow: hidden;">'
            '<thead><tr style="background: #1e293b; color: #94a3b8; font-size: 11px; text-transform: uppercase;">'
            '<th style="padding: 6px 10px; text-align: left;">Channel</th>'
            '<th style="padding: 6px 10px; text-align: left;">Date</th>'
            '<th style="padding: 6px 10px; text-align: left;">Message Preview</th>'
            '<th style="padding: 6px 10px; text-align: left;">Status</th>'
            '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        )
        return mark_safe(table_html)

    @admin.action(description='📄 Download Quotation PDF')
    def download_quotation(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one inquiry to download.", level=messages.ERROR)
            return
        inquiry = queryset.first()
        pdf_bytes = generate_quotation_pdf(inquiry)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Quotation_{inquiry.inquiry_number}.pdf"'
        return response

    @admin.action(description='🚀 Convert to Booking')
    def convert_to_booking(self, request, queryset):
        success_count = 0
        for inquiry in queryset:
            if inquiry.status == 'won':
                self.message_user(request, f"Inquiry {inquiry.inquiry_number} is already converted.", level=messages.WARNING)
                continue
            booking = Booking.objects.create(
                party=inquiry.party,
                guest_name=inquiry.guest_name,
                guest_phone=inquiry.guest_phone,
                pickup_location=inquiry.pickup_location,
                destination=inquiry.destination,
                pickup_date=inquiry.pickup_date,
                pickup_time=inquiry.pickup_time,
                drop_date=inquiry.drop_date,
                journey_type=inquiry.journey_type,
                vehicle_type=inquiry.vehicle_type,
                special_requirements=inquiry.special_requirements,
                quoted_price=inquiry.quoted_price,
                expected_km=inquiry.estimated_km,
                notes=inquiry.notes,
                status='pending'
            )
            inquiry.status = 'won'
            inquiry.save(update_fields=['status'])
            success_count += 1
        if success_count > 0:
            self.message_user(request, f"Successfully converted {success_count} inquiry(s) to bookings.")


# ==========================================================================
#  2. CustomerPreference Admin
# ==========================================================================

@admin.register(CustomerPreference)
class CustomerPreferenceAdmin(ModelAdmin):
    autocomplete_fields = ['client', 'preferred_vehicle_type']
    list_display = ('client_display', 'party_type_badge', 'preferred_vehicle_badge', 'dietary_badge', 'notification_channels', 'quick_contact')
    list_filter = ('whatsapp_opt_in', 'email_opt_in', 'preferred_vehicle_type', 'client__party_type')
    search_fields = ('client__name', 'client__phone', 'client__email', 'dietary_requirements')
    readonly_fields = ('dietary_preset_guide',)

    fieldsets = (
        ('Client Profile & Preferred Fleet', {
            'fields': (('client', 'preferred_vehicle_type'),)
        }),
        ('Catering & Dietary Guidelines', {
            'fields': ('dietary_requirements', 'dietary_preset_guide')
        }),
        ('Omnichannel Communication Consent', {
            'fields': (('whatsapp_opt_in', 'email_opt_in'),),
            'description': 'Customer opt-in permissions for transactional notifications and seasonal discount updates.'
        }),
    )

    @admin.display(description='Client')
    def client_display(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 600;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.client.id, obj.client.name
        )

    @admin.display(description='Party Type')
    def party_type_badge(self, obj):
        pt = getattr(obj.client, 'party_type', 'other')
        styles = {
            'corporate': ('#3b82f6', 'fas fa-briefcase', 'Corporate'),
            'travel_agency': ('#8b5cf6', 'fas fa-globe-asia', 'Travel Agency'),
            'hotel': ('#f59e0b', 'fas fa-hotel', 'Hotel Partner'),
            'individual': ('#10b981', 'fas fa-user', 'Individual / Family'),
        }
        color, icon, label = styles.get(pt, ('#64748b', 'fas fa-tag', pt.title()))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Preferred Vehicle')
    def preferred_vehicle_badge(self, obj):
        if not obj.preferred_vehicle_type:
            return mark_safe('<span style="color: #64748b;">Not Specified</span>')
        cap = f"({obj.preferred_vehicle_type.seating_capacity} seats)" if hasattr(obj.preferred_vehicle_type, 'seating_capacity') and obj.preferred_vehicle_type.seating_capacity else ""
        return format_html(
            '<span style="color: #f8fafc; font-size: 12px; font-weight: 500;">'
            '<i class="fas fa-shuttle-van mr-1" style="color: #38bdf8;"></i>{} <small style="color: #94a3b8;">{}</small>'
            '</span>',
            obj.preferred_vehicle_type.name, cap
        )

    @admin.display(description='Dietary Requirements')
    def dietary_badge(self, obj):
        req = (obj.dietary_requirements or '').lower()
        if not req:
            return mark_safe('<span style="color: #64748b;">Standard</span>')
        if 'brahmin' in req or 'pure veg' in req:
            badge = '<span class="badge" style="background: #15803d; color: #fff; padding: 3px 8px;">🌿 Pure Veg Brahmin</span>'
        elif 'jain' in req:
            badge = '<span class="badge" style="background: #ca8a04; color: #fff; padding: 3px 8px;">🥗 Jain Food</span>'
        elif 'halal' in req:
            badge = '<span class="badge" style="background: #0284c7; color: #fff; padding: 3px 8px;">🥩 Halal Certified</span>'
        elif 'corporate' in req:
            badge = '<span class="badge" style="background: #4f46e5; color: #fff; padding: 3px 8px;">🍽️ Corporate Buffet</span>'
        else:
            badge = f'<span class="badge" style="background: #334155; color: #e2e8f0; padding: 3px 8px;">{obj.dietary_requirements[:28]}</span>'
        return mark_safe(badge)

    @admin.display(description='Channels')
    def notification_channels(self, obj):
        badges = []
        if obj.whatsapp_opt_in:
            badges.append(
                '<span class="badge" style="background-color: #25D366; color: #fff; padding: 3px 8px; font-size: 11px; margin-right: 4px;">'
                '<i class="fab fa-whatsapp mr-1"></i>WhatsApp</span>'
            )
        if obj.email_opt_in:
            badges.append(
                '<span class="badge" style="background-color: #3b82f6; color: #fff; padding: 3px 8px; font-size: 11px;">'
                '<i class="fas fa-envelope mr-1"></i>Email</span>'
            )
        if not badges:
            return mark_safe('<span style="color: #94a3b8;">None</span>')
        return mark_safe(' '.join(badges))

    @admin.display(description='Contact')
    def quick_contact(self, obj):
        phone = obj.client.phone or '—'
        email = obj.client.email or '—'
        return format_html(
            '<span style="font-size: 11px; color: #94a3b8;"><i class="fas fa-phone mr-1"></i>{}<br><i class="fas fa-envelope mr-1"></i>{}</span>',
            phone, email
        )

    @admin.display(description='Standard Dietary Guidelines Presets')
    def dietary_preset_guide(self, obj):
        return mark_safe(
            '<div style="background: #0f172a; padding: 12px; border-radius: 6px; font-size: 12px; color: #94a3b8; border: 1px dashed #334155;">'
            '<strong style="color: #f8fafc;">💡 Recommended Copy-Paste Presets:</strong><br>'
            '• <code>Pure Vegetarian Brahmin Catering (No Onion/No Garlic for Temple Tours)</code><br>'
            '• <code>Jain Food Only (Strict vegetarian, no root vegetables)</code><br>'
            '• <code>Halal Certified Meals with Chettinad & Malabar Specialities</code><br>'
            '• <code>Standard Corporate Buffet with Morning High Tea & Refreshments</code><br>'
            '• <code>Mild Spices / Diabetic-Friendly Meals for Senior Citizens</code>'
            '</div>'
        )


# ==========================================================================
#  3. CommunicationLog Admin
# ==========================================================================

@admin.register(CommunicationLog)
class CommunicationLogAdmin(ModelAdmin):
    list_display = ('client_display', 'booking_link', 'channel_badge', 'intent_badge', 'message_preview', 'sent_at', 'status_badge')
    list_filter = ('comm_type', 'status', 'sent_at', ('booking', admin.EmptyFieldListFilter))
    search_fields = ('client__name', 'booking__booking_number', 'message_content')
    readonly_fields = ('client', 'booking', 'comm_type', 'message_content', 'sent_at', 'status', 'rendered_message_preview')

    fieldsets = (
        ('Dispatch Metadata', {
            'fields': (('client', 'booking'), ('comm_type', 'status', 'sent_at'))
        }),
        ('Rendered Customer View', {
            'fields': ('rendered_message_preview',),
            'description': 'Visual preview of the message formatted as received by the customer.'
        }),
        ('Raw Message Payload', {
            'fields': ('message_content',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Client')
    def client_display(self, obj):
        return format_html(
            '<a href="/admin/core_partners/client/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 500;">'
            '<i class="fas fa-building mr-1"></i>{}'
            '</a>',
            obj.client.id, obj.client.name
        )

    @admin.display(description='Linked Booking')
    def booking_link(self, obj):
        if not obj.booking:
            return mark_safe('<span style="color: #64748b;">General Broadcast</span>')
        return format_html(
            '<a href="/admin/operations/booking/{}/change/" style="color: #38bdf8; text-decoration: none; font-weight: 600; font-family: monospace;">'
            '<i class="fas fa-ticket-alt mr-1"></i>{}'
            '</a>',
            obj.booking.id, obj.booking.booking_number
        )

    @admin.display(description='Channel')
    def channel_badge(self, obj):
        if obj.comm_type == 'whatsapp':
            return mark_safe(
                '<span class="badge" style="background-color: #25D366; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '<i class="fab fa-whatsapp mr-1"></i>WhatsApp</span>'
            )
        return mark_safe(
            '<span class="badge" style="background-color: #3b82f6; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="fas fa-envelope mr-1"></i>Email</span>'
        )

    @admin.display(description='Intent')
    def intent_badge(self, obj):
        msg = (obj.message_content or '').lower()
        if 'quotation' in msg or 'quote' in msg:
            badge = '<span class="badge" style="background: #0284c7; color: #fff;">📋 Quote</span>'
        elif 'confirmed' in msg or 'confirmation' in msg:
            badge = '<span class="badge" style="background: #10b981; color: #fff;">✅ Confirmation</span>'
        elif 'payment' in msg or 'receipt' in msg:
            badge = '<span class="badge" style="background: #8b5cf6; color: #fff;">💳 Payment</span>'
        elif 'driver' in msg or 'chauffeur' in msg or 'dispatch' in msg or 'reported' in msg:
            badge = '<span class="badge" style="background: #f59e0b; color: #fff;">🚗 Dispatch</span>'
        elif 'reminder' in msg:
            badge = '<span class="badge" style="background: #06b6d4; color: #fff;">⏰ Reminder</span>'
        elif 'rate' in msg or 'feedback' in msg:
            badge = '<span class="badge" style="background: #eab308; color: #000;">🌟 Feedback</span>'
        elif 'discount' in msg or 'coupon' in msg or 'early bird' in msg:
            badge = '<span class="badge" style="background: #ec4899; color: #fff;">🎉 Promotion</span>'
        else:
            badge = '<span class="badge" style="background: #64748b; color: #fff;">💬 General</span>'
        return mark_safe(badge)

    @admin.display(description='Message Preview')
    def message_preview(self, obj):
        preview = obj.message_content[:85] + '...' if len(obj.message_content) > 85 else obj.message_content
        return format_html('<span style="color: #cbd5e1; font-size: 12px;">{}</span>', preview)

    @admin.display(description='Status')
    def status_badge(self, obj):
        styles = {
            'sent': ('#10b981', 'Sent'),
            'delivered': ('#3b82f6', 'Delivered'),
            'failed': ('#ef4444', 'Failed'),
        }
        color, label = styles.get(obj.status, ('#64748b', obj.status))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 8px; font-size: 11px;">{}</span>',
            color, label
        )

    @admin.display(description='Rendered Customer Message Preview')
    def rendered_message_preview(self, obj):
        content = escape(obj.message_content).replace('\n', '<br>')
        if obj.comm_type == 'whatsapp':
            time_str = obj.sent_at.strftime('%I:%M %p') if obj.sent_at else 'Just now'
            checkmarks = '<span style="color: #38bdf8; margin-left: 4px;">✓✓</span>' if obj.status == 'delivered' else '<span style="color: #94a3b8; margin-left: 4px;">✓</span>'
            return mark_safe(
                f'<div style="background: #0b141a; padding: 24px; border-radius: 8px; max-width: 600px;">'
                f'<div style="background: #005c4b; color: #e9edef; padding: 12px 16px; border-radius: 8px; position: relative; font-size: 13.5px; line-height: 1.5; box-shadow: 0 1px 2px rgba(0,0,0,0.3);">'
                f'{content}'
                f'<div style="text-align: right; font-size: 11px; color: #8696a0; margin-top: 6px;">'
                f'{time_str} {checkmarks}'
                f'</div>'
                f'</div>'
                f'</div>'
            )
        else: # Email
            client_name = obj.client.name if obj.client else 'Valued Customer'
            return mark_safe(
                f'<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; max-width: 650px;">'
                f'<div style="border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 14px; font-size: 12px; color: #94a3b8;">'
                f'<div><strong>To:</strong> {client_name}</div>'
                f'<div><strong>From:</strong> reservations@sivagayathiritravels.com</div>'
                f'</div>'
                f'<div style="color: #f1f5f9; font-size: 14px; line-height: 1.6;">{content}</div>'
                f'</div>'
            )


# ==========================================================================
#  4. Coupon Proxy Admin (from Marketing)
# ==========================================================================

@admin.register(CouponProxy)
class CouponProxyAdmin(ModelAdmin):
    autocomplete_fields = ['applicable_package']
    list_display = ('code_display', 'discount_display', 'package_scope_badge', 'usage_progress_display', 'expiry_countdown_badge', 'active_badge')
    list_filter = ('is_active', 'applicable_package__category')
    search_fields = ('code', 'applicable_package__name', 'applicable_package__package_code')

    fieldsets = (
        ('Coupon Identity & Status', {
            'fields': (('code', 'is_active'),)
        }),
        ('Discount Valuation', {
            'fields': (('discount_percent', 'flat_discount'),),
            'description': 'Specify either a percentage discount (e.g. 15.00 for 15%) OR a flat discount (e.g. 1000 for ₹1,000).'
        }),
        ('Applicable Tour Scope', {
            'fields': ('applicable_package',),
            'description': 'Select a target tour package, or leave empty to make this coupon valid across all packages.'
        }),
        ('Redemption Quotas & Validity', {
            'fields': (('usage_limit', 'used_count'), 'expiry_date')
        }),
    )

    @admin.display(description='Coupon Code')
    def code_display(self, obj):
        return format_html(
            '<span style="color: #f59e0b; font-weight: 700; font-size: 13px; font-family: monospace; '
            'background: #1e293b; padding: 4px 8px; border-radius: 4px; border: 1px dashed #f59e0b;">'
            '{}</span>',
            obj.code
        )

    @admin.display(description='Discount')
    def discount_display(self, obj):
        if obj.discount_percent:
            return format_html(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px; font-size: 12px;">'
                '{}% OFF</span>',
                obj.discount_percent
            )
        elif obj.flat_discount:
            return format_html(
                '<span class="badge" style="background-color: #8b5cf6; color: #fff; padding: 4px 8px; font-size: 12px;">'
                '₹{} FLAT</span>',
                f"{obj.flat_discount:,.0f}"
            )
        return mark_safe('<span style="color: #94a3b8;">—</span>')

    @admin.display(description='Tour Package Scope')
    def package_scope_badge(self, obj):
        if not obj.applicable_package:
            return mark_safe('<span class="badge" style="background: #334155; color: #93c5fd; padding: 4px 8px;"><i class="fas fa-globe mr-1"></i>All Packages</span>')
        cat = obj.applicable_package.category or 'tour'
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;">'
            '<span class="badge" style="background: #1e293b; color: #38bdf8; margin-right: 4px;">{}</span>'
            '{}</span>',
            cat.replace('_', ' ').title(),
            obj.applicable_package.name[:45]
        )

    @admin.display(description='Usage Quota')
    def usage_progress_display(self, obj):
        limit = obj.usage_limit
        used = obj.used_count
        if not limit:
            return format_html('<span style="color: #10b981; font-weight: 600;">{} uses (No Limit)</span>', used)
        
        pct = min(100, int((used / limit) * 100))
        color = '#10b981' if pct < 75 else '#f59e0b' if pct < 100 else '#ef4444'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<div style="background: #334155; border-radius: 4px; overflow: hidden; height: 14px; width: 85px;">'
            '<div style="background: {}; width: {}%; height: 100%;"></div>'
            '</div>'
            '<span style="color: {}; font-weight: 600; font-size: 11px;">{}/{} ({}%)</span>'
            '</div>',
            color, pct, color, used, limit, pct
        )

    @admin.display(description='Expiry Status')
    def expiry_countdown_badge(self, obj):
        if not obj.expiry_date:
            return mark_safe('<span class="badge" style="background-color: #1e293b; color: #10b981; padding: 3px 6px; font-size: 11px;">♾️ No Expiry</span>')
        today = timezone.now().date()
        remaining = (obj.expiry_date - today).days
        if remaining < 0:
            return mark_safe('<span class="badge" style="background-color: #ef4444; color: #fff; padding: 3px 6px; font-size: 11px;">❌ Expired</span>')
        elif remaining <= 7:
            return format_html(
                '<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 3px 6px; font-size: 11px;">'
                '🔥 {}d left</span>',
                remaining
            )
        return format_html(
            '<span style="color: #94a3b8; font-size: 12px;"><i class="fas fa-calendar-alt mr-1"></i>{} ({}d)</span>',
            obj.expiry_date.strftime('%d/%m/%Y'), remaining
        )

    @admin.display(description='Status')
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">Active</span>')
        return mark_safe('<span class="badge" style="background-color: #64748b; color: #fff; padding: 3px 8px;">Inactive</span>')


# ==========================================================================
#  5. EmailCampaign Proxy Admin (from Marketing)
# ==========================================================================

@admin.register(EmailCampaignProxy)
class EmailCampaignProxyAdmin(ModelAdmin):
    list_display = ('name_display', 'subject_display', 'theme_badge', 'sent_badge', 'active_badge')
    list_filter = ('is_active', 'sent_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('live_email_preview',)

    fieldsets = (
        ('Campaign Overview', {
            'fields': (('name', 'is_active'), 'subject')
        }),
        ('Dispatch Schedule', {
            'fields': ('sent_at',),
            'description': 'Leave empty to save as Draft. Set a timestamp when sending.'
        }),
        ('Newsletter HTML Body', {
            'fields': ('body_html',),
            'description': 'Full HTML template for email newsletter broadcast.'
        }),
        ('Live Customer Inbox Preview', {
            'fields': ('live_email_preview',),
            'description': 'Interactive rendering of how the email appears in customer inboxes.'
        }),
    )

    @admin.display(description='Campaign Name')
    def name_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600;">'
            '<i class="fas fa-paper-plane mr-1" style="color: #3b82f6;"></i>{}'
            '</span>',
            obj.name
        )

    @admin.display(description='Subject Line')
    def subject_display(self, obj):
        return format_html(
            '<span style="color: #cbd5e1; font-size: 12px;">{}</span>',
            obj.subject[:65] + '...' if len(obj.subject) > 65 else obj.subject
        )

    @admin.display(description='Theme')
    def theme_badge(self, obj):
        subj = (obj.subject or '').lower() + (obj.name or '').lower()
        if 'temple' in subj or 'divine' in subj or 'yatra' in subj or 'sabarimala' in subj:
            return mark_safe('<span class="badge" style="background: #8b5cf6; color: #fff;">🕉️ Devotional</span>')
        elif 'college' in subj or 'industrial' in subj or 'school' in subj:
            return mark_safe('<span class="badge" style="background: #f59e0b; color: #fff;">🎓 College IV</span>')
        elif 'hill' in subj or 'ooty' in subj or 'munnar' in subj or 'kodaikanal' in subj:
            return mark_safe('<span class="badge" style="background: #10b981; color: #fff;">⛰️ Hill Station</span>')
        elif 'corporate' in subj or 'retreat' in subj or 'team' in subj:
            return mark_safe('<span class="badge" style="background: #0284c7; color: #fff;">🏢 Corporate</span>')
        elif 'diwali' in subj or 'navratri' in subj or 'festive' in subj:
            return mark_safe('<span class="badge" style="background: #ec4899; color: #fff;">🪔 Festive Special</span>')
        return mark_safe('<span class="badge" style="background: #64748b; color: #fff;">🏖️ Vacation</span>')

    @admin.display(description='Sent Status')
    def sent_badge(self, obj):
        if obj.sent_at:
            return format_html(
                '<span class="badge" style="background-color: #10b981; color: #fff; padding: 4px 8px; font-size: 11px;">'
                '✅ Sent {}</span>',
                obj.sent_at.strftime('%d/%m/%y')
            )
        return mark_safe(
            '<span class="badge" style="background-color: #f59e0b; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '📝 Draft</span>'
        )

    @admin.display(description='Status')
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge" style="background-color: #10b981; color: #fff; padding: 3px 8px;">Active</span>')
        return mark_safe('<span class="badge" style="background-color: #64748b; color: #fff; padding: 3px 8px;">Inactive</span>')

    @admin.display(description='Live Email Rendering')
    def live_email_preview(self, obj):
        if not obj.body_html:
            return mark_safe('<span style="color: #94a3b8;">No HTML body provided yet.</span>')
        # Render responsive preview frame
        safe_html = escape(obj.body_html)
        return format_html(
            '<div style="background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #1e293b;">'
            '<div style="color: #94a3b8; font-size: 12px; margin-bottom: 8px;"><i class="fas fa-desktop mr-1"></i> Desktop &amp; Mobile Responsive Frame:</div>'
            '<iframe srcdoc="{}" style="width: 100%; height: 500px; border: none; border-radius: 6px; background: #fff;"></iframe>'
            '</div>',
            safe_html
        )


# ==========================================================================
#  6. UpsellRecommendation Proxy Admin (from Marketing)
# ==========================================================================

@admin.register(UpsellRecommendationProxy)
class UpsellRecommendationProxyAdmin(ModelAdmin):
    autocomplete_fields = ['package']
    list_display = ('title_display', 'package_category_badge', 'package_link', 'price_display', 'description_snippet')
    list_filter = ('package__category',)
    search_fields = ('title', 'package__name', 'package__package_code')
    readonly_fields = ('quick_preset_suggestions',)

    fieldsets = (
        ('Tour Assignment', {
            'fields': ('package',),
            'description': 'Search and select the tour package this add-on attaches to.'
        }),
        ('Add-On Identity & Commercials', {
            'fields': (('title', 'price'),)
        }),
        ('Customer Pitch & Inclusions', {
            'fields': ('description', 'quick_preset_suggestions')
        }),
    )

    @admin.display(description='Add-On Experience')
    def title_display(self, obj):
        return format_html(
            '<span style="color: #f1f5f9; font-weight: 600; font-size: 13px;">'
            '<i class="fas fa-gem mr-1" style="color: #a855f7;"></i>{}'
            '</span>',
            obj.title
        )

    @admin.display(description='Tour Category')
    def package_category_badge(self, obj):
        if not obj.package or not obj.package.category:
            return mark_safe('<span style="color: #64748b;">—</span>')
        cat = obj.package.category
        styles = {
            'devotional': ('#8b5cf6', 'fas fa-om', 'Devotional'),
            'college_iv': ('#f59e0b', 'fas fa-graduation-cap', 'College IV'),
            'hill_station': ('#10b981', 'fas fa-mountain', 'Hill Station'),
            'holiday': ('#14b8a6', 'fas fa-umbrella-beach', 'Leisure Beach'),
            'corporate_offsite': ('#3b82f6', 'fas fa-building', 'Corporate'),
            'local_tour': ('#0ea5e9', 'fas fa-car', 'Local Sightseeing'),
        }
        color, icon, label = styles.get(cat, ('#64748b', 'fas fa-tag', cat.title()))
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px;">'
            '<i class="{} mr-1"></i>{}'
            '</span>',
            color, icon, label
        )

    @admin.display(description='Base Package')
    def package_link(self, obj):
        return format_html(
            '<a href="/admin/packages/package/{}/change/" style="color: #93c5fd; text-decoration: none; font-weight: 500;">'
            '{}'
            '</a>',
            obj.package.id, obj.package.name
        )

    @admin.display(description='Add-On Price')
    def price_display(self, obj):
        return format_html(
            '<span style="color: #10b981; font-weight: 700; font-size: 13px;">₹{}</span>',
            f"{obj.price:,.0f}"
        )

    @admin.display(description='Description Preview')
    def description_snippet(self, obj):
        snip = obj.description[:75] + '...' if len(obj.description) > 75 else obj.description
        return format_html('<span style="color: #94a3b8; font-size: 12px;">{}</span>', snip)

    @admin.display(description='Recommended Add-On Ideas')
    def quick_preset_suggestions(self, obj):
        return mark_safe(
            '<div style="background: #0f172a; padding: 12px; border-radius: 6px; font-size: 12px; color: #94a3b8; border: 1px dashed #334155;">'
            '<strong style="color: #f8fafc;">💎 Popular High-Margin Add-On Ideas:</strong><br>'
            '• <code>🔥 Campfire &amp; DJ Music Night Setup (₹4,500)</code> - For College IV &amp; Hill Station resorts.<br>'
            '• <code>🛕 VIP Temple Darshan &amp; Special Archana Pass (₹1,800)</code> - For Pilgrimage circuits.<br>'
            '• <code>⛵ Luxury Private Alleppey Houseboat Upgrade (₹8,500)</code> - For Kerala vacations.<br>'
            '• <code>🚙 4x4 Off-Road Mountain Jeep Safari (₹3,200)</code> - Deep forest &amp; viewpoint trails.<br>'
            '• <code>🎥 High-Definition Drone Videography &amp; Reel Edit (₹7,500)</code> - For student IV groups.<br>'
            '• <code>🎙️ Multilingual Professional Certified Tour Guide (₹2,500)</code> - For heritage &amp; international tours.'
            '</div>'
        )


# ==============================================================================
#  Travel Master Data Admins
# ==============================================================================

@admin.register(HotelMaster)
class HotelMasterAdmin(ModelAdmin):
    list_display = ('name', 'destination', 'star_category_badge', 'room_type', 'cp_rate_display', 'map_rate_display', 'ap_rate_display', 'peak_surge_display', 'is_active')
    list_filter = ('destination', 'star_category', 'is_active')
    search_fields = ('name', 'destination', 'contact_phone', 'address')
    list_editable = ('is_active',)

    @admin.display(description='Category')
    def star_category_badge(self, obj):
        colors = {
            '5_star': '#eab308',
            '4_star': '#38bdf8',
            '3_star': '#10b981',
            'resort': '#ec4899',
            'heritage': '#a855f7',
            'budget': '#64748b'
        }
        color = colors.get(obj.star_category, '#64748b')
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 3px 7px; font-size: 11px;">{}</span>',
            color, obj.get_star_category_display()
        )

    @admin.display(description='Bed & Breakfast (CP)')
    def cp_rate_display(self, obj):
        return format_html('<b style="color: #10b981;">₹{}</b>', f"{obj.cp_rate:,.0f}" if obj.cp_rate else "0")

    @admin.display(description='Breakfast+Dinner (MAP)')
    def map_rate_display(self, obj):
        return format_html('<span style="color: #cbd5e1;">₹{}</span>', f"{obj.map_rate:,.0f}" if obj.map_rate else "0")

    @admin.display(description='All Meals (AP)')
    def ap_rate_display(self, obj):
        return format_html('<span style="color: #cbd5e1;">₹{}</span>', f"{obj.ap_rate:,.0f}" if obj.ap_rate else "0")

    @admin.display(description='Peak Surge')
    def peak_surge_display(self, obj):
        return format_html('<span style="color: #f59e0b;">+{}%</span>', obj.peak_surge_percent)


@admin.register(MonumentEntranceMaster)
class MonumentEntranceMasterAdmin(ModelAdmin):
    list_display = ('name', 'destination', 'domestic_rates_display', 'foreigner_rates_display', 'camera_fee_display', 'operating_hours', 'is_active')
    list_filter = ('destination', 'is_active')
    search_fields = ('name', 'destination')

    @admin.display(description='Domestic (Adult/Child)')
    def domestic_rates_display(self, obj):
        return format_html('<b style="color: #10b981;">₹{}</b> / ₹{}', f"{obj.domestic_adult_rate:,.0f}", f"{obj.domestic_child_rate:,.0f}")

    @admin.display(description='Foreigner (Adult/Child)')
    def foreigner_rates_display(self, obj):
        return format_html('<span style="color: #38bdf8;">₹{}</span> / ₹{}', f"{obj.foreigner_adult_rate:,.0f}", f"{obj.foreigner_child_rate:,.0f}")

    @admin.display(description='Camera Fee')
    def camera_fee_display(self, obj):
        return f"₹{obj.camera_fee:,.0f}" if obj.camera_fee else "Free"


@admin.register(ActivityMaster)
class ActivityMasterAdmin(ModelAdmin):
    list_display = ('name', 'destination', 'pricing_type_badge', 'rate_display', 'duration_display', 'is_active')
    list_filter = ('destination', 'pricing_type', 'is_active')
    search_fields = ('name', 'destination')

    @admin.display(description='Pricing Type')
    def pricing_type_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #1e293b; color: #38bdf8; padding: 3px 6px; font-size: 11px;">{}</span>',
            obj.get_pricing_type_display()
        )

    @admin.display(description='Rate')
    def rate_display(self, obj):
        return format_html('<b style="color: #10b981;">₹{}</b>', f"{obj.standard_rate:,.0f}")

    @admin.display(description='Duration')
    def duration_display(self, obj):
        return f"{obj.duration_minutes} mins"


@admin.register(GuideChargeMaster)
class GuideChargeMasterAdmin(ModelAdmin):
    list_display = ('destination', 'language_badge', 'half_day_display', 'full_day_display', 'is_active')
    list_filter = ('destination', 'language', 'is_active')
    search_fields = ('destination',)

    @admin.display(description='Language')
    def language_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #3b82f6; color: #fff; padding: 3px 7px; font-size: 11px;">{}</span>',
            obj.get_language_display()
        )

    @admin.display(description='Half Day')
    def half_day_display(self, obj):
        return format_html('<span>₹{}</span>', f"{obj.half_day_rate:,.0f}")

    @admin.display(description='Full Day')
    def full_day_display(self, obj):
        return format_html('<b style="color: #10b981;">₹{}</b>', f"{obj.full_day_rate:,.0f}")


# ==============================================================================
#  Custom Quotation Admin
# ==============================================================================

class QuotationItemInline(TabularInline):
    model = QuotationItem
    extra = 1
    fields = ('category', 'item_name', 'quantity', 'unit_cost', 'total_cost')
    readonly_fields = ('total_cost',)


class QuotationDayInline(StackedInline):
    model = QuotationDay
    extra = 1
    fields = ('day_number', 'title', 'overnight_destination', 'hotel', 'hotel_meal_plan', 'description')


@admin.register(Quotation)
class QuotationAdmin(ModelAdmin):
    list_display = (
        'quotation_number', 'version_badge', 'guest_name', 'destination',
        'duration_display', 'pax_count', 'net_cost_display', 'markup_display',
        'total_quoted_price_display', 'status_badge', 'booking_link', 'actions_display'
    )
    list_filter = ('status', 'destination', 'created_at')
    search_fields = ('quotation_number', 'guest_name', 'guest_phone', 'party__name', 'destination')
    readonly_fields = (
        'quotation_number', 'version', 'transport_cost', 'accommodation_cost',
        'monuments_cost', 'activities_cost', 'guide_cost', 'other_services_cost',
        'net_cost', 'markup_amount', 'gross_price', 'gst_amount', 'total_quoted_price',
        'booking', 'created_at', 'updated_at'
    )
    inlines = [QuotationDayInline, QuotationItemInline]
    actions = ['recalculate_quotes', 'convert_to_bookings']

    fieldsets = (
        ('1. Quotation Identification & Lead Reference', {
            'fields': (
                ('quotation_number', 'version'),
                ('inquiry', 'party'),
                ('guest_name', 'guest_phone', 'guest_email'),
                'title',
                ('destination', 'start_date', 'end_date'),
                ('pax_count', 'vehicle_type', 'vehicle_count'),
                'status',
            )
        }),
        ('2. Commercial Cost Breakdown & Markup Engine', {
            'fields': (
                ('transport_cost', 'accommodation_cost'),
                ('monuments_cost', 'activities_cost'),
                ('guide_cost', 'other_services_cost'),
                'net_cost',
                ('markup_percent', 'markup_amount'),
                'gross_price',
                ('gst_rate', 'gst_amount'),
                'total_quoted_price',
            )
        }),
        ('3. Scope, Inclusions & Exclusions', {
            'fields': (
                'inclusions',
                'exclusions',
                'terms_conditions',
            )
        }),
        ('4. System Conversion Tracking', {
            'fields': (
                'booking',
                ('created_by', 'created_at', 'updated_at'),
            ),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Version')
    def version_badge(self, obj):
        return format_html(
            '<span class="badge" style="background-color: #475569; color: #fff; padding: 2px 6px; font-size: 11px;">v{}</span>',
            obj.version
        )

    @admin.display(description='Duration')
    def duration_display(self, obj):
        return f"{obj.duration_nights}N / {obj.duration_days}D"

    @admin.display(description='Net Cost')
    def net_cost_display(self, obj):
        return format_html('<span style="color: #94a3b8;">₹{}</span>', f"{obj.net_cost:,.0f}")

    @admin.display(description='Markup')
    def markup_display(self, obj):
        return format_html('<span style="color: #38bdf8;">+{}%</span> (₹{})', obj.markup_percent, f"{obj.markup_amount:,.0f}")

    @admin.display(description='Quoted Price')
    def total_quoted_price_display(self, obj):
        return format_html('<b style="color: #10b981; font-size: 13px;">₹{}</b>', f"{obj.total_quoted_price:,.0f}")

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'draft': '#64748b',
            'sent': '#3b82f6',
            'negotiating': '#f59e0b',
            'accepted': '#10b981',
            'rejected': '#ef4444',
            'converted': '#8b5cf6',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description='Booking')
    def booking_link(self, obj):
        if obj.booking:
            return format_html(
                '<a href="/admin/operations/booking/{}/change/" style="color: #38bdf8; font-weight: 600;">{}</a>',
                obj.booking.id, obj.booking.booking_number
            )
        return mark_safe('<span style="color: #64748b;">Not Converted</span>')

    @admin.display(description='Actions')
    def actions_display(self, obj):
        return format_html(
            '<a href="/crm/quotations/{}/preview/" target="_blank" class="button" style="padding: 3px 8px; font-size: 11px; background: #0284c7; color: #fff; border-radius: 4px; text-decoration: none;">'
            '👁️ Preview</a>',
            obj.id
        )

    @admin.action(description="⚡ Recalculate totals from line items")
    def recalculate_quotes(self, request, queryset):
        for q in queryset:
            q.recalculate_totals()
        self.message_user(request, f"{queryset.count()} quotation(s) recalculated successfully.")

    @admin.action(description="🚀 Convert accepted quotes to Bookings")
    def convert_to_bookings(self, request, queryset):
        converted = 0
        for q in queryset:
            if not q.booking:
                q.convert_to_booking(user=request.user)
                converted += 1
        self.message_user(request, f"{converted} quotation(s) converted to confirmed operational Bookings.")


# ==============================================================================
#  4. Phase B Admin — FTO, Corporate, Supplier & Vouchers
# ==============================================================================

class PartyContactPersonInline(TabularInline):
    model = PartyContactPerson
    extra = 1
    fields = ('name', 'designation', 'contact_type', 'phone', 'mobile', 'email', 'is_primary')


@admin.register(PartnerProfile)
class PartnerProfileAdmin(ModelAdmin):
    list_display = ('party_name', 'category_badge', 'trade_name', 'credit_limit_display', 'pan_number', 'agreement_status', 'created_at')
    list_filter = ('category', 'agreement_valid_until')
    search_fields = ('party__name', 'trade_name', 'pan_number', 'iata_number', 'bank_name')
    raw_id_fields = ('party',)

    fieldsets = (
        ('1. Core Partner Identity & Tier', {
            'fields': (('party', 'category'), ('trade_name', 'iata_number'), 'pan_number')
        }),
        ('2. Credit & Settlement Terms', {
            'fields': ('credit_limit',)
        }),
        ('3. Bank Account & Remittance Info', {
            'fields': (
                ('bank_beneficiary_name', 'bank_name'),
                ('bank_account_number', 'bank_ifsc'),
                ('bank_branch', 'swift_bic')
            )
        }),
        ('4. Legal Agreements & Contracts', {
            'fields': (
                'agreement_file',
                ('agreement_valid_from', 'agreement_valid_until'),
                'contract_notes'
            )
        }),
    )

    @admin.display(description='Partner / Agency Name')
    def party_name(self, obj):
        return obj.party.name

    @admin.display(description='Tier Category')
    def category_badge(self, obj):
        colors = {
            'diamond': '#0ea5e9',
            'gold': '#eab308',
            'silver': '#94a3b8',
            'corporate_mnc': '#8b5cf6',
            'b2b_local': '#10b981',
        }
        color = colors.get(obj.category, '#64748b')
        return format_html(
            '<span class="badge" style="background-color: {}; color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, obj.get_category_display()
        )

    @admin.display(description='Credit Limit')
    def credit_limit_display(self, obj):
        return format_html('<b>₹{}</b>', f"{obj.credit_limit:,.0f}")

    @admin.display(description='Agreement')
    def agreement_status(self, obj):
        if obj.agreement_file:
            return mark_safe('<span style="color: #10b981;">📄 Uploaded</span>')
        return mark_safe('<span style="color: #94a3b8;">None</span>')


@admin.register(B2CCustomerProfile)
class B2CCustomerProfileAdmin(ModelAdmin):
    list_display = ('full_name', 'vip_badge', 'nationality', 'phone_display', 'city', 'passport_number', 'created_at')
    list_filter = ('is_vip', 'nationality', 'state')
    search_fields = ('full_name', 'party__name', 'party__phone', 'party__email', 'passport_number', 'city')
    raw_id_fields = ('party',)

    fieldsets = (
        ('1. Traveler Personal Profile', {
            'fields': (('party', 'full_name'), ('alternate_phone', 'nationality'), 'is_vip')
        }),
        ('2. International Travel & Identity Credentials', {
            'fields': (('passport_number', 'passport_expiry'), ('date_of_birth', 'anniversary_date'))
        }),
        ('3. Residence Address', {
            'fields': (('city', 'state', 'pincode'),)
        }),
        ('4. Social Media Footprint', {
            'fields': (('facebook_url', 'instagram_handle'), ('linkedin_url', 'twitter_handle'))
        }),
        ('5. Refund & Deposit Bank Account', {
            'fields': (('refund_bank_name', 'refund_account_no', 'refund_ifsc'),)
        }),
    )

    @admin.display(description='VIP')
    def vip_badge(self, obj):
        if obj.is_vip:
            return mark_safe('<span class="badge" style="background: #e11d48; color: #fff; padding: 2px 6px; border-radius: 4px;">👑 VIP</span>')
        return mark_safe('<span style="color: #94a3b8;">Standard</span>')

    @admin.display(description='Phone')
    def phone_display(self, obj):
        return obj.party.phone or obj.alternate_phone or '-'


class SupplierContractedRateInline(TabularInline):
    model = SupplierContractedRate
    extra = 1
    fields = ('service_category', 'service_name', 'room_type', 'meal_plan', 'seasonality', 'rack_rate', 'contracted_buy_rate', 'is_active')


@admin.register(SupplierProfile)
class SupplierProfileAdmin(ModelAdmin):
    list_display = ('supplier_name', 'type_badge', 'destination_city', 'rates_count', 'preferred_badge', 'contract_status')
    list_filter = ('supplier_type', 'destination_city', 'is_preferred')
    search_fields = ('party__name', 'trade_name', 'destination_city', 'gstin', 'pan_number')
    raw_id_fields = ('party',)
    inlines = [SupplierContractedRateInline]

    fieldsets = (
        ('1. Supplier Entity & Classification', {
            'fields': (('party', 'supplier_type'), ('trade_name', 'destination_city'), 'is_preferred')
        }),
        ('2. Statutory & Tax Registration', {
            'fields': (('pan_number', 'gstin'),)
        }),
        ('3. Payout Bank Information', {
            'fields': (
                ('bank_beneficiary_name', 'bank_name'),
                ('bank_account_number', 'bank_ifsc'),
                'bank_branch'
            )
        }),
        ('4. DMC Master Contract', {
            'fields': (
                'contract_document',
                ('contract_valid_from', 'contract_valid_until')
            )
        }),
    )

    @admin.display(description='Supplier Name')
    def supplier_name(self, obj):
        return obj.party.name

    @admin.display(description='Supplier Type')
    def type_badge(self, obj):
        return format_html('<span class="badge" style="background: #0d9488; color: #fff; padding: 3px 8px; border-radius: 4px;">{}</span>', obj.get_supplier_type_display())

    @admin.display(description='Preferred')
    def preferred_badge(self, obj):
        if obj.is_preferred:
            return mark_safe('<span style="color: #10b981; font-weight: 700;">★ Preferred</span>')
        return mark_safe('<span style="color: #94a3b8;">Standard</span>')

    @admin.display(description='Contract Rates')
    def rates_count(self, obj):
        return f"{obj.contracted_rates.count()} tariff(s)"

    @admin.display(description='Contract Document')
    def contract_status(self, obj):
        if obj.contract_document:
            return mark_safe('<span style="color: #10b981;">📄 Signed</span>')
        return mark_safe('<span style="color: #94a3b8;">Pending</span>')


@admin.register(SupplierContractedRate)
class SupplierContractedRateAdmin(ModelAdmin):
    list_display = ('supplier_name', 'service_name', 'seasonality_badge', 'room_type', 'meal_plan', 'rack_rate_display', 'contracted_rate_display', 'savings_display', 'is_active')
    list_filter = ('seasonality', 'service_category', 'is_active')
    search_fields = ('service_name', 'supplier__party__name', 'room_type')

    @admin.display(description='Supplier')
    def supplier_name(self, obj):
        return obj.supplier.party.name

    @admin.display(description='Seasonality')
    def seasonality_badge(self, obj):
        colors = {'peak': '#ef4444', 'regular': '#3b82f6', 'offpeak': '#10b981'}
        color = colors.get(obj.seasonality, '#64748b')
        return format_html('<span class="badge" style="background: {}; color: #fff; padding: 2px 6px; border-radius: 4px;">{}</span>', color, obj.get_seasonality_display())

    @admin.display(description='Rack Rate')
    def rack_rate_display(self, obj):
        return format_html('<span style="text-decoration: line-through; color: #94a3b8;">₹{}</span>', f"{obj.rack_rate:,.0f}")

    @admin.display(description='DMC Buy Rate')
    def contracted_rate_display(self, obj):
        return format_html('<b style="color: #10b981;">₹{}</b>', f"{obj.contracted_buy_rate:,.0f}")

    @admin.display(description='Savings')
    def savings_display(self, obj):
        return format_html('<span style="color: #0284c7; font-weight: 600;">{}% Margin</span>', obj.savings_percent)


@admin.register(SupplierServiceVoucher)
class SupplierServiceVoucherAdmin(ModelAdmin):
    list_display = ('voucher_number', 'voucher_type_badge', 'supplier_name', 'guest_name', 'dates_display', 'settlement_display', 'status_badge', 'actions_display')
    list_filter = ('status', 'voucher_type', 'service_date_start')
    search_fields = ('voucher_number', 'guest_name', 'supplier__party__name', 'confirmation_reference')
    readonly_fields = ('voucher_number', 'confirmation_token', 'issued_at', 'confirmed_at', 'created_at', 'updated_at')
    actions = ['issue_vouchers', 'confirm_vouchers']

    fieldsets = (
        ('1. Voucher Identity & Beneficiary Supplier', {
            'fields': (('voucher_number', 'voucher_type'), ('supplier', 'status'), ('quotation', 'booking'))
        }),
        ('2. Passenger & Stay Details', {
            'fields': (
                ('guest_name', 'guest_phone', 'pax_count'),
                ('service_date_start', 'service_date_end', 'duration_nights')
            )
        }),
        ('3. Service Specifications', {
            'fields': (
                ('hotel_room_type', 'hotel_meal_plan', 'room_count'),
                ('vehicle_type_name', 'pickup_time'),
                ('pickup_location', 'drop_location'),
                'activity_name',
                'special_instructions'
            )
        }),
        ('4. Settlement & Financial Obligations', {
            'fields': (
                ('contracted_unit_cost', 'total_payable_to_supplier'),
                'payment_terms'
            )
        }),
        ('5. Supplier Extranet Confirmation', {
            'fields': (
                ('confirmation_reference', 'confirmed_at'),
                ('confirmation_token', 'issued_at'),
                'supplier_notes'
            )
        }),
    )

    @admin.display(description='Type')
    def voucher_type_badge(self, obj):
        return obj.get_voucher_type_display()

    @admin.display(description='Supplier')
    def supplier_name(self, obj):
        return obj.supplier.party.name

    @admin.display(description='Service Window')
    def dates_display(self, obj):
        return f"{obj.service_date_start} to {obj.service_date_end} ({obj.duration_nights}N)"

    @admin.display(description='Payable to Supplier')
    def settlement_display(self, obj):
        return format_html('<b style="color: #0f766e;">₹{}</b>', f"{obj.total_payable_to_supplier:,.2f}")

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'draft': '#64748b',
            'issued': '#f59e0b',
            'confirmed': '#10b981',
            'amended': '#8b5cf6',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html('<span class="badge" style="background: {}; color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>', color, obj.get_status_display())

    @admin.display(description='Actions')
    def actions_display(self, obj):
        return format_html(
            '<a href="/crm/vouchers/{}/" target="_blank" class="button" style="padding: 3px 8px; font-size: 11px; background: #0284c7; color: #fff; border-radius: 4px; text-decoration: none;">'
            '📄 View Voucher</a>',
            obj.id
        )

    @admin.action(description="🚀 Issue selected vouchers to suppliers (Fires WhatsApp/Email)")
    def issue_vouchers(self, request, queryset):
        issued = 0
        for vch in queryset.filter(status='draft'):
            vch.status = 'issued'
            vch.issued_at = timezone.now()
            vch.save()
            issued += 1
        self.message_user(request, f"{issued} voucher(s) issued and dispatched to suppliers.")

    @admin.action(description="✅ Mark selected vouchers as Confirmed")
    def confirm_vouchers(self, request, queryset):
        confirmed = queryset.filter(status='issued').update(
            status='confirmed',
            confirmed_at=timezone.now()
        )
        self.message_user(request, f"{confirmed} voucher(s) marked as confirmed.")


@admin.register(DmcTask)
class DmcTaskAdmin(ModelAdmin):
    list_display = ('title', 'priority_badge', 'assigned_to', 'due_date', 'status_badge', 'overdue_badge')
    list_filter = ('status', 'priority', 'due_date', 'assigned_to')
    search_fields = ('title', 'description', 'assigned_to__username')

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        colors = {'urgent': '#ef4444', 'high': '#f97316', 'medium': '#eab308', 'low': '#10b981'}
        color = colors.get(obj.priority, '#64748b')
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', color, obj.get_priority_display())

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'pending': '#64748b', 'in_progress': '#3b82f6', 'completed': '#10b981', 'cancelled': '#ef4444'}
        color = colors.get(obj.status, '#64748b')
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', color, obj.get_status_display())

    @admin.display(description='SLA')
    def overdue_badge(self, obj):
        if obj.is_overdue:
            return mark_safe('<span style="color:#ef4444; font-weight:700;">⚠️ Overdue</span>')
        return mark_safe('<span style="color:#10b981;">On Schedule</span>')


@admin.register(FlightMaster)
class FlightMasterAdmin(ModelAdmin):
    list_display = ('airline', 'flight_number', 'origin_airport', 'destination_airport', 'departure_time', 'arrival_time', 'cabin_class', 'is_active')
    list_filter = ('airline', 'origin_airport', 'destination_airport', 'cabin_class', 'is_active')
    search_fields = ('airline', 'flight_number', 'origin_airport', 'destination_airport')


@admin.register(DmcDocument)
class DmcDocumentAdmin(ModelAdmin):
    list_display = ('title', 'category_badge', 'uploaded_by', 'created_at', 'download_link')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')

    @admin.display(description='Category')
    def category_badge(self, obj):
        return format_html('<span style="font-weight:600;">{}</span>', obj.get_category_display())

    @admin.display(description='Action')
    def download_link(self, obj):
        if obj.document_file:
            return format_html('<a href="{}" target="_blank" style="color:#0284c7; font-weight:700; text-decoration:none;">📥 Download File</a>', obj.document_file.url)
        return "No File"


@admin.register(TravelComplaint)
class TravelComplaintAdmin(ModelAdmin):
    list_display = ('complaint_number', 'complainant_name', 'category', 'severity_badge', 'status_badge', 'supplier_involved', 'supplier_rating_awarded', 'lodged_at')
    list_filter = ('status', 'severity', 'category', 'complainant_type')
    search_fields = ('complaint_number', 'complainant_name', 'complainant_phone', 'issue_description')
    actions = ['mark_as_investigating', 'mark_as_resolved']

    @admin.display(description='Severity')
    def severity_badge(self, obj):
        colors = {'critical': '#ef4444', 'high': '#f97316', 'medium': '#eab308', 'low': '#10b981'}
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', colors.get(obj.severity, '#64748b'), obj.get_severity_display())

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'lodged': '#ef4444', 'under_investigation': '#f59e0b', 'supplier_escalated': '#f97316', 'resolved': '#10b981', 'closed': '#64748b'}
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', colors.get(obj.status, '#64748b'), obj.get_status_display())

    @admin.action(description="🔍 Mark selected complaints as Under Investigation")
    def mark_as_investigating(self, request, queryset):
        cnt = queryset.filter(status='lodged').update(status='under_investigation')
        self.message_user(request, f"{cnt} complaint(s) marked under investigation.")

    @admin.action(description="🎉 Mark selected complaints as Resolved")
    def mark_as_resolved(self, request, queryset):
        cnt = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"{cnt} complaint(s) marked as resolved.")


@admin.register(SupplierPaymentRequisition)
class SupplierPaymentRequisitionAdmin(ModelAdmin):
    list_display = ('requisition_number', 'supplier', 'amount_requested', 'payment_type', 'status_badge', 'cost_to_company', 'cost_to_client', 'gross_margin_display', 'created_at')
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = ('requisition_number', 'supplier__company_name', 'invoice_number')
    actions = ['approve_requisitions', 'disburse_requisitions']

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'draft': '#64748b', 'pending_approval': '#f59e0b', 'approved': '#0284c7', 'disbursed': '#10b981', 'rejected': '#ef4444'}
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', colors.get(obj.status, '#64748b'), obj.get_status_display())

    @admin.display(description='Gross Margin')
    def gross_margin_display(self, obj):
        margin = obj.gross_margin
        color = '#10b981' if margin >= 0 else '#ef4444'
        return format_html('<strong style="color:{};">₹{}</strong>', color, f"{margin:,.2f}")

    @admin.action(description="✅ Approve selected requisitions for Payment")
    def approve_requisitions(self, request, queryset):
        cnt = queryset.filter(status='pending_approval').update(status='approved')
        self.message_user(request, f"{cnt} requisition(s) approved for payment.")

    @admin.action(description="💰 Mark selected requisitions as Disbursed/Paid")
    def disburse_requisitions(self, request, queryset):
        cnt = queryset.filter(status='approved').update(status='disbursed', disbursed_at=timezone.now())
        self.message_user(request, f"{cnt} requisition(s) marked as disbursed.")


@admin.register(DmcInvoice)
class DmcInvoiceAdmin(ModelAdmin):
    list_display = ('invoice_number', 'invoice_type_badge', 'billing_name', 'taxable_amount', 'total_tax_amount', 'total_invoice_amount', 'balance_due', 'status_badge', 'invoice_date')
    list_filter = ('invoice_type', 'status', 'tax_regime', 'invoice_date')
    search_fields = ('invoice_number', 'billing_name', 'client_gstin', 'client_pan', 'party__name')
    date_hierarchy = 'invoice_date'

    @admin.display(description='Type')
    def invoice_type_badge(self, obj):
        colors = {'proforma': '#8b5cf6', 'tax_invoice': '#0d9488'}
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', colors.get(obj.invoice_type, '#64748b'), obj.get_invoice_type_display())

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'draft': '#64748b', 'issued': '#0284c7', 'paid': '#10b981', 'partially_paid': '#f59e0b', 'cancelled': '#ef4444'}
        return format_html('<span class="badge" style="background:{}; color:#fff; padding:2px 6px; border-radius:4px;">{}</span>', colors.get(obj.status, '#64748b'), obj.get_status_display())


# ==========================================================================
# Phase 6 — Staff Notification Centre Admin
# ==========================================================================

@admin.action(description="✅ Mark selected notifications as Read")
def mark_all_notifications_read(modeladmin, request, queryset):
    cnt = queryset.update(is_read=True)
    modeladmin.message_user(request, f"{cnt} notification(s) marked as read.")


@admin.action(description="🗑️ Delete all Read notifications")
def delete_read_notifications(modeladmin, request, queryset):
    cnt, _ = queryset.filter(is_read=True).delete()
    modeladmin.message_user(request, f"{cnt} read notification(s) deleted.")


@admin.register(StaffNotification)
class StaffNotificationAdmin(ModelAdmin):
    list_display = ('type_badge', 'title', 'recipient_display', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'body', 'recipient__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    actions = [mark_all_notifications_read, delete_read_notifications]

    @admin.display(description='Type')
    def type_badge(self, obj):
        colors = {
            'new_booking': '#0ea5e9',
            'payment_received': '#10b981',
            'payment_failed': '#ef4444',
            'trip_departing': '#f59e0b',
            'tat_breach': '#f97316',
            'lead_won': '#8b5cf6',
            'lead_lost': '#64748b',
            'task_due': '#ec4899',
            'complaint_lodged': '#dc2626',
            'voucher_confirmed': '#059669',
            'system': '#475569',
        }
        icon = obj.get_notification_type_display().split(' ')[0]
        label = obj.get_notification_type_display()
        color = colors.get(obj.notification_type, '#475569')
        return format_html('<span style="background:{}; color:#fff; padding:3px 8px; border-radius:5px; font-size:.78rem;">{}</span>', color, label)

    @admin.display(description='Recipient')
    def recipient_display(self, obj):
        if obj.recipient:
            return format_html('👤 {}', obj.recipient.username)
        return format_html('<span style="color:#f59e0b;">📢 Broadcast (All Staff)</span>')
