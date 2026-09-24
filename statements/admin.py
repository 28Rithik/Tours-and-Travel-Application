from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import GeneratedStatement

@admin.action(description="Download PDF")
def download_pdf_action(modeladmin, request, queryset):
	from django.http import HttpResponseRedirect
	for obj in queryset:
		if obj.file_format == 'pdf':
			return HttpResponseRedirect(reverse('download-statement', args=[obj.id]))
		else:
			modeladmin.message_user(request, "Selected statement is an Excel file, not PDF.", level='WARNING')
	return None

@admin.register(GeneratedStatement)
class GeneratedStatementAdmin(admin.ModelAdmin):
	list_display = ('generated_at', 'party', 'transport_contract', 'from_date', 'to_date', 'file_format', 'closing_balance', 'display_amount_due', 'status', 'download_link')
	list_filter = ('file_format', 'status', 'generated_at')
	search_fields = ('party__name', 'transport_contract__name')
	date_hierarchy = 'generated_at'
	change_list_template = "admin/statements/generatedstatement/change_list.html"
	actions = [download_pdf_action]

	def display_amount_due(self, obj):
		return obj.amount_due
	display_amount_due.short_description = "Amount Due"

	def download_link(self, obj):
		url = reverse('download-statement', args=[obj.pk])
		return format_html('<a class="button" href="{}" target="_blank" style="padding:5px; background:#4CAF50; color:white; font-weight:bold; border-radius:4px; text-decoration:none;">📥 Download</a>', url)
	download_link.short_description = "Action"

	def get_search_results(self, request, queryset, search_term):
		queryset, use_distinct = super().get_search_results(request, queryset, search_term)
		if 'party_id' in request.GET and request.GET['party_id']:
			queryset = queryset.filter(party_id=request.GET['party_id'])
		return queryset, use_distinct
