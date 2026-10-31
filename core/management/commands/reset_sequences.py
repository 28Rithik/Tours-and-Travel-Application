"""
Django Management Command to synchronize and align PostgreSQL sequences.
Prevents UniqueViolation primary key conflicts after bulk imports or --keepdb test runs.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Reset all database primary key sequences to match current table max IDs.'

    def handle(self, *args, **options):
        vendor = connection.vendor
        if vendor != 'postgresql':
            self.stdout.write(self.style.WARNING(
                f"Database vendor is '{vendor}'. Sequence resetting is only required for PostgreSQL."
            ))
            return

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE column_default LIKE 'nextval%'
                  AND table_schema = 'public'
                ORDER BY table_name;
            """)
            sequences = cursor.fetchall()

            if not sequences:
                self.stdout.write(self.style.SUCCESS("No auto-increment sequences found."))
                return

            self.stdout.write(f"Aligning {len(sequences)} PostgreSQL table sequences...")
            reset_count = 0
            for table, col in sequences:
                try:
                    cursor.execute(
                        f'SELECT setval(pg_get_serial_sequence(\'{table}\', \'{col}\'), coalesce(max("{col}"), 1) + 1) FROM "{table}";'
                    )
                    reset_count += 1
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  - Skipping {table}.{col}: {exc}"))

            self.stdout.write(self.style.SUCCESS(
                f"Successfully aligned {reset_count}/{len(sequences)} PostgreSQL auto-increment sequences."
            ))

