# 🔧 SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 06: Fleet Engineering, Maintenance & Compliance

---

### 1. Overview & Fleet Health Philosophy

Operating a 300+ commercial vehicle fleet requires preventive, condition-based maintenance rather than reactive breakdown repairs. TravelERP provides interactive engineering studios and automated statutory compliance sentries to ensure:
- Zero on-road breakdowns during client commutes and high-value tours.
- Maximum tire tread life and fuel economy through scheduled rotations and pressure tracking.
- 100% compliance with RTO (Regional Transport Office) fitness and insurance validity.

---

### 2. 2D Axle & Tire Health Studio

- **URL**: `http://127.0.0.1:8000/maintenance/tire-studio/`
- **Axle Geometries Supported**:
  - `2-Axle (4x2)`: Standard Sedan, Innova MPV, Tempo Traveller, 32-Seater Mini Bus (Axle 1: Steer Left/Right; Axle 2: Drive Dual Left/Right).
  - `3-Axle Multi-Axle (6x2 / 6x4)`: 54-Seater Volvo 9600 / Scania Metrolink Luxury Coaches (Axle 1: Steer; Axle 2: Drive Dual; Axle 3: Tag/Dead Axle).
  - `Tandem Heavy`: Multi-axle logistics carriers.
- **Tread Depth Auditing & Color Codes**:
  - Millimeter precision tracking (Original tread: 14.0 mm – 16.0 mm).
  - **Healthy (Green)**: >= 8.0 mm
  - **Caution (Yellow)**: 4.0 mm – 7.9 mm (Schedule rotation / retread planning)
  - **Critical (Red)**: < 4.0 mm (Immediate tire replacement required)
- **Lifecycle & Retreading Tracking**:
  - Tracks casing lifespan across stages: `New (Original)`, `1st Retread (Cold/Hot)`, `2nd Retread`, `Scrapped`.
  - Calculates Cost-Per-Kilometer (CPK) per tire brand (Michelin, Bridgestone, MRF, Apollo).
- **Tire Rotation Manager**:
  - Front-to-Rear and Cross-Axle rotations logged with odometer readings.
  - Automatically recommends rotation when wear variance across an axle exceeds 2.0 mm.

---

### 3. 2D Interactive Vehicle Damage Marker Studio

- **URL**: `http://127.0.0.1:8000/admin/maintenance/damage-marker/`
- **Capabilities**:
  - Scalable 2D SVG vector vehicle blueprint showing Front, Rear, Left Side, Right Side, and Roof.
  - Interactive click-to-pin damage plotting:
    - *Dent*
    - *Scratch*
    - *Glass Crack / Windshield Chip*
    - *Paint Peeling*
    - *Upholstery Tear*
  - Severity Rating: Minor, Moderate, Severe.
  - Pre-Trip vs Post-Trip inspection comparison: Prevents drivers or customers from disputing damage caused during a rental.

---

### 4. Statutory Compliance Vault (`maintenance_compliance`)

The compliance engine audits six critical statutory documents for every vehicle in the fleet:

| Document Type | Verification Rule | Alert Window | Operational Consequence |
| :--- | :--- | :--- | :--- |
| **Fitness Certificate (FC)** | Mandatory annual RTO vehicle fitness | 30 Days prior to expiry | Vehicle locked from 1-Click Roster Dispatch |
| **Commercial Insurance** | Comprehensive + Third-Party Passenger Liability | 15 Days prior | Locked from active trip assignment |
| **Pollution (PUC)** | Emission test certificate (6-month validity) | 7 Days prior | Flagged on dispatch dashboard |
| **State / All-India Permit** | Contract carriage / Tourist permit validity | 30 Days prior | Inter-state border dispatch locked |
| **Road Tax Token** | Quarterly / Annual State Road Tax | 15 Days prior | Accounts alert for tax payment |
| **Commercial TR Badge** | Driver commercial heavy vehicle endorsement | 30 Days prior | Driver blocked from shift allocation |

---

### 5. Preventive Maintenance (PM) Job Cards, Workshop 4.0 & Spares Inventory

- **Workshop Mechanic Studio (`/maintenance/workshop/`)**:
  - Live bay status board: Active Job Cards, Grounded in Bays, Low Stock Parts Alert, MTD Parts Consumed.
  - Digital job cards with mechanic allocation, service task checklists, and time tracking.
- **Spare Parts & Consumables Store (`/maintenance/parts-inventory/`)**:
  - Unfold solid KPI cards, SKU catalog with reorder thresholds, and direct issue to active job cards.
- **PM Service Intervals**:
  - Minor Service (Every 10,000 KM): Engine oil change, oil filter, air filter cleaning, brake pad inspection.
  - Major Service (Every 30,000 KM): Fuel filter, coolant flush, gearbox oil, suspension bush inspection, wheel alignment.
  - Annual Overhaul: Clutch plate inspection, AC compressor overhaul, alternator check.
- **Automated Work Orders**:
  - When a vehicle's telematics odometer approaches a PM milestone, TravelERP automatically generates a draft `WorkOrder` and notifies the garage head.
