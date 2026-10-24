# 🛠️ SIVA GAYATHRI TOURS & TRAVELS — SCRIPTS CATALOG

This directory contains database seeders, GIS/OSRM infrastructure tools, comprehensive test suites, and data import pipelines for the **TravelERP** platform.

Every script in this directory has been validated for syntax integrity with Python 3.12 (`compileall` check: 0 errors).

---

## 📑 Functional Script Categories

### 1. Database Seeders (`seed_*.py`)
Used to bootstrap, provision, and populate the system with realistic operational records:

| Seeder Script | Functional Domain |
| :--- | :--- |
| `seed_comprehensive_packages.py` | Populates 6,000+ tour packages, itineraries, and tariffs |
| `seed_enterprise_staff_roster.py` | Sets up 13 enterprise personas with RBAC roles and approval ceilings |
| `seed_enterprise_fleet_vehicles.py`| Seeds commercial vehicles with FASTag IDs, fuel specs, and GPS tokens |
| `seed_full_user_fleet_catalog.py` | Builds complete vehicle catalog with pricing matrices |
| `seed_category_specifications.py` | Sets luggage capacities, passenger seats, and comfort amenities |
| `seed_vehicle_categories.py` | Populates core vehicle taxonomy (Sedan, MPV, Tempo, Bus, Coach) |
| `seed_chart_of_accounts.py` | Seeds standard double-entry General Ledger chart of accounts |
| `seed_crm_marketing_data.py` | Seeds realistic CRM leads, pipeline stages, and inquiries |
| `seed_fleet_contracts_data.py` | Generates recurring IT park / university employee commute contracts |
| `seed_live_operations_ecosystem.py`| Initializes live duty slips, GPS tokens, and dispatch states |
| `seed_gateway_configs.py` | Configures dynamic UPI QR, Razorpay test credentials, and webhooks |
| `seed_kerala_iv.py` | Seeds multi-bus student Industrial Visit (IV) expedition |
| `seed_shakthi_mega_iv.py` | Seeds large-scale 12-coach college expedition |
| `seed_safety_and_commuters.py` | Seeds female night shift commuters and security escort pairs |
| `seed_licenses.py` | Populates commercial driver licenses and RTO badges |

---

### 2. GIS Stack, Routing Engine & Database Migrations
Infrastructure automation for local GIS servers, offline maps, and database transitions:

| Infrastructure Tool | Description |
| :--- | :--- |
| `manage_gis_stack.py` | Manages local PostGIS, TileServer-GL, and OSRM container health |
| `setup_osrm_india.py` | Downloads and configures the Open Source Routing Machine India profile |
| `migrate_to_postgres.py` | Migrates data from development SQLite to production PostgreSQL 15 |
| `start_postgres_and_migrate.bat`| One-click Windows batch launcher for PostgreSQL service & migration |
| `download_full_india_map.py` | Retrieves OSM PBF vector map extracts for offline cartography |
| `pregenerate_regional_tiles.py` | Caches South India map tiles for sub-second offline rendering |

---

### 3. Comprehensive Verification & Regression Suites (`verify_*.py`, `test_*.py`)
End-to-end audit scripts that validate system stability, forms, UI styling, and routes:

| Verification Suite | Target Areas |
| :--- | :--- |
| `full_a_to_z_smoke_test.py` | Master smoke test verifying every view and URL in the project |
| `master_8phase_e2e_verification.py` | End-to-end functional audit across all 8 operational phases |
| `master_ui_forms_js_verification.py`| Inspects all HTML forms, input field validations, and JavaScript |
| `test_end_to_end_erp_complete.py` | Simulates customer booking ➔ dispatch ➔ execution ➔ billing |
| `test_all_forms_edge_cases_and_anomalies.py` | Edge-case input testing (negative values, zero division, overlaps) |
| `e2e_full_platform_audit.py` | Complete platform sanity check across staff portals and admin |
| `verify_project_integrity_and_deduplication.py` | Ensures zero model collision and deduplicated routing tables |
| `test_fleet_commute_5phases.py` | Validates corporate commute clustering, TSP 2-Opt, and IVR |
| `test_gst_ewaybill_studio.py` | Verifies B2B GST tax calculation and NIC E-Way Bill schema |
| `test_payment_gateway_gl_studio.py`| Verifies dynamic UPI QR generation and General Ledger balance |

---

### 4. Data Import & Catalog Ingestion Pipelines (`import_*.py`, `ingest_*.py`)
ETL pipelines that imported and normalized thousands of authentic tour circuits:

| Import Pipeline | Source / Dataset |
| :--- | :--- |
| `import_chennai_complete.py` | Ingests comprehensive Chennai & South India holiday catalog |
| `import_all_chennaitourstravels.py` | Imports pilgrimage circuits and heritage packages |
| `import_rengha_catalog.py` | Normalizes Madurai, Theni, and Kodaikanal holiday circuits |
| `import_sblt_packages.py` | Imports South Indian bus tour and coastal packages |
| `ingest_complete_trawell_catalog.py`| Ingests pan-India hill station and nature destination packages |
| `export_all_tour_packages_to_excel.py` | Exports all tour packages into master Excel spreadsheets |

---

### 5. Diagnostics, Telematics & Inspection Utilities (`inspect_*.py`, `check_*.py`)
Field diagnostic tools used for telemetry validation, category cross-referencing, and audits:

| Diagnostic Script | Purpose |
| :--- | :--- |
| `inspect_admin_row.py` | Inspects Django Unfold table rendering and inline forms |
| `check_all_divisions.py` | Validates arithmetic calculations against zero-division errors |
| `check_js.py` | Static syntax analysis of embedded and static JavaScript files |
| `audit_all_fleet_forms.py` | Audits vehicle and chauffeur input validation rules |
| `comprehensive_category_audit.py` | Cross-references vehicle seat capacities against pricing slabs |

---

## 🚀 Execution Guide

Run any script using the project's Python interpreter:

```powershell
# Windows PowerShell:
& "C:\Users\rithi\AppData\Local\Programs\Python\Python312\python.exe" scripts/<script_name>.py

# Example: Run the master smoke test
& "C:\Users\rithi\AppData\Local\Programs\Python\Python312\python.exe" scripts/full_a_to_z_smoke_test.py
```
