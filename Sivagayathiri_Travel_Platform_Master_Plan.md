# 🚀 Sivagayathiri Tours and Travels — Travel Platform Master Plan
## Evolving the Travel ERP into a Full Travel Operations & Booking Platform

> **Company:** Sivagayathiri Tours and Travels, Coimbatore, Tamil Nadu
> **Scope:** Single-tenant — built for this company only, not sold or shared with other agencies
> **Base:** Existing `travelerp` Django project (retrofit, not a rewrite)
> **Build method:** Phased, AI-assisted development — each phase below is a self-contained unit of work
> **Date:** September 2026

---

## 📌 Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State — What the ERP Already Does](#2-current-state--what-the-erp-already-does)
3. [Target Vision — Full Feature Scope](#3-target-vision--full-feature-scope)
4. [Gap Analysis](#4-gap-analysis)
5. [Target Architecture](#5-target-architecture)
6. [New & Upgraded Modules](#6-new--upgraded-modules)
7. [Data Model Additions](#7-data-model-additions)
8. [Phased Roadmap](#8-phased-roadmap)
9. [Tech Stack Decisions](#9-tech-stack-decisions)
10. [Risks & Mitigations](#10-risks--mitigations)
11. [Open Questions](#11-open-questions)

---

## 1. Executive Summary

Sivagayathiri Tours and Travels runs a single-tenant, admin-only Django ERP (`travelerp`) that manages internal operations end-to-end: bookings, trip dispatch, fleet, drivers, finance, compliance, and statements. It has no customer-facing layer and no online payment collection.

This plan evolves that ERP, **in place**, into a full travel operations and booking platform for this company alone — covering package/itinerary building, online booking and payments, customer self-service, CRM automation (WhatsApp + email), supplier and commission management, marketing tools (coupons, campaigns, AI upsells), reporting/forecasting, and compliance (GST/TCS/audit trails). No multi-tenancy is required — there is exactly one business using this system.

Because this is a solo, AI-assisted build, the plan is broken into **phases**, each scoped to be a standalone unit of work with its own goal, deliverables, and affected apps/models — suitable for turning into an individual build brief when that phase starts.

---

## 2. Current State — What the ERP Already Does

| Area | Existing Capability |
|---|---|
| Core | Party/Client/Supplier model, Driver & Cleaner profiles, Vehicle registry with compliance tracking, RateCard pricing |
| Operations | Booking → Trip lifecycle (`booked → assigned → confirmed → started → completed → billed → settled`), bulk/event contracts, traffic fines |
| Fleet Contracts | Institutional recurring contracts (schools, BPOs, govt), named routes & shifts |
| Finance | Payments, trip expenses, supplier costs, fuel tracking, driver advances/settlements, payslips, corporate fuel/FASTag accounts, vehicle loans |
| Maintenance | Compliance documents, service records, parts inventory, tyre/battery tracking, defect tickets, insurance claims |
| CRM | Basic inquiry tracking (`new → quoted → won → lost`) |
| Statements | PDF/Excel party & supplier statements, GST/TDS, party ledger |
| Dashboard | Internal operations snapshot |
| Integrations | Mocked GPS, FASTag, fuel card APIs |
| Reporting | Trip P&L, vehicle profitability, party profitability |

**Key characteristic:** everything above serves internal staff only, via Django admin. No customer login, no online payment, no marketing automation.

---

## 3. Target Vision — Full Feature Scope

### 🗂 Package Creation & Management
- Itinerary builder — day-by-day schedules with activities, hotels, transport, meals
- Dynamic packaging — combine transport, hotels, transfers, and activities into one sellable product
- Customizable, reusable package templates per destination
- Inventory management — track available seats, rooms, or slots per package

### 💳 Booking & Payments
- Online booking engine — customers book directly from the website
- Payment gateways — Razorpay (primary, India), with Stripe/PayPal as optional for international clients
- Multi-currency pricing display
- Automated GST-compliant invoicing & receipts
- Partial payments & installment plans

### 📞 CRM & Marketing
- Lead capture from website, email, WhatsApp
- Customer profiles — preferences, past bookings, communication history
- Automated reminders — payment due dates, travel documents, trip updates
- WhatsApp + email integration for itineraries, confirmations, updates
- Email campaign tools — newsletters, seasonal offers, abandoned-cart reminders
- Voucher & coupon system — discount codes, promotional campaigns
- AI-powered upsell recommendations — excursions, insurance, upgrades based on traveler profile

### 🌍 Supplier & Partner Management
- Supplier contracts — rates from hotels, transport providers (and airlines if/when flights are added)
- Commission tracking — agent commissions, reseller margins
- Real-time availability sync with suppliers *(flagged as a later/optional phase — depends on external supplier APIs)*

### 📊 Reporting & Analytics
- Sales dashboards — bookings, revenue, cancellations
- Profitability reports — margin per package, per customer
- Forecasting tools — predict seasonal/destination demand

### 🛠 Operational Tools
- Document management — visas, tickets, vouchers, insurance (customer-facing documents, distinct from existing driver/vehicle docs)
- Multi-language support
- Mobile app access — manage bookings/itineraries on the go
- Offline access *(flagged as a later/optional phase — significant added complexity)*

### 🔒 Security & Compliance
- Data protection for customer information
- GST + TCS (Tax Collected at Source) compliance
- Audit trails for accountability

### Customer Self-Service
- Self-service portal — customers log in to view itineraries, invoices, payment status, and trip updates

---

## 4. Gap Analysis

| Capability | ERP Today | Gap to Close |
|---|---|---|
| Customer-facing booking | None (admin-only) | Build self-service booking portal |
| Online payments | Recorded manually after the fact | Razorpay integration, payment links, partial/installment payments |
| Invoicing | Staff-generated statements | Auto-generated GST invoices triggered by booking/payment events |
| Itinerary/package building | Trip has hotel/journey data, but no day-by-day itinerary or dynamic packaging | New itinerary builder + package template system |
| Inventory as sellable stock | Vehicle/driver assignment only | Seat/room/slot inventory tied to packages |
| CRM depth | Basic Inquiry model | Customer profiles with history, automated reminders, WhatsApp/email integration |
| Marketing | None | Coupon engine, email campaigns, AI upsell recommendations |
| Supplier management | `Supplier` party type exists, no contracts/commissions | New supplier contract & commission tracking |
| Reporting | Trip/vehicle/party P&L exists | Extend to package-level margins, add demand forecasting |
| Compliance | GST/TDS handled in statements | Add TCS handling, formal audit trail logging |
| Document management | Driver/vehicle docs only | Customer-facing document storage (visas, tickets, vouchers, insurance) |
| Multi-language | None | i18n framework across customer-facing UI |
| Mobile access | None | Mobile-friendly portal or dedicated app |

---

## 5. Target Architecture

Single-tenant, in-place upgrade — no tenant model, no data isolation layer needed.

```
travelerp/
│
├── core/                    🏛️ EXISTING — Party, Vehicle, Driver, RateCard (unchanged structurally)
├── operations/               🚗 EXISTING — Booking, Trip (extended: link to Package/Itinerary)
├── finance/                   💰 EXISTING — Payment, expenses, payroll (extended: gateway-linked payments)
├── maintenance/                🔧 EXISTING — unchanged
├── fleet_contracts/             🏫 EXISTING — unchanged
├── crm/                          📞 EXISTING → upgraded: customer profiles, reminders, campaign links
├── statements/                    📄 EXISTING → extended: GST + TCS, auto-triggered invoices
├── dashboard/                      📊 EXISTING → extended: sales dashboard, forecasting widgets
├── integrations/                    🔌 EXISTING — GPS/FASTag/fuel mocks unchanged; add WhatsApp/email providers
│
├── packages/                        🗂️ NEW — Itinerary builder, package templates, dynamic packaging, inventory
├── payments_gateway/                 💳 NEW — Razorpay (+ optional Stripe/PayPal), payment links, installments, webhooks
├── marketing/                         📣 NEW — Coupons/vouchers, email campaigns, AI upsell recommendations
├── suppliers/                          🌍 NEW — Supplier contracts, rates, commission tracking
├── customer_portal/                     🌐 NEW — Self-service login, itinerary/invoice/document view, booking flow
├── documents/                             🛂 NEW — Customer document management (visas, tickets, vouchers, insurance)
├── analytics/                              📊 NEW — Package/customer profitability, forecasting
└── audit/                                   🔒 NEW — Audit trail logging across sensitive models
```

---

## 6. New & Upgraded Modules

### 6.1 `packages` — Itinerary & Package Management
- `Package` — destination, duration, base pricing, description, media gallery
- `PackageTemplate` — reusable structure to spin up new packages quickly
- `ItineraryDay` — day-by-day activities, hotel, transport, meals, linked to a Package
- `PackageInventory` — tracks available seats/rooms/slots per departure date
- Links into existing `operations.Trip` so dispatched trips originate from a sold package

### 6.2 `payments_gateway`
- Razorpay integration first (India-first, matches existing GST setup); Stripe/PayPal as optional add-ons for international clients
- Payment link generation, webhook handling for success/failure
- `InstallmentPlan` — splits a package price into scheduled partial payments
- Auto-creates `finance.Payment` records on successful webhook, keeping existing finance logic intact

### 6.3 `marketing`
- `Coupon` — percentage/flat discount, usage limits, expiry, package-specific rules
- `EmailCampaign` — newsletters, seasonal offers, abandoned-cart sequences
- `UpsellRecommendation` — rules/AI-assisted suggestions (excursions, insurance, upgrades) shown at checkout, based on traveler profile/past bookings

### 6.4 `suppliers`
- `SupplierContract` — negotiated rates from hotels/transport providers, validity period
- `CommissionRule` — agent/reseller commission percentage, applied at booking time
- Real-time supplier availability sync — deferred to a later phase pending which supplier APIs are actually needed

### 6.5 `customer_portal`
- Customer login (separate from staff Django admin)
- View bookings, itineraries, invoices, payment status/balance, uploaded documents
- Complete booking flow: browse package → choose date/tier → apply coupon → pay (full or installment)

### 6.6 `documents`
- Customer-facing document storage: visa copies, e-tickets, vouchers, insurance documents
- Distinct from existing `media/` usage for driver/vehicle docs

### 6.7 `analytics`
- Extends existing `travelerp/reports.py`
- Package-level and customer-level profitability
- Basic demand forecasting (seasonal booking trend analysis)

### 6.8 `audit`
- Change-logging on sensitive models (payments, bookings, invoices) — who changed what, when

---

## 7. Data Model Additions

**New models (grouped by app):**
- `packages`: Package, PackageTemplate, ItineraryDay, PackageInventory
- `payments_gateway`: PaymentLink, InstallmentPlan, PaymentWebhookEvent
- `marketing`: Coupon, CouponRedemption, EmailCampaign, UpsellRecommendation
- `suppliers`: SupplierContract, CommissionRule
- `customer_portal`: CustomerAccount (or extend `core.Party`/`Client` with login capability)
- `documents`: CustomerDocument
- `audit`: AuditLogEntry

**Modified models:**
- `operations.Booking` / `Trip` — link to `packages.Package` and `PackageInventory`
- `statements.GeneratedStatement` — extend for TCS alongside existing GST/TDS
- `core.Client` — extend or link to `CustomerAccount` for self-service login

No `organization` FK or tenant scoping required anywhere — this system serves one business.

---

## 8. Phased Roadmap

Each phase is designed to be handed off as its own build brief. Earlier phases are prerequisites for later ones; each phase should leave the system fully working for staff, without breaking existing ERP functionality.

### **Phase 1 — Packages & Itinerary Foundation**
- Build `packages` app: Package, PackageTemplate, ItineraryDay, PackageInventory
- Link Package → existing Booking/Trip flow
- Staff-side admin UI for creating/managing packages and itineraries
- *No customer-facing UI yet — this phase is data-model and internal-UI only*

### **Phase 2 — Payments & Invoicing**
- Build `payments_gateway` app, integrate Razorpay
- Payment links, webhook handling, installment plans
- Auto-generate GST invoices (extend `statements`) triggered by payment events
- Add TCS handling alongside existing GST/TDS

### **Phase 3 — Customer Self-Service Portal**
- Build `customer_portal`: login, booking flow (browse package → book → pay)
- View itinerary, invoices, payment status/balance
- Build `documents` app for customer document storage/viewing

### **Phase 4 — CRM & Communication Automation**
- Upgrade `crm`: customer profiles with preference/history tracking
- WhatsApp Business API integration — confirmations, reminders, updates
- Email integration — transactional emails (confirmations, receipts)
- Automated reminders (payment due, document expiry, trip updates)

### **Phase 5 — Marketing Tools**
- Build `marketing` app: coupon/voucher engine
- Email campaign tools — newsletters, seasonal offers, abandoned-cart reminders
- AI-powered upsell recommendations at checkout

### **Phase 6 — Supplier & Commission Management**
- Build `suppliers` app: contracts, rates, commission rules
- Apply commission logic at booking time
- (Real-time supplier availability sync deferred — revisit only if/when external hotel/transport APIs are actually needed)

### **Phase 7 — Reporting, Forecasting & Compliance**
- Extend `analytics`: package/customer profitability, seasonal demand forecasting
- Build `audit` app: change-logging on payments/bookings/invoices
- Sales dashboards for staff

### **Phase 8 — Reach: Mobile, Multi-language, Multi-currency**
- Mobile-friendly customer portal (or dedicated app, decide based on usage after Phase 3 launches)
- i18n framework for multi-language customer-facing UI
- Multi-currency display; Stripe/PayPal added only if international bookings materialize
- Offline access — evaluated last, only if a genuine remote-connectivity need shows up in practice

---

## 9. Tech Stack Decisions

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Django (existing) | Reuse current codebase and skillset |
| Database | SQLite (dev) → PostgreSQL before customer portal goes live | Real customer traffic + payments need better write concurrency than SQLite |
| Customer-facing frontend | Django templates + HTMX + Alpine.js | Fast solo development, no separate frontend stack to maintain |
| Admin/staff UI | Jazzmin (existing) | Already in place for internal ops |
| Payments | Razorpay first; Stripe/PayPal only if international demand appears | India-first, matches existing GST workflows |
| Messaging | WhatsApp Business API + transactional email (e.g. SendGrid/SES) | Matches required CRM automation |
| PDF/Excel | ReportLab + OpenPyXL (existing) | Already proven for statements |
| Mobile | Mobile-responsive portal first; native app only if usage justifies it | Avoids premature investment in a separate mobile codebase |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Large overall scope for a solo build | Strict phase sequencing; each phase ships independently useful functionality |
| Payment webhook failures causing reconciliation drift | Idempotent webhook handlers, reconciliation view comparing gateway vs recorded payments |
| Customer portal introduces new attack surface (auth, payments) not present in admin-only system | Use Django's built-in auth hardening, HTTPS everywhere, rate-limit login, PCI-safe gateway integration (never store raw card data) |
| SQLite unsuitable once real customer traffic/payments begin | Migrate to PostgreSQL before Phase 2 (payments) goes live |
| Scope creep from "nice to have" items (offline mode, native mobile, real-time supplier sync, multi-currency) | Explicitly deferred to Phase 8 and revisited only if real usage demands them |
| WhatsApp Business API approval delays | Apply for API access at the start of Phase 4, before development begins |

---

## 11. Open Questions

- Will flights ever be part of packages, or is this transport/hotel/activity only for now? (Affects how far "dynamic packaging" needs to go.)
- Is there a real near-term need for Stripe/PayPal (international clients), or is Razorpay alone sufficient at launch?
- Should the customer portal be a fully separate login system, or should existing `Client` records in `core` get login capability directly?
- Any existing WhatsApp Business API access already set up, or does that application/approval need to start now given it can take time?
- Priority order confirmation: is the phase order above (Packages → Payments → Portal → CRM → Marketing → Suppliers → Analytics → Reach) correct for your business priorities, or should something move up?

---

*This document defines the full target scope and phased build plan for evolving Sivagayathiri Tours and Travels' internal ERP into a complete package-booking, payment-collection, and customer-engagement platform — built for this company only, phase by phase, with AI-assisted development.*
