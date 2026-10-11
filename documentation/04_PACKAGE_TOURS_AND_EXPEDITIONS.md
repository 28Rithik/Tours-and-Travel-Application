# 🗺️ SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 04: Package Tours, Group Expeditions & HTMX Decks

---

### 1. Architectural Migration & Decoupling

In earlier iterations, the package tour administrative interface relied on a monolithic 153 KB JavaScript file (`package_dynamic_form.js`) coupled to traditional Django admin.

In Phase 7, the entire ecosystem was modernized:
1. **Decoupled from Legacy JS**: Replaced monolithic scripts with modular HTMX endpoints that exchange reactive HTML fragments.
2. **24 ModelAdmins on Unfold**: All models inherit from `unfold.admin.ModelAdmin`.
3. **11 Inlines on Unfold**: Stacked and Tabular inlines updated with modern badge pills, clean fieldsets, and responsive layout grids.
4. **Proxy Navigation Split**: Partitioned operational workloads cleanly into `packages` (Master Catalogs & Tariffs) and `package_tours` (Live Departure Batches, College IVs, and Passenger Manifests).

---

### 2. Comprehensive Model & Inline Registry

#### 2.1 The 24 Modernized ModelAdmins

| App / Namespace | Model | ModelAdmin Class | Purpose |
| :--- | :--- | :--- | :--- |
| `packages` | `PackageTemplate` | `PackageTemplateAdmin` | Standard multi-day itinerary templates |
| `packages` | `Package` | `PackageAdmin` | Active commercial packages |
| `packages` | `PackageVehicleTariff` | `PackageVehicleTariffAdmin` | Fleet-specific pricing matrix (Sedan to Coach) |
| `packages` | `TempleDarshanSlot` | `TempleDarshanSlotAdmin` | Pilgrimage temple darshan slot allocator |
| `packages` | `InternationalDocumentChecklist`| `InternationalDocumentChecklistAdmin`| Visa, passport, insurance requirements |
| `packages` | `ItineraryDay` | `ItineraryDayAdmin` | Day-by-day sightseeing and activity schedule |
| `packages` | `PackageSeasonalRate` | `PackageSeasonalRateAdmin` | High season, peak holiday & festival surcharges |
| `packages` | `PackageHotelAllotment` | `PackageHotelAllotmentAdmin` | Contracted room inventory (Deluxe, Triple, Quad) |
| `packages` | `PackageAddon` | `PackageAddonAdmin` | Optional upgrades (DJ Night, Buffet, Campfire) |
| `packages` | `PackageB2BMargin` | `PackageB2BMarginAdmin` | Sub-agency commission and agent net rates |
| `packages` | `TourFeedbackLog` | `TourFeedbackLogAdmin` | Guest NPS ratings, driver reviews, food quality |
| `packages` | `PackageInventory` | `PackageInventoryHiddenAdmin` | Master batch departure inventory |
| `packages` | `BoardingPoint` | `BoardingPointHiddenAdmin` | Pickup points for holiday departures |
| `packages` | `CollegeIVExpedition` | `CollegeIVExpeditionHiddenAdmin` | Student industrial visit tracking |
| `packages` | `TourPassengerManifest` | `TourPassengerManifestHiddenAdmin`| Passenger rooming & seating list |
| `package_tours` | `TourDepartureBatchProxy`| `TourDepartureBatchAdmin` | Operations console for bus departure batches |
| `package_tours` | `CollegeIVProxy` | `CollegeIVAdmin` | Student expedition control board |
| `package_tours` | `BoardingPointProxy` | `BoardingPointAdmin` | Boarding node manager |
| `package_tours` | `PassengerManifestProxy`| `PassengerManifestAdmin` | Digital manifest & rooming console |
| `package_tours` | `HotelAllotmentProxy` | `HotelAllotmentAdmin` | Hotel room blocks management |
| `package_tours` | `TourFeedbackProxy` | `TourFeedbackProxyAdmin` | Guest reviews & feedback dashboard |
| `package_tours` | `SeasonalRateProxy` | `SeasonalRateProxyAdmin` | Seasonal tariff multipliers |
| `package_tours` | `PackageAddonProxy` | `PackageAddonProxyAdmin` | Package addon console |
| `package_tours` | `B2BMarginProxy` | `B2BMarginProxyAdmin` | Travel agent net margin manager |

#### 2.2 The 11 Unfold Inlines
- `ItineraryDayInline` (StackedInline) on `PackageAdmin`
- `PackageVehicleTariffInline` (TabularInline) on `PackageAdmin`
- `PackageSeasonalRateInline` (TabularInline) on `PackageAdmin`
- `PackageAddonInline` (TabularInline) on `PackageAdmin`
- `PackageHotelAllotmentInline` (TabularInline) on `PackageAdmin`
- `PackageB2BMarginInline` (TabularInline) on `PackageAdmin`
- `TempleDarshanSlotInline` (StackedInline) on `PackageAdmin`
- `InternationalDocumentChecklistInline` (TabularInline) on `PackageAdmin`
- `BoardingPointInline` (TabularInline) on `TourDepartureBatchAdmin`
- `HotelAllotmentInline` (TabularInline) on `TourDepartureBatchAdmin`
- `PassengerManifestInline` (TabularInline) on `TourDepartureBatchAdmin`

---

### 3. HTMX Reactive Decks in Package Change Form

When editing any package at `/admin/packages/package/<id>/change/`, five HTMX decks reactively execute without page reloads:

#### 3.1 Category Intelligence Deck (`/packages/htmx/category-intel/`)
Dynamically renders category-specific operational rules upon category selection:
- 🎓 **College / School Industrial Visit (IV)**: Factory entry clearance letter required, Campfire & DJ cutoff strictly 10:00 PM, 1 faculty escort free per 15 students, digital roll number manifest.
- 🛕 **Devotional Pilgrimage & Temple Darshan**: Mandatory dress code specifications (Dhoti/Saree), VIP Darshan token links, shoe stand logistics, Sattvic vegetarian meal protocol.
- ✈️ **International Tour Expedition**: Minimum 6-month passport validity check, overseas travel medical insurance mandatory, international flight baggage allowances.
- 🌴 **Honeymoon / Leisure / Hill Station**: Candlelight dinner upgrades, luxury vehicle pushback seating, private resort bonfire setup.

#### 3.2 Operating Unit Economics & Gross Profit P&L Deck (`/packages/htmx/unit-economics/`)
Calculates real-time financial margins based on direct costs and selling rates:
- **Direct Cost Per Head**: Hotel + Coach Transport + Meals + Activities + Misc.
- **Selling Rate (With Food vs Without Food)**.
- **Unit Gross Margin & Margin %**.
- **Convoy Gross Profit**: Multiplied across convoy capacity (e.g. 50 Pax = +₹60,000 profit).
- **Breakeven Occupancy**: Minimum seats required to cover fixed coach and guide overhead (e.g. 41 / 50 Pax).

#### 3.3 Dynamic Vehicle Tariff Calculator (`/packages/htmx/tariff-calculate/`)
Computes per-vehicle quotes dynamically based on tour duration, estimated total kilometers, driver daily bata, toll charges, and vehicle seating tier.

#### 3.4 WhatsApp Customer Briefing Modal (`/packages/htmx/whatsapp-briefing/`)
Generates 3 formatted WhatsApp briefing templates ready for instant dispatch:
1. *Customer Quick Quotation & Itinerary Highlights*
2. *Departure Day Packing & Attire Guidelines*
3. *Trip In-Charge Faculty / Tour Leader Roster Briefing*

#### 3.5 Proposal PDF Quotation Preview Modal (`/packages/htmx/proposal-preview/`)
Provides a 1-click preview link to branded, print-ready customer proposals (`/packages/quote/<id>/`).

---

### 4. Student Industrial Visit (IV) Protocols

1. **Digital Passenger Manifest & Rooming List**:
   - Manages student lists with Roll Number, Gender, Room Number, and Emergency Contact.
   - Separate room allocations for Male Students, Female Students, and Accompanying Faculty.
2. **CSV Template Manifest Upload**:
   - Download standardized CSV template (`/packages/manifest/template/download/`).
   - 1-Click bulk CSV import (`/packages/manifest/upload/`) with automatic validation of mandatory fields.
