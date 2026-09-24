from django.contrib import admin
from .models import CustomerDocument

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: This model now appears under "Digital Collections & Guest Portal"
# ──────────────────────────────────────────────────────────────────────────

@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'booking', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('title', 'customer__name', 'booking__booking_number')

    def has_module_permission(self, request):
        return False
