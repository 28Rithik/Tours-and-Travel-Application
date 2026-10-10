from django.db import models
from core.models import Client
from operations.models import Booking

class CustomerDocument(models.Model):
    DOCUMENT_TYPES = [
        ('visa', 'Visa Copy'),
        ('ticket', 'E-Ticket'),
        ('voucher', 'Booking Voucher'),
        ('insurance', 'Travel Insurance'),
        ('other', 'Other Document')
    ]
    customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='customer_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.customer.name}"


class KnowledgeDocument(models.Model):
    """
    RAG Knowledge Document Store for Rathasārathi AI Operations Intelligence.
    Stores policies, packages, tourist spot guides, temple rules, and emergency protocols.
    """
    CATEGORY_CHOICES = [
        ('package_itinerary', '🗺️ Tour Packages & Itinerary Guides'),
        ('policy_rules', '📜 Booking, Night Bata, Toll & Cancellation Policies'),
        ('tourism_guide', '🏛️ Destination Sightseeing, E-Pass & Temple Rules'),
        ('fleet_safety', '🛡️ Chauffeur Safety, Emergency & Breakdown Protocols'),
        ('faq_general', '💡 General Customer & Agent FAQ'),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='package_itinerary')
    source = models.CharField(max_length=150, blank=True, help_text="e.g. Operations Manual 2026, Tourism Circular")
    raw_content = models.TextField(help_text="Full plaintext content or PDF text extract")
    is_active = models.BooleanField(default=True, verbose_name="Active for RAG Retrieval")
    chunk_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "RAG Knowledge Document"
        verbose_name_plural = "RAG Knowledge Documents"
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class KnowledgeChunk(models.Model):
    """
    Individual semantic chunk indexed for hybrid vector/keyword search by Rathasārathi AI.
    """
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField(default=0)
    chunk_title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    keywords = models.TextField(blank=True, help_text="Comma-separated keywords for BM25 matching")
    vector_tfidf = models.JSONField(default=dict, blank=True, help_text="Normalized term frequencies for cosine similarity")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "RAG Knowledge Chunk"
        verbose_name_plural = "RAG Knowledge Chunks"
        ordering = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk #{self.chunk_index}"

