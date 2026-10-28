# ☀️ SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 07: Light Mode & Aesthetics Design System

---

### 1. Design Philosophy: Sunlight-Visible High Contrast

Transport fleet dispatchers, depot supervisors, and tour managers frequently use laptops, tablets, and mobile devices in open sunlight, transport yards, and bus depots. 

In response to explicit operational requirements:
> *"I mainly use light mode"*

TravelERP features a **high-contrast, daylight-visible Light Mode design system** across every studio, companion tracker, driver wallet, and admin console, while preserving dark mode for nighttime command centers.

---

### 2. Core CSS Variable Tokens

Every portal and studio utilizes semantic CSS custom properties defined in `:root` (Light Mode default) and overridden in `html.dark`:

```css
:root {
    /* Backgrounds & Surfaces */
    --bg-base: #f8fafc;        /* Slate 50: Clean, bright app canvas */
    --bg-card: #ffffff;        /* Pure White: High contrast card background */
    --border-glass: #e2e8f0;   /* Slate 200: Crisp, subtle card borders */

    /* Typography */
    --text-main: #0f172a;      /* Slate 900: Razor-sharp readable primary text */
    --text-muted: #64748b;     /* Slate 500: Clear secondary helper text */

    /* Brand & Accent Palettes */
    --accent-primary: #0284c7; /* Sky 600: Electric operational blue */
    --accent-success: #059669; /* Emerald 600: Punctual, verified, safe */
    --accent-warning: #d97706; /* Amber 600: Delay, caution, maintenance */
    --accent-danger: #dc2626;  /* Red 600: Breach, SOS panic, overdue */
}

html.dark {
    --bg-base: #090d16;        /* Deep space midnight */
    --bg-card: rgba(18, 24, 38, 0.85);
    --border-glass: rgba(255, 255, 255, 0.08);

    --text-main: #f8fafc;
    --text-muted: #94a3b8;

    --accent-primary: #38bdf8;
    --accent-success: #10b981;
    --accent-warning: #f59e0b;
    --accent-danger: #ef4444;
}
```

---

### 3. Anti-FOUC (Flash of Unstyled Content) Synchronization

To ensure that pages do not briefly flash in dark mode when loaded in sunlight, an anti-FOUC inline script is placed at the very top of `<head>` in every template:

```html
<script>
    (function() {
        try {
            var raw = localStorage.getItem('_x_adminTheme');
            var t = raw ? JSON.parse(raw) : (localStorage.getItem('theme') || 'auto');
            var isDark = t === 'dark' || (t === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
            if (isDark) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        } catch(e) {}
    })();
</script>
```

#### Synchronized LocalStorage Keys:
- `theme`: Used by standalone portals, live tracking pages, guest companions, and studios.
- `_x_adminTheme`: Used by Django Unfold Admin's internal theme engine.
Both keys are kept synchronized simultaneously upon any toggle action.

---

### 4. Interactive Theme Toggle Implementation

Every studio header includes an intuitive theme toggle button:

```html
<button class="btn btn-secondary" onclick="toggleTheme()" title="Toggle Light/Dark Theme">
    <i class="fas fa-sun" id="themeIconSun" style="display:none; color: #f59e0b;"></i>
    <i class="fas fa-moon" id="themeIconMoon" style="color: #64748b;"></i>
</button>

<script>
    function updateThemeIcon() {
        const isDark = document.documentElement.classList.contains('dark');
        const sun = document.getElementById('themeIconSun');
        const moon = document.getElementById('themeIconMoon');
        if (sun && moon) {
            sun.style.display = isDark ? 'inline-block' : 'none';
            moon.style.display = isDark ? 'none' : 'inline-block';
        }
    }

    function toggleTheme() {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        localStorage.setItem('_x_adminTheme', isDark ? 'dark' : 'light');
        updateThemeIcon();
    }

    document.addEventListener('DOMContentLoaded', updateThemeIcon);
</script>
```

---

### 5. Verified Portals with Daylight Light Mode Support

1. **Batch Roster Dispatcher Studio** (`/commute/roster-dispatcher/`): White KPI cards, clean shift table, electric blue buttons.
2. **SLA Performance & Penalty Studio** (`/commute/sla-penalties/`): High-contrast red infraction tags, emerald green waiver badges.
3. **Parent & Employee Live Bus Tracking** (`/commute/track/<token>/`): Real OpenStreetMap vector tiles, high-contrast boarding node cards.
4. **Women Safety IVR Simulator** (`/commute/women-safety/`): Daylight white table cards, high-contrast DTMF phone simulation.
5. **2D Axle & Tire Health Studio** (`/maintenance/tire-studio/`): Clear axle chassis outlines, vivid wear indicators.
6. **CRM Drag-and-Drop Kanban Board** (`/admin/crm/kanban/`): Crisp column headers, legible client contact chips.
7. **Day-Wise Trip Itinerary Builder Studio** (`/admin/operations/trip/<id>/itinerary-builder/`): Distinct timeline cards, sharp venue chips.
8. **Guest Tour Companion** (`/tour/itinerary/<token>/`): Mobile-friendly daylight contrast for travelers exploring outdoor tourist sites.
9. **Petty Cash Float Register & Driver Wallet** (`/admin/finance/petty-cash-studio/` & `/driver/wallet/`): Clear financial figures, bright receipts.
10. **Bank Reconciliation Studio** (`/admin/finance/bank-reconciliation/`): Multi-tier match badges (Exact, Fuzzy, Unmatched).
11. **Dispatch Control Center** (`/dispatch/`): Unfold solid gradient KPI cards, Unfold data table, status pill badges.
12. **Interstate Border Permit Sentry** (`/operations/border-permits/`): Solid KPI deck, Parivahan verification indicators.
13. **Chauffeur Fatigue Sentry** (`/operations/driver-fatigue-sentry/`): 5-tier rest hours KPI cards, `/` shortcut search bar.
14. **Trip Cash Envelopes** (`/operations/cash-envelopes/`): Verified expense balances, cashier refund reconciliation.
15. **Breakdown SOS Emergency Relief** (`/operations/breakdown-sos/`): High-urgency alert pills, replacement vehicle allocation.
16. **Parivahan E-Challan Sentry** (`/operations/echallan-sentry/`): Speeding violation pills, fine settlement tracking.
17. **Empty Leg Return Optimizer** (`/operations/empty-legs/`): Deadhead KM avoided metric, discount return offer cards.
18. **Statutory Document Watchdog** (`/operations/statutory-compliance/`): 30-day and 7-day RTO FC inspection alerts.
19. **PNR Group Arrival Manifest** (`/operations/pnr-arrivals/`): Live airport gate placards, flight/train delay badges.
20. **Customer Portal & Fleet Showcase** (`/customer-portal/` & `/customer-portal/fleet/`): High-contrast marketing cards, vehicle specifications, transparent rate tables.
21. **Chauffeur Mobile PWA Portal** (`/driver-portal/`): Mobile-optimized high-contrast sunlight inspection checklists and digital twin handover cards.

---

### 6. Zero-CDN 100% Locally Self-Hosted Typography & Asset Architecture

To ensure instant first contentful paint (FCP), complete offline resilience, and total independence from external networks, TravelERP has purged 100% of external runtime CDN scripts and font links:

1. **Precompiled CSS Subsystem**:
   - Replaced browser-compiled Tailwind CDN (4MB runtime script) with precompiled, minified `static/app.css` and extracted component tokens in `static/css/base-ui.css`.
2. **6 Self-Hosted Modern Font Families**:
   - All fonts are served locally in compressed **WOFF2 format** from `static/fonts/` via `static/fonts/fonts.css`:
     - **Plus Jakarta Sans**: Primary modern UI sans-serif for navigation, tables, and form cards.
     - **Outfit**: Contemporary geometric heading font for customer portals and showcase banners.
     - **JetBrains Mono**: Monospace font for telemetry coordinates, PNRs, vehicle reg numbers, and financial figures.
     - **Space Grotesk**: High-tech display sans for analytics radar and telemetry metrics.
     - **Inter**: Neutral, crisp fallback sans for enterprise documentation and data tables.
     - **Material Symbols Outlined**: Clean operational iconography.
   - All fonts use `font-display: swap` to prevent invisible text during loading.
3. **Critical Font Preloading & Anti-FOUT**:
   - The primary UI font is preloaded in the `<head>` of all base templates:
     ```html
     <link rel="preload" href="/static/fonts/plus-jakarta-sans-17.woff2" as="font" type="font/woff2" crossorigin>
     ```
   - This eliminates Flash of Unstyled Text (FOUT) and delivers instantaneous text rendering.
4. **Self-Hosted Vendor Libraries**:
   - **Font Awesome 6.5.1**: Localized in `static/fontawesome/` (CSS + WOFF2 webfonts).
   - **Leaflet 1.9.4**: Localized in `static/leaflet/` (JS, CSS, retina marker images).
   - **Chart.js 4.4.4**: Localized in `static/js/chart.umd.min.js` with `defer` loading.
   - **Alpine.js 3.14.3 & HTMX 1.9.10**: Localized in `static/js/`.
5. **PWA Service Worker v4 Pre-Caching**:
   - Cached in `static/sw.js` under the cache bucket `sgt-travelerp-v4` for instant sub-millisecond local retrieval even when completely offline.

