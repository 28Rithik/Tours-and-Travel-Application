from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CustomerDocument, KnowledgeDocument, KnowledgeChunk

# ──────────────────────────────────────────────────────────────────────────
# HIDDEN: This model now appears under "Digital Collections & Guest Portal"
# ──────────────────────────────────────────────────────────────────────────

@admin.register(CustomerDocument)
class CustomerDocumentAdmin(ModelAdmin):
    list_display = ('title', 'customer', 'booking', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('title', 'customer__name', 'booking__booking_number')

    def has_module_permission(self, request):
        return False


class KnowledgeChunkInline(admin.TabularInline):
    from .models import KnowledgeChunk
    model = KnowledgeChunk
    extra = 0
    fields = ('chunk_index', 'chunk_title', 'keywords', 'content')
    readonly_fields = ('chunk_index',)


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(ModelAdmin):
    from .models import KnowledgeDocument
    list_display = ('title', 'category', 'chunk_count', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'updated_at')
    search_fields = ('title', 'raw_content', 'source')
    readonly_fields = ('chunk_count', 'created_at', 'updated_at')
    inlines = [KnowledgeChunkInline]

