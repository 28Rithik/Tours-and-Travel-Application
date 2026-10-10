"""
Django Management Command: seed_rag_knowledge_base
Seeds and indexes core operational policies, tour packages, temple guidelines,
and safety manuals into the grounded Rathasārathi RAG Knowledge Base.
"""

from django.core.management.base import BaseCommand
from operations.rag_engine import RAGKnowledgeEngine


class Command(BaseCommand):
    help = 'Seeds and vectorizes operational documents into the Rathasārathi RAG Knowledge Base.'

    def handle(self, *args, **options):
        self.stdout.write("Ingesting and indexing knowledge base documents...")
        chunks_count = RAGKnowledgeEngine.seed_default_knowledge()
        self.stdout.write(self.style.SUCCESS(f"[OK] Successfully indexed {chunks_count} knowledge chunks into RAG engine!"))
