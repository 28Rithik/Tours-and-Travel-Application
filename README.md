# 🌐 SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
### Enterprise Omnichannel Fleet Dispatch, Tour Operations & Accounting ERP

[![Django](https://img.shields.io/badge/Django-5.1.5-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django Unfold](https://img.shields.io/badge/Admin-Django%20Unfold%200.40-0284C7?style=for-the-badge)](https://github.com/unfoldadmin/django-unfold)
[![Architecture](https://img.shields.io/badge/Stack-ASGI%20%2F%20Channels%20%2B%20HTMX-6366F1?style=for-the-badge)](https://channels.readthedocs.io/)
[![Database](https://img.shields.io/badge/Database-SQLite%20WAL%20%2F%20PostgreSQL%2015%20%2B%20PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Performance](https://img.shields.io/badge/Latency-Sub--50ms%20%2842.43ms%29-10B981?style=for-the-badge)](documentation/performance_analysis.md)
[![Offline-First](https://img.shields.io/badge/Assets-100%25%20Self--Hosted%20%2F%20Zero--CDN-0284C7?style=for-the-badge)](documentation/07_LIGHT_MODE_AND_AESTHETICS_SYSTEM.md)
[![Compression](https://img.shields.io/badge/GZip%20Wire%20Savings-81.5%25-6366F1?style=for-the-badge)](documentation/performance_analysis.md)

---

## 📖 Executive Summary

**TravelERP** is an enterprise-grade, omnichannel fleet management and travel operations ERP built for **Siva Gayathri Tours & Travels**. Operating across South India (Tamil Nadu, Kerala, Karnataka, Andhra Pradesh, Puducherry) and All-India national tour circuits, the platform coordinates a commercial fleet of **300+ vehicles** (Sedans, Innova Crysta MPVs, Tempo Travellers, Urbanias, Mini Buses, and 54-Seater Luxury Coaches).

The system delivers an **end-to-end omnichannel architecture across 4 synchronized interfaces**:
1. **Operations & Executive Cockpit**: Standardized on the modern Django Unfold Admin design language with solid gradient KPI cards, universal command palettes, and real-time dispatch studios.
2. **Public Customer Self-Service Portal (`/customer-portal/`)**: Customer package booking, vehicle rate cards, instant fare estimators, and tour inquiries.
3. **Chauffeur Mobile PWA Portal (`/driver-portal/`)**: Mobile-first vehicle handover inspection, digital odometer logging, expense wallets, and live duty execution.
4. **Interactive Guest Companions & Digital Proposals (`/tour/itinerary/<token>/`, `/quote/<token>/`)**: Zero-login mobile companions accessible via SMS/WhatsApp magic links.

The application operates with a **Zero-CDN, 100% locally self-hosted asset architecture**, delivering an average live response latency of **42.43 ms** with **81.5% GZip wire compression**.

---

## 🚀 Key Modules & Capabilities

### 1. Real-Time Dispatch Control & Operations Studios
* **Dispatch Control Center (`/dispatch/`)**: Real-time cockpit managing unassigned, assigned, in-transit, and completed duty slips. Features Unfold solid gradient KPI cards, instant tab filters, and full search.
* **Interstate State Border Permit Sentry (`/operations/border-permits/`)**: Automatically detects cross-border routes, calculates seating-based check-post tax, and tracks Parivahan AITP compliance.
* **Chauffeur Fatigue & Duty Rest Sentry (`/operations/driver-fatigue-sentry/`)**: Tracks continuous driving hours, enforces statutory 8h rest periods, and flags night-shift or Ghat road (Ooty/Kodaikanal) risks with dispatch lockouts.
* **Trip Cash Advance & Kharcha Envelope Studio (`/operations/cash-envelopes/`)**: Digital floats issued per trip with verified on-road logging of diesel, tolls, state taxes, and driver bata.
* **Highway Breakdown & SOS Emergency Relief (`/operations/breakdown-sos/`)**: Emergency coordination room with GPS landmark logging, passenger distress monitoring, and 1-click replacement vehicle dispatch.
* **Parivahan RTO E-Challan Sentry (`/operations/echallan-sentry/`)**: Synchronizes highway traffic fines, allocates liability (driver deduction vs. company overhead), and reconciles payments.
* **Empty-Leg Return Optimizer (`/operations/empty-legs/`)**: Discovers deadhead return corridors (e.g. Madurai ➔ Chennai) to monetize unbooked seats at discounted rates above fuel/toll costs.
* **Fleet Statutory Compliance Watchdog (`/operations/statutory-compliance/`)**: Actively monitors Fitness (FC), Commercial Insurance, Road Tax, Tourist Permits, and PUC with zero-tolerance dispatch locks.
* **Flight & Train PNR Arrival Manifest (`/operations/pnr-arrivals/`)**: Live flight and Vande Bharat train tracking, chauffeur airport gate coordination, and placard display management.

### 2. Fleet & Chauffeur Directory
* **Vehicle Fleet Roster (`/fleet/vehicles/`)**: Complete commercial vehicle directory with fuel type, seating capacity, FASTag wallet linkage, GPS tracker IMEI, and fitness status.
* **Chauffeur Directory (`/fleet/drivers/`)**: Driver licensing (Badge TR/HMV), police verification, emergency contacts, biometric IDs, and safety scorecards.
* **Fleet Taxonomy & Hierarchy (`/fleet/categories/`, `/fleet/types/`)**: Structured vehicle categorization from Compact Sedans to Luxury Multi-Axle Coaches.

### 3. Maintenance Workshop 4.0
* **2D Vehicle Damage Marker Studio (`/maintenance/damage-marker/`)**: Interactive 2D chassis blueprint (Sedan, SUV, Coach) to pin dents, scratches, and damage severity.
* **2D Axle & Tire Health Studio (`/maintenance/tire-studio/`)**: Visual axle diagrams with color-coded tread depth wear (<=2.5mm critical alert) and retread tracking.
* **Spare Parts & Consumables Inventory (`/maintenance/parts-inventory/`)**: Warehouse SKU catalog, stock-level sentry, and automated job card allocation.
* **Mechanic Garage Floor Studio (`/maintenance/workshop/`)**: Digital job cards, mechanic assignment, time logging, and parts consumption tracking.

### 4. Corporate Employee Transport (ETS) & Institutional Commute
* **Batch Roster Dispatcher (`/commute/roster-dispatcher/`)**: Capacity matching and route clustering for corporate IT and school commute operations.
* **SLA Performance & Penalty Studio (`/commute/sla-penalties/`)**: Delay breach detection linked directly to corporate billing deductions.
* **Women Safety & Night Escort Command (`/commute/women-safety/`)**: Mandatory security escorts for isolated female drops during night shifts (8 PM - 6 AM).

### 5. Holiday Tour Packages & Industrial Visits (IV)
* **Master Package Catalog**: 6,252+ curated holiday packages across Pilgrimage, Hill Stations, Heritage, and International destinations.
* **Day-by-Day Itinerary Builder (`/trips/<id>/itinerary-builder/`)**: Dynamic drag-and-drop itinerary sequencer with venue coordinates and timing slots.
* **Guest Tour Companion (`/tour/itinerary/<token>/`)**: Zero-login mobile companion accessible via SMS/WhatsApp magic link.
* **College Industrial Visits (IV)**: Special multi-bus expedition coordination with student manifests and faculty liaison.

### 6. Finance, Billing & Accounting
* **Corporate GST B2B Invoicing (`/finance/gst-studio/`)**: Automated CGST/SGST/IGST tax calculation, invoice generation, and e-Way Bill JSON generation.
* **Dynamic UPI QR & Settlement (`/payments/`)**: NPCI-compliant dynamic UPI QR generation with instant webhook payment simulation.
* **Driver Advances & Bata Calculator**: Multi-tier outstation bata calculation based on plain vs. ghat terrain and day/night duty hours.
* **Party Ledger & CAB Statements (`/statements/generate/`)**: High-density landscape multi-page PDF statements with reconciliation sections.

### 7. Rathasārathi AI Operations Copilot
* Sub-second natural language fleet operations assistant powered by Groq Cloud (LLaMA 3.3-70B / Qwen) with local rule fallback.
* 8 live database function calling tools: active tours, compliance expiry alerts, revenue metrics, driver safety, fleet availability, CRM inquiries, trip lookups, and semantic tour package search.

---

## 🎨 Django Unfold Design Language

The entire operational staff portal has been standardized to match the **Django Unfold Admin UI**:
* **Solid Gradient KPI Decks**: `.unfold-kpi-card-solid` cards in 6 calibrated themes (`blue`, `green`, `purple`, `amber`, `rose`, `slate`) with monospace numbers, micro tracking-wider titles, and faint background icons.
* **Standardized Data Tables**: `.unfold-table` with uppercase 11px headers, 1px border grid, subtle hover highlights, and `.unfold-pill-badge` status pills.
* **Multi-Fieldset Form Cards**: `.unfold-form-card` sections with numbered step badges, clean inputs, and sticky action footers (`.unfold-submit-bar`).
* **Universal Search Bar**: `.unfold-search-box` with integrated `<kbd>/</kbd>` keyboard shortcut for instant filtering.
* **Dual Cockpit Aesthetics**: Sunlight-optimized Light Mode for outdoor yard dispatchers and high-contrast Dark Mode for night control desks.

---

## ⚡ Zero-CDN High-Speed Engine & Performance Subsystem

TravelERP is architected for extreme responsiveness and 100% offline-first reliability in remote transport yards:

* **100% Self-Hosted Typography & Static Assets**: Zero runtime CDN scripts or external network dependencies.
  - 6 self-hosted font families (`Plus Jakarta Sans`, `JetBrains Mono`, `Material Symbols Outlined`, `Outfit`, `Space Grotesk`, `Inter`) loaded locally via `@font-face` rules in `static/fonts/fonts.css`.
  - Self-hosted Font Awesome 6.5.1, Leaflet 1.9.4, Chart.js 4.4.4, Alpine.js 3.14.3, and HTMX 1.9.10.
  - Critical font preloading (`<link rel="preload">`) and PWA Service Worker v4 asset caching eliminate font flash (FOUT).
* **In-Memory Caching & Session Acceleration (`cached_db`)**:
  - `SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'` serves authenticated session lookups directly from memory (`LocMemCache` or `Redis`), eliminating 1 SQL query per request across every ERP page.
  - Single consolidated `CACHES` block with Redis connection pooling (`max_connections=50`) and automatic `LocMemCache` fallback.
* **SQLite WAL Concurrency Engine**:
  - Configured with `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=10000; PRAGMA temp_store=MEMORY;`, enabling simultaneous non-blocking reads and concurrent writes during rapid HTMX partial refreshes.
* **Database Query Consolidation**:
  - Main operations dashboard aggregates trip and fleet metrics via conditional SQL (`Count(filter=Q(...))`) in a single query instead of 6 separate scans.
  - Chauffeur Fatigue Sentry and Breakdown SOS Studio compute fleet statistics in single SQL aggregates, cutting 50–100 individual driver queries down to 1.
* **Average Live Latency**: **42.43 ms** across all 16 primary application views with an average **81.5% GZip wire compression**.

---

## 💻 Tech Stack & Architecture

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.12+, Django 5.1.5 | High-performance ORM, security, auth, and business logic |
| **Real-Time & ASGI** | Django Channels 4.3, Daphne 4.2, channels-redis 4.3 | Live GPS WebSockets and asynchronous event pipelines |
| **Admin & UI Shell** | Django Unfold 0.40, Custom Unfold Tokens | Modern, responsive dashboard and operations interface |
| **Reactivity** | HTMX 1.21, Vanilla ES6+ JavaScript, Alpine.js | Fast asynchronous table updates without SPA overhead |
| **Static Assets & Fonts** | WhiteNoise 6.9, 100% Self-Hosted WOFF2 Fonts | Zero-CDN, hashed manifest storage, 1-year immutable caching |
| **Databases** | SQLite 3 WAL Mode (Dev) / PostgreSQL 15 + PostGIS (Prod) | Structured records, spatial geometries, vector embeddings |
| **Session & Cache** | cached_db Session Engine, django-redis 6.0, LocMemCache | In-memory session lookups and distributed query caching |
| **Document Engine** | ReportLab 4.2, openpyxl 3.1, xlsxwriter, QRCode | PDF invoices, landscape CAB statements, Excel rosters |
| **Task Queue & Cache**| Celery 5.6, Redis 8.1, Huey | Background jobs, statement parsing, and distributed caching |
| **AI Copilot** | Groq Cloud LLaMA 3.3 / Qwen, Rathasārathi Engine | Natural language operations assistant and semantic search |

---

## 📂 Project Structure

```text
travelerp/               Core project settings, ASGI/WSGI configs, and root URL routing
core/                    Party, Chauffeur, Vehicle registry, and RateCard pricing models
operations/              Trip dispatch, 7-milestone lifecycle, OSRM routing, studios
finance/                 Corporate GST invoices, e-Way bills, petty cash, customer ledgers
finance_fleet/           Fleet CPK (Cost-Per-KM) optimization radar studio
finance_payroll/         Chauffeur and operational staff payroll processing
payments_gateway/        Dynamic UPI QR generation, Razorpay webhook simulation, GL engine
crm/                     Interactive Kanban pipeline, customer inquiries, quotations
fleet_commute/           Corporate employee transit (ETS), shift rosters, ESG reporting
fleet_contracts/         Institutional contracts, daily vehicle requirements, SLA tracking
maintenance/             Interactive 2D damage marker, tyre studio, workshop job cards
packages/                Holiday tour package catalog, itineraries, day-wise activities
package_tours/           Group tour departures, college industrial visits (IVs), manifests
customer_portal/         Public customer landing page, self-service package booking
driver_portal/           Chauffeur mobile PWA, vehicle handover, trip execution lifecycle
documentation/           Comprehensive 11-chapter enterprise manuals and architecture guides
templates/               Responsive Django HTML UI templates matching Unfold styling
static/                  Application stylesheets (custom_admin.css), scripts, and assets
media/                   Uploaded trip documents, odometer photos, and vehicle papers
scripts/                 Database seeders, spatial utilities, and data import tools
```

---

## 🛠️ Setup & Installation

### Prerequisites
* Python 3.12 or newer
* Git

### Windows PowerShell Setup

```powershell
# 1. Clone the repository
git clone https://github.com/28Rithik/Tours-and-Travel-Application.git
cd "Tours and Travel Application"

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Apply database migrations
python manage.py migrate

# 5. Create superuser administrator
python manage.py createsuperuser

# 6. Verify system integrity
python manage.py check

# 7. Start the development server
python manage.py runserver
```

### Linux / macOS Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run migrations and start server
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## 🌐 Console & URL Directory

| Portal / Studio | Endpoint URL | Description |
| :--- | :--- | :--- |
| **Executive Master Dashboard** | `/` or `/dashboard/` | High-level executive KPI overview and financial trends |
| **Django Unfold Admin** | `/admin/` | Full database administration and models |
| **Dispatch Control Center** | `/dispatch/` | Real-time booking & trip dispatch board |
| **Create Booking** | `/bookings/create/` | 4-step Unfold booking entry form |
| **Staff Roles & Permissions** | `/staff/roles-matrix/` | Multi-hub RBAC capability matrix and ceilings |
| **Staff Login** | `/staff/login/` | Secure authentication for operational personnel |
| **Customer Portal Home** | `/customer-portal/` | Public self-service portal & instant fare calculator |
| **Tour Packages Catalog** | `/customer-portal/packages/` | Curated holiday & pilgrimage departures |
| **Fleet Showcase & Specs** | `/customer-portal/fleet/` | Interactive vehicle rate cards & photo galleries |
| **Services Overview** | `/customer-portal/services/` | Commercial fleet solutions & employee transit |
| **Corporate Transit Service** | `/customer-portal/services/employee-transportation/` | Enterprise corporate shuttle & SEZ mobility |
| **About Us Legacy** | `/customer-portal/about/` | Company history, accreditations, and safety standards |
| **Chauffeur Mobile PWA** | `/driver-portal/` | Mobile-first driver handover, odometer & duty log |
| **Driver PWA Login** | `/driver-portal/login/` | Mobile OTP / PIN login for field chauffeurs |
| **Driver Cash Wallet** | `/driver/wallet/` | On-road trip cash float and receipt scanner |
| **GIS Telematics Control** | `/gis/control-center/` | Live GPS fleet tracking radar & vehicle telemetry |
| **CRM Visual Kanban Board** | `/crm/kanban/` | Drag-and-drop lead stages with TAT monitoring |
| **CRM Inquiry Pipeline** | `/crm/queries/` | Customer query tracker and quotation builder |
| **Driver Settlement Studio**| `/finance/driver-settlement/` | Chauffeur trip duty slip settlement & bata sign-off |
| **GST B2B Invoicing Studio** | `/finance/gst-studio/` | Tax invoices, CGST/SGST/IGST, and e-Way bill JSON |
| **Bank Statement Reconciler**| `/finance/bank-reconciliation/` | CSV statement parser with fuzzy UTR matching |
| **Dynamic UPI Payments** | `/payments/` | Dynamic NPCI UPI QR generation & webhook simulator |
| **Fleet Vehicle Roster** | `/fleet/vehicles/` | Vehicle inventory and fitness radar |
| **Chauffeur Directory** | `/fleet/drivers/` | Driver roster and licensing sentry |
| **Vehicle Categories** | `/fleet/categories/` | Vehicle classifications and capacity |
| **Vehicle Types** | `/fleet/types/` | Commercial vehicle type catalog |
| **Border Permit Sentry** | `/operations/border-permits/` | Interstate road tax, AITP passes & hill e-Pass |
| **Chauffeur Fatigue Sentry**| `/operations/driver-fatigue-sentry/` | Driver rest counter and fatigue locking |
| **Trip Cash Envelopes** | `/operations/cash-envelopes/` | Outstation cash advances & expenses |
| **Highway Breakdown SOS** | `/operations/breakdown-sos/` | 24x7 emergency relief dispatch |
| **Parivahan E-Challans** | `/operations/echallan-sentry/` | Highway violation tracking and settlement |
| **Empty-Leg Monetization** | `/operations/empty-legs/` | Deadhead return trip optimizer |
| **Statutory Compliance** | `/operations/statutory-compliance/` | Fleet papers and RTO FC watchdog |
| **PNR Arrivals Manifest** | `/operations/pnr-arrivals/` | Flight and train delay manifest |
| **Commute Roster Dispatcher**| `/commute/roster-dispatcher/` | 300+ vehicle corporate/school route optimizer |
| **Women Safety Command** | `/commute/women-safety/` | Night shift female escort guardrails & IVR |
| **Parts Inventory** | `/maintenance/parts-inventory/` | Spare parts catalog and stock alerts |
| **Tire Health Studio** | `/maintenance/tire-studio/` | 2D axle tread depth tracking |
| **Damage Marker Studio** | `/maintenance/damage-marker/` | 2D chassis inspection blueprint |
| **Workshop Mechanic Studio**| `/maintenance/workshop/` | Garage floor job cards and work orders |
| **Guest Tour Itinerary** | `/tour/itinerary/<token>/` | Zero-login mobile passenger tour companion |
| **Interactive Quote** | `/quote/<token>/` | Digital interactive proposal with live itinerary |
| **Statement Generator** | `/statements/generate/` | Multi-page PDF/Excel CAB statements |

---

## 🧪 Testing & Validation

Run the test suite and verify system health:

```powershell
# 1. Standard Django system check
python manage.py check

# 2. Migration integrity check
python manage.py makemigrations --check

# 3. Run test suite
python manage.py test -v 1

# 4. Collect static assets
python manage.py collectstatic --noinput
```

---

## 🚢 Production Deployment

For containerized deployment using Docker Compose:

```bash
# Build and run the production stack (Nginx, Daphne ASGI, Gunicorn, PostgreSQL, Redis)
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 📄 License & Ownership

Copyright © 2026 **Siva Gayathri Tours & Travels**. All rights reserved.
Proprietary software developed for enterprise transport operations.
