"""
operations/management/commands/audit_database_integrity.py

Automated End-to-End Database Integrity, Normalization & Form Validation Auditor.
"""

import json
from django.core.management.base import BaseCommand
from operations.database_health_service import run_full_database_health_audit


class Command(BaseCommand):
    help = "Conducts a full end-to-end database check, normalization audit, and form validation verification."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output results as a structured JSON object')
        parser.add_argument('--deep', action='store_true', help='Perform deep entity relationship linkage checks')

    def handle(self, *args, **options):
        is_json = options.get('json', False)
        is_deep = options.get('deep', False)

        report = run_full_database_health_audit(is_deep=is_deep)

        if is_json:
            self.stdout.write(json.dumps(report, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("  TRAVEL ERP — DATABASE INTEGRITY, NORMALIZATION & FORM AUDIT REPORT")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Timestamp: {report['timestamp']}")
        self.stdout.write(f"System Health: {self.style.SUCCESS('100% HEALTHY') if report['status'] == 'HEALTHY' else self.style.WARNING('WARNINGS DETECTED')}\n")

        self.stdout.write("DATABASE ENTITY POPULATION:")
        self.stdout.write("-" * 80)
        keys = list(report["counts"].keys())
        for i in range(0, len(keys), 3):
            line = ""
            for k in keys[i:i+3]:
                line += f"  {k.replace('_', ' ').title():<18}: {report['counts'][k]:<10}"
            self.stdout.write(line)

        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("CHECK CATEGORIES & TELEMETRY:")
        self.stdout.write("-" * 80)

        for cat_name, cat_data in report["audits"].items():
            cat_title = cat_data.get("title", cat_name.replace("_", " ")).upper()
            status_badge = self.style.SUCCESS("[ PASS ]") if cat_data["passed"] else self.style.ERROR("[ FAIL ]")
            self.stdout.write(f"\n{status_badge} {cat_title}")
            for chk in cat_data.get("checks", []):
                chk_badge = "[OK]" if chk["passed"] else "[X]"
                self.stdout.write(f"    {chk_badge} {chk['title']}: {chk['detail']}")

        self.stdout.write("\n" + "=" * 80)
        s = report["summary"]
        self.stdout.write(f"TOTAL CHECKS: {s['total_checks']}  |  PASSED: {self.style.SUCCESS(str(s['passed_checks']))}  |  FAILED: {s['failed_checks']}  |  COMPLIANCE: {s['compliance_pct']}%")
        self.stdout.write("=" * 80 + "\n")
