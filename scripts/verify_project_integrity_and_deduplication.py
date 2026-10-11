import os
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"c:\Users\rithi\Documents\Documents Project Intership and Course\Projects\Rag chatbot\Tours and Travel Application")
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.apps import apps
from django.contrib import admin
from django.urls import get_resolver
from django.db import connection

print("=" * 80)
print("🔍 SIVA GAYATHRI TOURS & TRAVELS — PROJECT AUDIT & DEDUPLICATION REPORT")
print("=" * 80)

# 1. AUDIT APPS & MODELS
print("\n--- 1. AUDITING REGISTERED APPS & MODELS ---")
all_models = apps.get_models()
print(f"Total installed apps: {len(apps.get_app_configs())}")
print(f"Total registered models: {len(all_models)}")

table_to_models = defaultdict(list)
for m in all_models:
    db_table = m._meta.db_table
    table_to_models[db_table].append(f"{m._meta.app_label}.{m.__name__}")

duplicate_tables = {tbl: m_list for tbl, m_list in table_to_models.items() if len(m_list) > 1}
if duplicate_tables:
    print(f"⚠️ FOUND {len(duplicate_tables)} DB TABLES USED BY MULTIPLE MODELS (e.g. Proxy Models):")
    for tbl, m_list in duplicate_tables.items():
        is_proxy = any(apps.get_model(*m.split('.'))._meta.proxy for m in m_list)
        status = "Intentional Proxy" if is_proxy else "🚨 CONFLICTING CONCRETE TABLES"
        print(f"  • Table '{tbl}': {', '.join(m_list)} -> [{status}]")
else:
    print("  [PASS] All DB tables map uniquely to distinct models.")

# 2. AUDIT ADMIN REGISTRATIONS
print("\n--- 2. AUDITING ADMIN SITE REGISTRATIONS ---")
admin_registry = admin.site._registry
print(f"Total models registered in admin.site: {len(admin_registry)}")

admin_model_names = defaultdict(list)
for model_cls, admin_instance in admin_registry.items():
    admin_model_names[model_cls.__name__].append(f"{model_cls._meta.app_label} ({admin_instance.__class__.__name__})")

duplicate_admin_names = {name: reg_list for name, reg_list in admin_model_names.items() if len(reg_list) > 1}
if duplicate_admin_names:
    print(f"⚠️ Note: {len(duplicate_admin_names)} Model Names exist across different apps:")
    for name, reg_list in duplicate_admin_names.items():
        print(f"  • '{name}': {', '.join(reg_list)}")
else:
    print("  [PASS] All admin registered model names are distinct.")

# 3. AUDIT URL RESOLVER & ROUTE NAMES
print("\n--- 3. AUDITING URL ROUTES & NAMES ---")
resolver = get_resolver()

def list_urls(patterns, prefix=""):
    routes = []
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            routes.extend(list_urls(p.url_patterns, prefix + str(p.pattern)))
        else:
            name = getattr(p, 'name', None)
            full_pattern = prefix + str(p.pattern)
            routes.append((full_pattern, name, getattr(p, 'callback', None)))
    return routes

routes = list_urls(resolver.url_patterns)
print(f"Total URL routes detected: {len(routes)}")

name_to_routes = defaultdict(list)
for pattern, name, cb in routes:
    if name:
        cb_str = f"{cb.__module__}.{cb.__name__}" if cb and hasattr(cb, '__name__') else str(cb)
        name_to_routes[name].append((pattern, cb_str))

duplicate_names = {n: r_list for n, r_list in name_to_routes.items() if len(r_list) > 1}
if duplicate_names:
    print(f"⚠️ Found {len(duplicate_names)} duplicate URL route names across apps/namespaces:")
    for n, r_list in duplicate_names.items():
        patterns_str = "; ".join([f"{pat} ({cb})" for pat, cb in r_list])
        print(f"  • Name '{n}': {patterns_str}")
else:
    print("  [PASS] All URL route names are uniquely resolved.")

# 4. AUDIT TEMPLATE FILES & DETECT DUPLICATES
print("\n--- 4. AUDITING TEMPLATE FILES FOR DUPLICATIONS ---")
templates_dir = BASE_DIR / "templates"
all_html_files = list(templates_dir.rglob("*.html"))
print(f"Total HTML template files: {len(all_html_files)}")

templates_by_name = defaultdict(list)
for tf in all_html_files:
    rel_path = tf.relative_to(templates_dir)
    templates_by_name[tf.name].append(str(rel_path))

duplicate_templates = {name: paths for name, paths in templates_by_name.items() if len(paths) > 1}
if duplicate_templates:
    print(f"ℹ️ Found {len(duplicate_templates)} template filenames used in multiple directories:")
    for name, paths in duplicate_templates.items():
        print(f"  • '{name}': {', '.join(paths)}")
else:
    print("  [PASS] All template file basenames are unique.")

print("\n" + "=" * 80)
print("AUDIT SUMMARY COMPLETE")
print("=" * 80)
