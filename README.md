# TravelERP

TravelERP is a single-user Django website for cab and travel operations. It replaces a spreadsheet workflow with structured records for parties, bookings, trips, vehicles, drivers, billing, expenses, payments, ledgers, statements, and profitability.

## Features

- Django Admin CRUD for all operational and finance records
- Booking to trip workflow with automatic `BK-0001` and `TR-0001` identifiers
- Rate card selection by party, vehicle type, and effective date
- Kilometer, day, day-plus-kilometer, fixed, and custom billing
- Independent driver money requests stored as Driver Advances, with allocations across one or more trips
- Owned and outsourced vehicles, with supplier/cab-owner tracking and per-trip supplier rental costs
- Trip expenses, fuel records, driver settlements, payments, and adjustments
- Party ledger with opening balance, charges, receipts, supplier payments, advances, and adjustments
- Split customer receipts across cash, UPI/GPay, card, bank transfer, or cheque
- Billable customer extras such as water bottles and snacks
- CAB statement PDF and Excel exports
- Landscape multi-page PDF with repeating table header, page numbers, and reconciliation page
- Vehicle and party profitability reports
- Login-protected dashboard and reporting pages
- Employee transport contracts with daily vehicle requirements and mixed owned/outsourced assignments
- Driver/cleaner crew assignments and separate employee payments

## Technology

- Python 3.12+
- Django 6.0.2
- SQLite
- ReportLab 4.2.2
- openpyxl 3.1.5
- Django templates with responsive CSS

## Project Layout

```text
travelerp/       Django settings, URLs, WSGI
core/            Party, Driver, Vehicle, RateCard
operations/      Booking, Trip, TripJourney, billing services
finance/         Expenses, fuel, advances, settlements, payments, ledger
statements/      Statement history, row building, PDF and Excel exports
templates/       Shared and page templates
static/          Application stylesheet
media/           Uploaded receipts and documents
```

## Windows Setup

Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks script activation for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

The checked-in `.venv` interpreter is also usable without activation:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

## Initialize the Database

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Enter a username, email, and password when prompted. The superuser is used for both the Admin and main application login.

## Run the Application

```powershell
python manage.py runserver
```

Open:

- Main application: http://127.0.0.1:8000/
- Login: http://127.0.0.1:8000/login/
- Dashboard: http://127.0.0.1:8000/dashboard/
- Admin: http://127.0.0.1:8000/admin/
- Statement generator: http://127.0.0.1:8000/statements/generate/

## Recommended Data Entry Order

1. Create a Party in Admin.
2. Create a Driver and Vehicle.
3. Create a Rate Card for the party and vehicle type.
4. Create a Booking. The booking number is generated automatically.
5. Create a Trip from the booking. The trip number and applicable rate are generated automatically when values are omitted.
6. Assign the vehicle and driver, then record dates, times, and opening/closing kilometres.
7. Mark the trip completed after the journey.
8. Add expenses, fuel records, and driver settlement details.
9. Store driver money requests under Finance > Driver money requests as Driver Advances. Leave the optional trip blank when the money is not yet tied to one trip.
10. Use the Driver Advance allocation rows to split one request across multiple trips. For example, allocate a ₹2,000 request across three trips as ₹800, ₹700, and ₹500. Create a second Driver Advance for any later request, such as ₹500.
11. Record customer receipts, supplier payments, or ledger adjustments.
12. Open the party ledger or generate a PDF/Excel statement.

Customer payment timing does not change the trip workflow. Record a customer receipt when money is actually received: it may be after the trip, or 3, 10, 30, or 50 days later. A customer who pays the full amount after the trip uses one receipt; a customer who pays in parts uses one Payment record for each transfer. For example, a ₹15,000 bill can be recorded as ₹5,000 cash, ₹6,000 UPI/GPay, and ₹4,000 card. The payment records must total the customer bill before the trip balance reaches zero.

Record the actual opening and closing kilometres after the trip. If the vehicle runs 1,600 KM, the KM billing uses 1,600 KM even when the estimate was lower. Add customer-provided items such as water bottles and snacks as separate Trip Expense records with `Billable to customer` enabled. Internal costs such as a company repair can be recorded with that option disabled.

## Tests and Checks

Run the full backend, UI route, export, and mock workflow suite:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test -v 1
```

The current suite covers billing, rate-card fallback, numbering, driver advances, ledger reconciliation, authentication redirects, UI route rendering, statement filters, PDF/Excel output, reports, and a complete mock operations flow.

Seed 1,000 realistic bookings and trips, plus large related datasets across the application:

```powershell
python manage.py seed_mock_data
```

The command is repeatable and keeps records with the `DEMO-` prefix. It creates Sivagayathiri Tours and Travels in Coimbatore, realistic customer names and locations, corporate/individual/travel-agency/hotel parties, partner travel suppliers, owned and outsourced vehicles, drivers, bookings, trips, expenses, fuel, advances, settlements, payments, supplier costs, adjustments, and statement history from 2024 through 2026.

Remove only the seeded demo records later, while preserving the company and non-demo records:

```powershell
python manage.py remove_mock_data
```

Collect static assets before deployment:

```powershell
python manage.py collectstatic --noinput
```

## Statement Rules

Customer receipts reduce the party balance. Supplier payments and driver advances increase it. Ledger adjustments use their signed amount.

Rate cards can be entered for a whole vehicle type or for one exact vehicle. When a trip is created, an active exact-vehicle rate is preferred; otherwise the active vehicle-type rate is used. The trip stores a copy of the selected rates so later rate-card edits do not change historical billing.

For outsourced work, create the cab owner as a Party with type `Supplier`, mark the rented Vehicle as `Outsourced / supplier`, and set its owner. Add a Supplier Trip Cost for each outsourced trip. This records the amount payable to the owner and includes it in profitability without changing the amount billed to your customer.

To send a statement to the outsourced owner, select the supplier party in the statement generator. The export lists outsourced trip rental costs, shows the supplier name, subtracts recorded `Supplier payment` transactions, and calculates the remaining payable amount.

For employee transportation, create one `Employee Transport Contract` for the company service, then create one `Employee Transport Day` for each operating date. Set that day's required vehicle count and add one `Employee Transport Assignment` for every bus, car, or van. Owned and outsourced vehicles can be mixed on the same date, and each assignment keeps its own driver, cleaner, route, time, KM, customer rate, and supplier cost. Use `Trip Crew Assignment` when a bus has both a driver and cleaner. If the same person performs both jobs, use the `Driver + cleaner` role with the Driver field only; do not create a duplicate cleaner. Use `Employee Payment` for separate pay amounts, for example driver ₹1,000 and cleaner ₹500, or one combined driver-cleaner payment.

The statement uses the supplied CAB statement style: a dense landscape trip table, separate supplier payment rows, repeating period and party headers, page numbering, and a final reconciliation section. Business-specific reconciliation labels can be adjusted in the statement renderer.

## PythonAnywhere Deployment

1. Upload or clone the project to PythonAnywhere.
2. Create a virtual environment and install `requirements.txt`.
3. Configure a manual web app with the matching Python version.
4. Point the WSGI configuration to `travelerp.wsgi.application`.
5. Set `DEBUG=False` and configure the PythonAnywhere domain in `ALLOWED_HOSTS`.
6. Run `python manage.py migrate` and `python manage.py createsuperuser`.
7. Run `python manage.py collectstatic --noinput`.
8. Map `/static/` to `staticfiles/` and `/media/` to `media/` in the Web tab.
9. Reload the web application.
10. Back up `db.sqlite3` regularly.

Before production, replace the development `SECRET_KEY` with an environment-based secret and configure HTTPS security settings.

## Current Scope

Included: full core operations, finance tracking, driver advances, billing, party ledger, statements, reports, authentication, tests, and deployment preparation.

Not included: mobile applications, a separate JavaScript frontend, multi-user roles, and importing historical spreadsheet data.
