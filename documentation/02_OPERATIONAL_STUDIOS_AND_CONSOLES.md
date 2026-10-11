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

#### 2.14 TARA AI Operations Copilot Studio
- **URL**: `http://127.0.0.1:8000/admin/operations/tara-ai/`
- **Key Capabilities**:
  - Natural language fleet queries: *"Which buses are delayed in Coimbatore today?"*
  - Contextual awareness across 166 models, bookings, drivers, and maintenance alerts.
