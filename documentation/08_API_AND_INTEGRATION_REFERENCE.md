# 🔌 SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 08: API & Omnichannel Integrations Reference

---

### 1. API Architecture

TravelERP employs a multi-protocol integration layer catering to:
- **HTMX Reactive Endpoints**: Server-rendered HTML fragments for dynamic dashboard decks.
- **REST JSON APIs**: Mobile app consumption, telematics ingestion, and automated batch scripts.
- **Omnichannel Webhooks**: Real-time inbound webhooks from Meta (WhatsApp & Facebook Leads), Arattai, and Banking gateways.
- **Spatial Routing APIs**: Interfaced with OSRM (Open Source Routing Machine) and OpenStreetMap.

---

### 2. Core REST & Operational Endpoints

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/api/bookings/<id>/` | GET | Session | Retrieves complete booking details with pricing and passengers |
| `/api/trips/<id>/` | GET | Session | Retrieves trip status, assigned vehicle, driver, and milestones |
| `/api/vehicle-types/` | GET | Session | Lists all 25 active vehicle seating categories |
| `/api/vehicles/<reg>/check-availability/` | GET | Session | Validates vehicle availability for a specific date range |
| `/api/trips/<id>/bata/calculate/` | GET/POST | Session | Computes day, night halt, and hill station driver allowances |
| `/api/telematics/ping/` | POST | API Key | Ingests vehicle GPS telematics ping (lat, lng, speed, fuel) |
| `/api/telematics/live/<vehicle_id>/` | GET | Session | Returns latest live GPS location and telematics metrics |
| `/api/spatial/nearest-vehicles/` | GET | Session | Haversine query returning closest available standby vehicles |
| `/api/routing/route/` | GET | Public | High-speed OSRM routing geometry, distance, and duration |
| `/api/routing/optimize/` | POST | Session | 2-Opt TSP waypoint optimizer for multi-stop circuits |

---

### 3. Commute & Live Tracking APIs

| Endpoint | Method | Auth | Description |
| :--- | :---: | :---: | :--- |
| `/commute/api/roster-dispatcher/generate/` | POST | Login | 1-Click batch shift generation and vehicle/driver allocation |
| `/commute/api/track/<token>/live/` | GET | Public | 5-second polling endpoint returning real-time bus coordinates & ETA |
| `/commute/api/ivr/simulate-call/` | POST | Session | Triggers automated night shift safety check call to commuter |
| `/commute/api/ivr/webhook/` | POST | Public | Receives telecom DTMF digits (1=Safe, 2=Panic SOS) |
| `/commute/api/verify-boarding-otp/` | POST | Session | Driver boarding scanner OTP validation |
| `/commute/api/sla-penalties/waive/` | POST | Admin | Submits management waiver for contractual delay penalty |
| `/commute/api/clusters/optimize/` | POST | Session | Spatial clustering and TSP route sequencing for commuter roster |
| `/commute/api/clusters/commit/` | POST | Session | Commits approved AI clusters into live operational shift dispatch |

---

### 4. Package Tours HTMX Endpoints

| Endpoint | Method | Response | Description |
| :--- | :---: | :---: | :--- |
| `/packages/htmx/category-intel/` | GET | HTML Card | Category intelligence guidelines (Devotional, IV, Intl) |
| `/packages/htmx/unit-economics/` | GET | HTML Deck | Real-time direct cost, selling rate, and gross profit margin |
| `/packages/htmx/tariff-calculate/` | POST | HTML Fragment | Vehicle fleet tariff breakdown (Sedan, Innova, Coach) |
| `/packages/htmx/whatsapp-briefing/` | GET | HTML Modal | 3 pre-formatted customer WhatsApp briefing messages |
| `/packages/htmx/proposal-preview/` | GET | HTML Modal | Branded proposal quotation preview link |

---

### 5. Omnichannel Webhook Integrations

#### 5.1 Meta WhatsApp Cloud API (`/admin/integrations/whatsapp/`)
- Inbound webhook handler receives customer tour inquiries, booking confirmations, and driver replies.
- Outbound template dispatcher sends:
  - *Trip Sheet Briefings* to drivers with Google Maps location links.
  - *Booking Vouchers* and invoices to customers.
  - *Parent Bus Arrival Notifications* (5 minutes before pickup).

#### 5.2 Arattai Messaging Webhook (`/api/integrations/arattai/webhook/`)
- Native integration with Zoho Arattai messaging app for indigenous corporate fleet notifications.

#### 5.3 Meta Lead Ads Webhook (`/api/integrations/meta/webhook/`)
- Captures leads generated from Facebook & Instagram travel advertising campaigns.
- Auto-ingests inquiries directly into the CRM pipeline within seconds.

#### 5.4 Google Sheets Real-Time Sync (`/api/integrations/google-sheets/sync/`)
- Two-way synchronization between operations spreadsheets and TravelERP core database.
