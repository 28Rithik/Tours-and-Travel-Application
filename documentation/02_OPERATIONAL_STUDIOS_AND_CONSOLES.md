# 🛠️ SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 02: Operational Studios & Interactive Consoles

---

### 1. Studio Architecture Overview

TravelERP incorporates specialized, domain-specific visual studios that replace static database tables with interactive control rooms. Every studio features:
- High-contrast daylight **Light Mode** styling with instant dark mode toggling.
- Anti-FOUC (Flash of Unstyled Content) theme synchronization via `localStorage`.
- Real-time responsive controls, keyboard shortcuts, and instant asynchronous data submission.

---

### 2. Comprehensive Catalog of Operational Studios

#### 2.1 2D Axle & Tire Health Studio
- **URL**: `http://127.0.0.1:8000/maintenance/tire-studio/` (Alias: `/admin/maintenance/tire-studio/`)
- **Key Capabilities**:
  - Interactive SVG visual layout of 2-Axle (4x2), 3-Axle (6x2/6x4 Multi-Axle Volvo Coach), and Heavy Tandem configurations.
  - Color-coded tread depth wear indicators:
    - 🟢 **Healthy**: >= 8.0 mm
    - 🟡 **Caution**: 4.0 mm – 7.9 mm
    - 🔴 **Critical Replacement**: < 4.0 mm
  - Tire rotation logging (Front-to-Rear, Cross-Axle) with odometer tracking.
  - Retreading lifecycle counter (Original, 1st Retread, 2nd Retread, Scrapped).
  - Live cold pressure psi display and telematics pressure alerts.

#### 2.2 Visual CRM Drag-and-Drop Kanban Board
- **URL**: `http://127.0.0.1:8000/admin/crm/kanban/` (Alias: `/crm/kanban/`)
- **Key Capabilities**:
  - Interactive 5-column stage pipeline: `New Leads` ➔ `Follow-Up Active` ➔ `Quotation Sent` ➔ `Negotiation / Objection` ➔ `Converted to Booking`.
  - Drag-and-drop HTML5 drag events with asynchronous stage updating (`/crm/api/inquiries/<id>/update-stage/`).
  - 1-Click quick actions: Call dialer, WhatsApp proposal dispatch, Objection logger modal, Turnaround Time (TAT) speed badges.
  - Instant conversion to Trip & Booking with one click.

#### 2.3 Day-Wise Trip Itinerary Builder Studio
- **URL**: `http://127.0.0.1:8000/admin/operations/trip/<trip_id>/itinerary-builder/`
- **Key Capabilities**:
  - Dynamic day sequencer with drag-to-reorder day cards.
  - Multi-category activity tagging: Sightseeing, Meals, Temple Darshan, Safari, Travel Transit, Leisure.
  - 1-Click package template import (`/api/trip/<id>/itinerary/import-package/`) that auto-populates day plans from standard catalogs.
  - Live preview modal and instant public guest companion link generator.

#### 2.4 Guest Tour Companion Portal (Zero-Login Mobile Web)
- **URL**: `http://127.0.0.1:8000/tour/itinerary/<token>/`
- **Key Capabilities**:
  - Zero-login mobile companion accessible to tour guests via SMS/WhatsApp magic token.
  - Day-wise visual timeline with interactive venue coordinates, maps, and recommended attire.
  - Assigned vehicle and captain contact cards with 1-tap dialer.
  - Emergency 24/7 helpline buttons and digital tour voucher access.

#### 2.5 Petty Cash Float Register Studio
- **URL**: `http://127.0.0.1:8000/admin/finance/petty-cash-studio/` (Alias: `/admin/petty-cash/`)
- **Key Capabilities**:
  - Cash custodian management across branch offices (HQ Coimbatore, Chennai Depot, Bangalore Hub).
  - Real-time reconciliation of cash top-ups against verified trip vouchers.
  - Discrepancy flagging when driver reported cash outlays exceed permitted float allowances.
  - Daily float closing balance reports with PDF/CSV export.

#### 2.6 Driver Mobile Cash Wallet
- **URL**: `http://127.0.0.1:8000/driver/wallet/`
- **Key Capabilities**:
  - Mobile-first interface for drivers and tour managers on active multi-day trips.
  - 1-Tap expense logger: Diesel fuel, State border entry permits, Highway tolls, Driver Bata, Parking.
  - Camera receipt photo upload with instant OCR and receipt thumbnail preview.
  - Live remaining float balance computation.

#### 2.7 Automated Bank Statement CSV Reconciler
- **URL**: `http://127.0.0.1:8000/admin/finance/bank-reconciliation/` (Alias: `/finance/bank-reconciliation/`)
- **Key Capabilities**:
  - Universal CSV statement uploader (HDFC, ICICI, SBI, Axis Bank formats).
  - Intelligent fuzzy matching on 12-digit UTR (Unique Transaction Reference) and IMPS/NEFT transaction remarks.
  - Auto-reconciliation of customer booking deposits against pending invoices.
  - 1-Click batch reconciliation and manual override tools.

#### 2.8 1-Click Batch Roster Dispatcher (300+ Vehicles Scale)
- **URL**: `http://127.0.0.1:8000/commute/roster-dispatcher/`
- **Key Capabilities**:
  - Evaluates institutional contracts (School, Corporate IT SEZ) for any target date.
  - Statutory driver commercial TR badge and vehicle fitness validation.
  - AI Route Clustering Cockpit with capacity matching (Sedan, MPV, Tempo, Coach).
  - 2-Opt TSP waypoint sequencing and passenger boarding pass generation.

#### 2.9 Corporate SLA Performance & Penalty Deductions Studio
- **URL**: `http://127.0.0.1:8000/commute/sla-penalties/`
- **Key Capabilities**:
  - Ingestion of telemetry delay breaches (>15 min late arrivals, geofence speeding).
  - Penalty deduction ledger linked directly to monthly corporate invoicing (`ContractMonthlyInvoice`).
  - Executive waiver management with mandatory reason logging and audit trail.

#### 2.10 Women Safety IVR Simulator & Commute Buddy Command
- **URL**: `http://127.0.0.1:8000/commute/women-safety/`
- **Key Capabilities**:
  - Night shift guardrails enforcement (8 PM – 6 AM).
  - Detection of isolated female drops (last drop in vehicle).
  - Automated buddy pairing and mandatory security escort allocation.
  - Simulated outbound telephony IVR terminal with DTMF response testing.

#### 2.11 Corporate GST B2B Invoicing & NIC E-Way Bill Studio
- **URL**: `http://127.0.0.1:8000/admin/finance/gst-studio/`
- **Key Capabilities**:
  - Tax invoice generation adhering to Indian GST rules (CGST + SGST vs IGST).
  - NIC E-Way Bill JSON schema compliant generator.
  - 1-Click direct WhatsApp invoice dispatch to client accounts team.

#### 2.12 Dynamic UPI & Payment Gateway Studio
- **URL**: `http://127.0.0.1:8000/admin/finance/payment-studio/`
- **Key Capabilities**:
  - Dynamic NPCI-compliant UPI QR generation (`upi://pay?pa=...&am=...&tr=...`).
  - Real-time webhook simulator and direct settlement ledger reconciliation.

#### 2.13 2D Interactive Vehicle Damage Marker Studio
- **URL**: `http://127.0.0.1:8000/admin/maintenance/damage-marker/`
- **Key Capabilities**:
  - 2D SVG vehicle chassis blueprint (Sedan, SUV, Coach).
  - Click-to-pin damage markers: Dent, Scratch, Crack, Paint Peeling.
  - Severity level assignment (Low, Medium, Severe) and repair cost estimation.

#### 2.14 Rathasārathi AI Operations Copilot Studio
- **URL**: `http://127.0.0.1:8000/admin/operations/rathasarathi-ai/`
- **Key Capabilities**:
  - Sub-second natural language fleet queries powered by Groq Cloud (LLaMA 3.3-70B / Qwen).
  - 8 Live Database Function Calling Tools: active tours, compliance expiry alerts, revenue collection metrics, driver safety scorecards, fleet availability, CRM pipeline, trip lookups, and semantic tour package search.
  - Semantic Package Search: Instant search across 6,252 packages, 30,508 day-by-day itineraries, and 31,221 vehicle tariffs with pgvector and TF-IDF cosine similarity.
  - Built-in ⚙️ Settings Modal for live Groq API key configuration, runtime validation, and model discovery.
  - Resilient offline fallback to internal local semantic rule engine with zero downtime.

#### 2.15 Interstate State Border Entry Tax & AITP Permit Sentry
- **URL**: `http://127.0.0.1:8000/operations/border-permits/` (Alias: `/admin/operations/border-permits/`)
- **Design Architecture**: Django Unfold Solid KPI Deck (`blue`, `green`, `rose`, `slate`), Tabs Navigation, `.unfold-table`.
- **Key Capabilities**:
  - Real-time detection of cross-border routes (Kerala, Karnataka, Andhra Pradesh, Puducherry).
  - Automated check-post tax rate lookup by seating capacity and state tariff rules.
  - Parivahan AITP clearance verification and digital permit receipt archiving.

#### 2.16 Chauffeur Fatigue & Ghat Safety Sentry
- **URL**: `http://127.0.0.1:8000/operations/driver-fatigue-sentry/` (Alias: `/admin/operations/driver-fatigue-sentry/`)
- **Design Architecture**: 5-Tier Unfold Solid KPI Deck, `.unfold-search-box` with `/` shortcut, `.unfold-table`.
- **Key Capabilities**:
  - Continuous duty hours counter and mandatory statutory 8h rest validation.
  - Night-shift and Ghat road risk detection (Ooty, Kodaikanal, Munnar hairpin bends).
  - Dispatch locks preventing fatigued driver assignment without authorized managerial override.

#### 2.17 Trip Cash Advance & Kharcha Settlement Envelope Studio
- **URL**: `http://127.0.0.1:8000/operations/cash-envelopes/` (Alias: `/admin/operations/cash-envelopes/`)
- **Design Architecture**: Unfold KPI Deck, `.unfold-search-box` with `/` shortcut, `.unfold-table`.
- **Key Capabilities**:
  - Digital cash float issuance for multi-day outstation trips.
  - Verified on-road expense logging (diesel, tolls, state tax, driver bata).
  - Depot cashier surplus refund and deficit settlement workflows.

#### 2.18 Highway Breakdown & Emergency SOS Relief Dispatch Studio
- **URL**: `http://127.0.0.1:8000/operations/breakdown-sos/` (Alias: `/admin/operations/breakdown-sos/`)
- **Design Architecture**: High-urgency Unfold KPI Deck (`rose`, `amber`, `green`, `blue`), SOS Search, Emergency Action Bar.
- **Key Capabilities**:
  - Live incident logging with GPS highway corridor markers and passenger headcount.
  - 1-Click relief vehicle and replacement chauffeur dispatch.
  - 24x7 control room phone hotline integration and passenger distress monitoring.

#### 2.19 Parivahan RTO Traffic E-Challan Sentry Studio
- **URL**: `http://127.0.0.1:8000/operations/echallan-sentry/` (Alias: `/admin/operations/echallan-sentry/`)
- **Design Architecture**: Unfold KPI Deck, violation status pills, `.unfold-table`.
- **Key Capabilities**:
  - Automated sync with National & State Highway Parivahan violation cameras.
  - Liability allocation: driver settlement deduction (speeding/rash driving) vs. company absorbed (technical/RTO papers).
  - Payment reconciliation and fine settlement ledger logging.

#### 2.20 Empty-Leg Return Deadhead Trip Marketplace & Optimizer
- **URL**: `http://127.0.0.1:8000/operations/empty-legs/` (Alias: `/admin/operations/empty-legs/`)
- **Design Architecture**: Unfold KPI Deck (`blue`, `green`, `purple`, `slate`), `.unfold-search-box`, `.unfold-table`.
- **Key Capabilities**:
  - Auto-detection of vehicles returning empty after one-way drops (e.g. Madurai ➔ Chennai).
  - Dynamic offer pricing above marginal fuel/toll costs.
  - Deadhead KM avoidance and carbon footprint reduction reporting.

#### 2.21 Commercial Fleet RTO Fitness (FC), AIS-140 & Statutory Compliance Sentry
- **URL**: `http://127.0.0.1:8000/operations/statutory-compliance/` (Alias: `/admin/operations/statutory-compliance/`)
- **Design Architecture**: Unfold KPI Deck (`green`, `rose`, `amber`, `blue`), `.unfold-search-box`, `.unfold-table`.
- **Key Capabilities**:
  - Automated audit of Fitness Certificates (FC), Commercial Insurance, Road Tax, Tourist Permits, PUC.
  - Zero-tolerance dispatch lock for vehicles with expired or non-compliant statutory papers.
  - 7-day and 30-day proactive RTO inspection renewal alerts.

#### 2.22 Flight & Train PNR Group Arrival Manifest Studio
- **URL**: `http://127.0.0.1:8000/operations/pnr-arrivals/` (Alias: `/admin/operations/pnr-arrivals/`)
- **Design Architecture**: Unfold KPI Deck (`purple`, `blue`, `amber`, `green`), `.unfold-search-box`, `.unfold-table`.
- **Key Capabilities**:
  - Real-time flight and Vande Bharat train delay monitoring.
  - Chauffeur airport gate and welcome placard coordination.
  - VIP and corporate delegation arrival manifests.
