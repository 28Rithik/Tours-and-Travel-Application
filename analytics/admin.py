from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html, mark_safe
from .models import DriverScorecard, ReportLog
from .services import calculate_driver_scorecard


@admin.action(description="⚡ Recalculate Driver Performance Scorecards")
def recalculate_scorecards(modeladmin, request, queryset):
    updated = 0
    for card in queryset:
        calculate_driver_scorecard(card.driver, start_date=card.month)
        updated += 1
    modeladmin.message_user(request, f"{updated} driver scorecard(s) recalculated with live duty metrics.")


@admin.register(DriverScorecard)
class DriverScorecardAdmin(ModelAdmin):
    list_display = (
        'driver_link',
        'month_display',
        'grade_badge',
        'overall_score_bar',
        'punctuality_display',
        'safety_display',
        'rating_stars',
        'fuel_display',
        'total_trips',
        'total_kms_display',
    )
    list_filter = ('grade', 'period_type', 'month')
    search_fields = ('driver__name', 'driver__phone')
    autocomplete_fields = ['driver']
    actions = [recalculate_scorecards]
    date_hierarchy = 'month'
    readonly_fields = ('computed_at',)

    fieldsets = (
        ("Captain & Evaluation Period", {
            "fields": (
                "driver",
                ("month", "period_type"),
                ("overall_composite_score", "grade"),
            )
        }),
        ("1. Punctuality & Reliability (25% Weight)", {
            "fields": (
                ("total_trips", "completed_trips"),
                ("on_time_trips", "delayed_trips"),
                "punctuality_score",
            )
        }),
        ("2. Safety & Infractions (30% Weight)", {
            "fields": (
                ("overspeeding_count", "harsh_braking_count"),
                ("traffic_fines_count", "total_fine_amount"),
                "safety_score",
            )
        }),
        ("3. Guest Rating & Hospitality (25% Weight)", {
            "fields": (
                ("feedback_count", "average_rating"),
                "customer_rating_score",
            )
        }),
        ("4. Fuel Eco-Driving Efficiency (20% Weight)", {
            "fields": (
                "total_kms_driven",
                ("expected_fuel_litres", "actual_fuel_litres"),
                "fuel_efficiency_score",
            )
        }),
        ("Audit & Notes", {
            "fields": (
                "notes",
                "computed_at",
            )
        }),
    )

    @admin.display(description="Captain", ordering='driver__name')
    def driver_link(self, obj):
        return format_html(
            '<a href="/admin/core/driver/{}/change/" style="font-weight:700; color:#38bdf8;">👨‍✈️ {}</a>',
            obj.driver.pk, obj.driver.name
        )

    @admin.display(description="Period", ordering='month')
    def month_display(self, obj):
        return obj.month.strftime('%b %Y')

    @admin.display(description="Grade", ordering='grade')
    def grade_badge(self, obj):
        styles = {
            'A+': ('#059669', '#d1fae5', '⭐ A+ Elite'),
            'A': ('#10b981', '#ecfdf5', '🟢 A Excellent'),
            'B': ('#2563eb', '#eff6ff', '🔵 B Standard'),
            'C': ('#d97706', '#fef3c7', '🟡 C Needs Help'),
            'D': ('#dc2626', '#fee2e2', '🔴 D High Risk'),
        }
        fg, bg, label = styles.get(obj.grade, ('#4b5563', '#f3f4f6', obj.grade))
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 10px; border-radius:12px; font-weight:800; font-size:11px;">{}</span>',
            bg, fg, label
        )

    @admin.display(description="Score (Composite)", ordering='overall_composite_score')
    def overall_score_bar(self, obj):
        score = float(obj.overall_composite_score)
        color = '#10b981' if score >= 85 else ('#3b82f6' if score >= 70 else ('#f59e0b' if score >= 55 else '#ef4444'))
        return format_html(
            '<div style="width:110px; display:inline-block;">'
            '<div style="background:#334155; border-radius:6px; height:8px; overflow:hidden; margin-bottom:3px;">'
            '<div style="background:{}; width:{}%; height:100%;"></div>'
            '</div>'
            '<span style="font-weight:700; font-size:11px; color:{};">{}%</span>'
            '</div>',
            color, min(100, score), color, obj.overall_composite_score
        )

    @admin.display(description="Punctuality (25%)")
    def punctuality_display(self, obj):
        return f"{obj.punctuality_score}%"

    @admin.display(description="Safety (30%)")
    def safety_display(self, obj):
        color = '#10b981' if obj.safety_score >= 85 else ('#f59e0b' if obj.safety_score >= 60 else '#ef4444')
        return format_html('<span style="color:{}; font-weight:700;">{}%</span>', color, obj.safety_score)

    @admin.display(description="Guest Rating (25%)")
    def rating_stars(self, obj):
        return format_html('<span style="color:#fbbf24; font-weight:700;">★ {}</span> <small style="color:#94a3b8;">({} reviews)</small>', obj.average_rating, obj.feedback_count)

    @admin.display(description="Fuel Eco (20%)")
    def fuel_display(self, obj):
        return f"{obj.fuel_efficiency_score}%"

    @admin.display(description="Total KM Driven")
    def total_kms_display(self, obj):
        return f"{obj.total_kms_driven:,} KM"


@admin.register(ReportLog)
class ReportLogAdmin(ModelAdmin):
    list_display = ('report_name', 'generated_at', 'generated_by')
    readonly_fields = ('generated_at',)
