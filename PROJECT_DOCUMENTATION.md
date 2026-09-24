# TravelERP Project Documentation

## 1. Project At A Glance

**Project name:** TravelERP

**Business:** Sivagayathiri Tours and Travels, Coimbatore, Tamil Nadu

**Project type:** Single-user web application for cab and travel operations

**Main goal:** Replace spreadsheet-based travel operations with structured, connected records for customers, bookings, trips, vehicles, employees, billing, expenses, payments, ledgers, statements, and profitability.

TravelERP is built with Django and uses server-rendered HTML templates. Django Admin is the main data-entry workspace for most records, while the custom website provides the daily dashboard, booking-to-trip workflow, ledgers, reports, and statement exports.

This document describes what the code currently does. It is intended to help a human developer or an AI assistant understand the project quickly and accurately.

---

## 2. What The System Does

The application supports this overall business cycle:

1. Create the company master data: customers, suppliers, drivers, cleaners, vehicles, and rate cards.
2. Receive a customer travel request and create a Booking.
3. Convert the Booking into one or more Trips.
4. Assign a vehicle and driver and record the journey details.
5. Calculate the customer charge from the selected billing model.
6. Record trip expenses, fuel, supplier costs, driver advances, and settlements.
7. Record customer receipts, supplier payments, or ledger adjustments.
8. Review party balances and profitability.
9. Generate a PDF or Excel statement for a customer or supplier.

The same system also supports employee transportation contracts, daily vehicle assignments, driver/cleaner crew assignments, and employee payments.

---

## 3. Technology Stack

- Python 3.12.10 in the configured environment
- Django 6.0.2
- SQLite database stored in `db.sqlite3`
- Django templates for the user interface
- ReportLab 4.2.2 for PDF statements
- openpyxl 3.1.5 for Excel statements
- Gunicorn 23.0.0 for deployment serving
- WhiteNoise 6.9.0 for static files
- Responsive CSS in `static/app.css`
- Time zone: `Asia/Kolkata`

### Main Django applications

| App | Responsibility |
|---|---|
| `core` | Parties, drivers, cleaners, vehicles, rate cards, workforce history |
| `operations` | Bookings, trips, journeys, crew, employee transport |
| `finance` | Expenses, fuel, supplier costs, advances, settlements, payments |
| `statements` | Statement history, row building, PDF and Excel exports |
| `travelerp` | Project settings, URLs, dashboard, reports, shared views |

---

## 4. Repository Structure

```text
travelerp/
  settings.py       Django configuration
  urls.py           Application URL routing
  views.py          Dashboard, ledger, and report views
  reports.py        Profitability calculations
  asgi.py           ASGI entry point
  wsgi.py           WSGI entry point

core/
  models.py         Parties, drivers, cleaners, vehicles, rate cards
  admin.py          Admin configuration
  tests.py          Core validation tests
  management/
    commands/
      seed_mock_data.py
      remove_mock_data.py
  migrations/

operations/
  models.py         Bookings, trips, journeys, crew, employee transport
  forms.py          Booking and trip forms
  services.py       Rate-card selection
  views.py          Booking and trip web workflow
  admin.py          Admin configuration
  tests.py          Operations tests
  migrations/

finance/
  models.py         Financial and cost records
  services.py       Party ledger calculations
  admin.py          Admin configuration
  tests.py          Finance tests
  migrations/

statements/
  models.py         Generated statement history
  forms.py          Statement filter form
  services.py       Statement row and balance preparation
  renderers.py      PDF and Excel rendering
  views.py          Statement generation and downloads
  admin.py          Admin configuration
  tests.py          Statement tests
  migrations/

templates/
  base.html
  registration/login.html
  dashboard.html
  party_ledger.html
  profitability_report.html
  operations/
  statements/

static/app.css      Shared application styles
staticfiles/        Collected static files
media/              Uploaded receipts and documents
manage.py           Django command entry point
requirements.txt    Python dependencies
README.md           Setup and user workflow notes
```

---

## 5. Data Model

### 5.1 Party

`core.Party` represents a business or person connected to the company.

Supported party types:

- Travel agency
- Corporate customer
- Hotel
- Individual customer
- Supplier
- Other

A Party stores contact details, billing cycle, credit period, default day and kilometre rates, opening balance, and active/inactive state.

A Party can have:

- Many bookings
- Many trips
- Many rate cards
- Many payments
- Many ledger adjustments
- Employee transport contracts as a customer
- Supplied vehicles as a supplier

### 5.2 Driver

`core.Driver` represents a driver or employee who can be assigned to trips.

It stores contact details, licence information, joining date, employment status, employer party, and default batta rate.

A driver can have:

- Many trips
- Many crew assignments
- Many advances
- Many settlements
- Many employee payments
- Many employment periods

### 5.3 DriverEmploymentPeriod

`core.DriverEmploymentPeriod` stores employment history, including re-hiring periods.

Rules:

- Leaving date cannot be earlier than joining date.
- A driver can have only one active period with no leaving date.

### 5.4 Cleaner

`core.Cleaner` represents a cleaner or support employee.

It stores employer, contact details, joining date, status, default daily rate, and whether the cleaner can drive.

Cleaners can be assigned to trip crews and can receive employee payments.

### 5.5 Vehicle

`core.Vehicle` represents an owned fleet vehicle or an outsourced supplier vehicle.

It stores:

- Registration number
- Vehicle type, brand, model, year, and seating capacity
- Ownership type
- Supplier owner when outsourced
- Fuel type
- Current kilometre reading
- Availability or maintenance status
- Insurance, FC, and permit expiry dates

Rules:

- Registration number is unique.
- An outsourced vehicle must have a supplier owner.
- An owned vehicle cannot have a supplier owner.

When a completed, billed, or settled trip has a closing kilometre reading, the vehicle current kilometre value is updated to the highest known reading.

### 5.6 RateCard

`core.RateCard` stores customer-specific billing rates.

A rate card contains:

- Party
- Vehicle type
- Optional exact vehicle override
- Day rate
- Kilometre rate
- Extra kilometre rate
- Driver batta
- Night, airport, permit, and other charges
- Effective start and optional end date

Rate selection checks the active exact-vehicle rate first. If no exact-vehicle rate exists, it checks the active vehicle-type rate. A trip copies the selected core rates into its own fields so later rate-card edits do not change historical trip billing.

### 5.7 Booking

`operations.Booking` represents the original customer request or itinerary.

It stores:

- Automatically generated booking number such as `BK-0001`
- Customer party
- Guest name and phone
- Booking date
- Pickup location and destination
- Pickup date and time
- Journey type
- Required vehicle type
- Special requirements and plan details
- Itinerary status
- Hotel confirmation status
- Notes

Supported journey types include local, outstation, airport, one way, and round trip.

One Booking can have multiple Trips.

### 5.8 Trip

`operations.Trip` is the operational and billing record created from a booking.

It stores:

- Automatically generated trip ID such as `TR-0001`
- Booking and party
- Guest name
- Vehicle and primary driver
- Operational status
- Start and end dates and times
- Opening and closing kilometres
- Billing model and copied rates
- Days count
- Driver batta
- Commission
- Advance received
- Hotel information
- Partner handover notes

Supported statuses:

- Booked
- Assigned
- Driver confirmed
- Started
- Completed
- Cancelled
- Billed
- Settled

Supported billing models:

- Kilometre
- Day
- Day plus kilometre
- Fixed
- Custom

Important calculated values:

- `used_km = closing_km - opening_km`, never below zero
- `km_amount = used_km * km_rate`
- `day_amount = days_count * day_rate`
- Day-plus-kilometre billing adds both amounts
- Fixed and custom billing use `fixed_amount`
- `total_expenses` includes only customer-billable trip expenses
- `total_amount = bill_value + total_expenses`
- `balance = total_amount - received_amount`

Customer receipts linked to the trip are used for `received_amount`. If there are no customer receipt records, the legacy `advance_received` field is used.

Trip-generated messages:

- Customer confirmation message
- Internal handover message

### 5.9 TripJourney

`operations.TripJourney` stores route segments inside a trip.

It can record:

- Start and end locations
- Start and end kilometres
- Start and end timestamps

### 5.10 TripCrewAssignment

`operations.TripCrewAssignment` assigns one worker to a trip with a role.

Roles:

- Driver
- Cleaner
- Driver plus cleaner
- Additional driver

Validation prevents ambiguous assignments and checks the special driver-plus-cleaner behavior. A driver-plus-cleaner row uses the Driver field and does not create a duplicate cleaner assignment.

### 5.11 Employee Transport Contract

`operations.EmployeeTransportContract` represents a recurring employee transportation service for a customer.

It stores customer, date range, billing model, vehicle-day rate, status, GST rate, and notes.

Contract dates are validated so the end date cannot be before the start date.

### 5.12 Employee Transport Day

`operations.EmployeeTransportDay` represents one operating date in a contract.

It stores required vehicle count and notes.

Rules:

- A date can appear only once within a contract.
- The operating date must fall inside the contract date range.

### 5.13 Employee Transport Assignment

`operations.EmployeeTransportAssignment` assigns a vehicle and optional driver/cleaner for one employee transport day.

It stores route, start/end times, opening/closing kilometres, customer rate, supplier cost, and status.

Rules:

- Closing kilometres cannot be below opening kilometres.
- Outsourced vehicles require a positive supplier cost.
- The same vehicle cannot be assigned more than once on the same contract day when active.

### 5.14 TripExpense

`finance.TripExpense` records a cost or customer extra connected to a trip.

Expense types include toll, permit, parking, driver food, hotel, water, snacks, repair, and other.

It stores amount, date, description, receipt upload, who paid, and whether the expense is billable to the customer.

Examples:

- Water bottles and snacks can be customer-billable.
- Company repairs can be recorded as non-billable internal costs.

### 5.15 SupplierTripCost

`finance.SupplierTripCost` records what the company owes to an outsourced vehicle supplier for a trip.

Rules:

- The vehicle must be outsourced.
- The supplier must match the vehicle owner.
- The cost vehicle must match the trip vehicle.
- The supplier Party must have supplier type.

Supplier cost reduces profitability but does not change the customer amount billed.

### 5.16 FuelRecord

`finance.FuelRecord` records fuel usage for a vehicle and optionally links it to a trip.

It stores fuel quantity, price, fuel station, date, and kilometre readings.

Calculated values:

- Fuel amount
- Distance travelled
- Mileage

Closing kilometres cannot be below opening kilometres.

### 5.17 DriverAdvance

`finance.DriverAdvance` represents money requested or issued to a driver.

The trip link is optional, so a request can exist before it is associated with a specific trip.

A single advance can be split across multiple trips using `DriverAdvanceAllocation`.

Calculated values:

- Allocated amount
- Remaining amount

### 5.18 DriverAdvanceAllocation

`finance.DriverAdvanceAllocation` assigns part of a driver advance to one trip.

Rules:

- Advance and trip drivers must match.
- The same advance cannot be allocated to the same trip twice.
- Total allocations cannot exceed the advance amount.

### 5.19 DriverSettlement

`finance.DriverSettlement` records driver batta settlement for a trip.

It stores driver, trip, days, batta, advance adjusted, and settlement date.

Rules:

- Settlement driver must match the trip driver.
- Advance adjusted cannot exceed batta.

The remaining settlement balance is `batta - advance_adjusted`.

### 5.20 EmployeePayment

`finance.EmployeePayment` records a payment made to exactly one driver or cleaner.

Supported payment types:

- Advance
- Daily pay
- Settlement
- Salary

Supported payment modes include cash, UPI, bank transfer, cheque, card, and other.

Rules:

- Exactly one of driver or cleaner must be selected.
- Amount must be greater than zero.
- A driver payment linked to a trip must match that trip's primary driver.

### 5.21 Payment

`finance.Payment` records a financial transaction for a party.

Payment types:

- Customer receipt
- Supplier payment
- Advance
- Adjustment

Payment modes:

- Cash
- UPI
- Bank transfer
- Cheque
- Card
- Other

Rules:

- Amount must be greater than zero.
- A payment linked to a trip must use the same party as that trip.

Customer payments can be split into multiple Payment rows, for example cash, UPI, and card payments for one bill.

### 5.22 LedgerAdjustment

`finance.LedgerAdjustment` records a signed adjustment against a party ledger.

It stores party, date, amount, and description.

### 5.23 GeneratedStatement

`statements.GeneratedStatement` stores statement history and the filters used to create an export.

It stores:

- Party
- Date range
- PDF or Excel format
- Generation timestamp
- Opening and closing balance snapshots
- Optional vehicle and driver filters
- Optional trip status filter

---

## 6. Main User Workflows

### 6.1 First-Time Setup

1. Install dependencies.
2. Run migrations.
3. Create a superuser.
4. Log in through the application or Admin.
5. Create customers and suppliers.
6. Create drivers and cleaners.
7. Create owned and outsourced vehicles.
8. Create party and vehicle rate cards.

### 6.2 Booking To Trip

1. Open the booking list.
2. Create a booking with customer, guest, route, date, time, journey type, and vehicle type.
3. The system generates a booking number.
4. Open the booking detail page.
5. Create a trip from the booking.
6. The system generates a trip ID, copies the party and guest, sets the initial date, and selects an active rate card where possible.
7. Assign vehicle and driver using the trip form or Admin.
8. Record operational dates, times, kilometres, hotel details, and handover notes.
9. Update the trip status as work progresses.
10. Mark the trip completed after the journey.

### 6.3 Billing And Customer Receipts

1. Select a billing model.
2. Enter actual opening and closing kilometres after the trip.
3. Enter days count for day-based billing.
4. Add customer-billable extras as TripExpense records.
5. Review the calculated trip total.
6. Record one or more customer receipt Payment records when money is actually received.
7. Use the trip balance and party ledger to confirm what remains due.

Payment timing is independent of trip timing. A customer may pay immediately, later, or in multiple parts.

### 6.4 Outsourced Supplier Work

1. Create a Party with type Supplier.
2. Create a Vehicle marked Outsourced / supplier.
3. Set the supplier as the vehicle owner.
4. Assign the outsourced vehicle to a trip.
5. Create a SupplierTripCost for the trip.
6. Record supplier payments against the supplier Party.
7. Generate a supplier statement to see trip costs, payments, and remaining payable balance.

### 6.5 Driver Money And Settlement

1. Create a DriverAdvance for a money request.
2. Leave the trip blank if the request is not yet tied to a trip.
3. Allocate the advance across one or more trips using DriverAdvanceAllocation.
4. Create a DriverSettlement after the trip.
5. Enter batta and the amount adjusted from advances.
6. Use the settlement balance to see what remains payable.

### 6.6 Employee Transport

1. Create an EmployeeTransportContract for a customer.
2. Add one EmployeeTransportDay for each operating date.
3. Set the required number of vehicles.
4. Add one EmployeeTransportAssignment for each vehicle.
5. Mix owned and outsourced vehicles when necessary.
6. Add the driver, cleaner, route, times, kilometres, customer rate, and supplier cost.
7. Use TripCrewAssignment when a trip has multiple crew members.
8. Record separate EmployeePayment records for driver and cleaner pay.

### 6.7 Party Ledger

The party ledger combines:

- Opening balance
- Customer trip charges
- Customer receipts
- Supplier trip costs
- Supplier payments
- Driver advances where applicable
- Ledger adjustments

It calculates the balance for a selected period. The service layer supports date, vehicle, driver, and status filters.

### 6.8 Statements

1. Open Statement Generation.
2. Select a customer or supplier Party.
3. Enter the date range.
4. Optionally choose vehicle, driver, and trip status.
5. Choose PDF or Excel.
6. Generate the file.
7. The statement is saved in GeneratedStatement history and can be downloaded again.

PDF output uses a landscape, multi-page format with repeating headers, page numbers, trip rows, payment rows, and a final reconciliation section. Excel output uses an openpyxl workbook.

### 6.9 Profitability Reports

The application provides:

- Vehicle profitability report
- Party profitability report

Reports group completed, billed, or settled trips and calculate revenue and costs such as:

- Trip billing
- Trip expenses
- Fuel
- Driver batta
- Supplier trip costs

The result includes cost and profit values grouped by vehicle or party.

---

## 7. Web Pages And URLs

All application pages are login-protected unless stated otherwise.

| URL | Purpose |
|---|---|
| `/` | Redirects to dashboard |
| `/login/` | Login page |
| `/logout/` | Logs out the current user |
| `/admin/` | Django Admin workspace |
| `/dashboard/` | KPI dashboard and operational overview |
| `/bookings/` | Searchable and filterable booking list |
| `/bookings/create/` | Create a booking |
| `/bookings/<id>/` | View booking and related trips |
| `/bookings/<id>/trip/create/` | Create a trip from a booking |
| `/trips/<id>/` | View trip details and generated messages |
| `/trips/<id>/status/` | Update trip status |
| `/trips/<id>/customer-confirmation/` | Preview customer confirmation message |
| `/parties/<id>/ledger/` | View a party ledger |
| `/statements/generate/` | Generate PDF or Excel statement |
| `/statements/<id>/download/` | Download a saved statement |
| `/reports/vehicle-profitability/` | Vehicle profitability |
| `/reports/party-profitability/` | Party profitability |

### UI pages

- Login page
- Shared base layout and navigation
- Dashboard
- Booking list
- Booking creation form
- Booking detail
- Trip creation form
- Trip detail
- Customer confirmation preview
- Party ledger
- Profitability reports
- Statement generation form

Finance, workforce, employee transport, and most CRUD screens are provided by Django Admin rather than custom pages.

---

## 8. Admin Workspace

All models are registered with Django Admin.

Admin configuration includes list displays, filtering, search fields, and related record management. Driver advance allocations are available as an inline under the driver advance record.

Admin is currently the primary interface for:

- Parties
- Drivers and cleaners
- Vehicles and rate cards
- Trip journeys and crew assignments
- Expenses and fuel records
- Supplier costs
- Driver advances and allocations
- Driver settlements
- Employee payments
- Customer and supplier payments
- Ledger adjustments
- Employee transport contracts and assignments
- Generated statement history

---

## 9. Validation And Business Rules

The application validates important data at the model layer using Django `clean()` methods.

Key validation rules:

- Booking and trip identifiers are generated automatically.
- Trip end date cannot be before start date.
- Closing kilometres cannot be below opening kilometres.
- Trip party and guest must match the booking.
- A vehicle cannot be assigned to overlapping active/completed/billed/settled trips.
- Outsourced vehicles require a supplier owner.
- Owned vehicles cannot have supplier owners.
- Supplier costs must use the outsourced vehicle's owner.
- Employee transport dates must be within the contract period.
- A vehicle cannot be assigned twice on the same employee transport day.
- Driver advance allocations cannot exceed the original advance.
- Advance allocation driver must match the trip driver.
- Employee payments must belong to exactly one driver or cleaner.
- Payments and settlements cannot use invalid or excessive amounts.
- A driver can have only one active employment period.

---

## 10. Seed And Cleanup Commands

### Seed demo data

```powershell
python manage.py seed_mock_data
```

The command creates repeatable demo data, including approximately:

- 100 customer parties
- 25 suppliers
- 120 drivers
- 30 cleaners
- 120 vehicles
- 1,000 bookings and trips
- Expenses and fuel records
- Driver advances and settlements
- Customer and supplier payments
- Supplier costs
- Employee transport data
- Employee payments
- Generated statements

Demo records are identified with the `DEMO-` prefix where applicable. The seed command is transactional and intended for development/testing data.

### Remove demo data

```powershell
python manage.py remove_mock_data
```

This removes identified demo records while preserving the company Party and non-demo records. Cleanup is currently incomplete for some record types; see the unfinished work section.

---

## 11. Installation And Running

### Windows setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### Initialize the database

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### Run locally

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and log in. The Admin workspace is at `http://127.0.0.1:8000/admin/`.

### Static files

```powershell
python manage.py collectstatic --noinput
```

---

## 12. Configuration

Important settings are in `travelerp/settings.py`:

- SQLite database path
- Installed Django apps
- Template directory
- Static and media directories
- Login and logout redirects
- Asia/Kolkata time zone
- Company name and location
- Development secret key
- Development debug mode
- Allowed local hosts

The project has both WSGI and ASGI entry points. PythonAnywhere deployment guidance exists in `README.md`.

---

## 13. Testing Status

Tests are distributed across the project:

- `core/tests.py`: employment period validation
- `operations/tests.py`: numbering, rate cards, billing, crew, employee transport, filters, and messages
- `finance/tests.py`: ledgers, advances, allocations, and payments
- `statements/tests.py`: rows, PDF, Excel, generation, and downloads
- `travelerp/tests.py`: authentication, UI smoke tests, workflow, reports, statements, and validation

Commands:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test -v 1
```

The verified project state reports:

- Django system check passes.
- No missing migrations are reported.
- 24 tests are discovered and pass.

The tests cover the most important current behavior, including:

- Login protection
- Booking and trip workflow
- Rate-card fallback
- Automatic identifiers
- Kilometre billing
- Billable customer extras
- Customer receipts and split payments
- Party ledger calculations
- Outsourced supplier costs
- Supplier statements
- Driver advances and settlements
- Employee payments
- PDF and Excel output
- Profitability reports
- Mock workflow

---

## 14. Current Implementation Boundaries

The application is intentionally a single-user internal operations tool.

Implemented through the custom website:

- Dashboard
- Booking creation and search
- Booking details
- Trip creation
- Trip details
- Status update
- Customer confirmation preview
- Party ledger page
- Profitability reports
- Statement generation and download

Implemented mainly through Admin:

- Master data CRUD
- Finance data entry
- Employee transport data entry
- Crew assignments
- Detailed operational record editing
- Statement history management

---

## 15. Things Not Done Yet

This section lists work that is not currently complete or still needs improvement based on the codebase.

### Product features not included

- No mobile application.
- No separate React or other JavaScript frontend.
- No multi-user roles or fine-grained permissions.
- No historical spreadsheet import tool.
- No dedicated customer or supplier self-service portal.
- No automated email, SMS, or WhatsApp sending of confirmations or statements.
- No online payment gateway integration.
- No full accounting software integration.
- No automated invoice numbering or tax invoice workflow.

### User interface gaps

- No custom finance pages; finance entry requires Django Admin.
- No custom employee transport pages; employee transport entry requires Django Admin.
- No booking edit page or booking delete workflow.
- No custom trip edit page; detailed trip changes require Admin.
- No dedicated UI for adding trip journeys, crew assignments, expenses, fuel, supplier costs, payments, or settlements.
- The party ledger service supports vehicle, driver, date, and status filters, but the party ledger page does not expose all of those filters.

### Business workflow gaps

- Trip status updates accept the listed statuses but do not enforce transition order. For example, a trip may be moved to a later status without a transition policy.
- Status changes do not currently appear to have role-specific permission controls.
- Billing and settlement completion are recorded as statuses but do not provide a complete invoice approval or settlement approval process.
- There is no automated vehicle availability calendar or dispatch board.
- There is no automatic reminder system for expiring insurance, FC, permits, licences, or credit periods.
- There is no automated payroll calculation for drivers or cleaners.
- There is no full GST/tax calculation workflow for normal trips and invoices.

### Reporting and calculation risks

- Some dashboard totals use broad record sets and should be reviewed for exact business-period and trip-status rules.
- Dashboard monthly revenue is not fully restricted to only eligible completed trips in every calculation.
- Profitability currently includes all trip expenses in cost calculations, while customer billing correctly includes only expenses marked billable. The business may need separate cost and billable-expense reporting rules.
- There is no formal accounting period close or audit-lock process.
- There is no export of all reports to CSV or Excel beyond statements.

### Data and maintenance gaps

- `remove_mock_data.py` does not currently remove every type of data created by `seed_mock_data.py`, including some EmployeePayment, employee transport, cleaner, and employment-period records.
- The database is SQLite, which is suitable for development and small single-user use but may not be ideal for a larger production workload.
- There is no documented backup automation.
- There is no production monitoring, error tracking, or audit log for changes.

### Production hardening still required

- Move `SECRET_KEY` to an environment variable or secret manager.
- Set `DEBUG=False` in production.
- Configure the real production domain in `ALLOWED_HOSTS`.
- Configure HTTPS, secure cookies, CSRF trusted origins, HSTS, and other Django security settings.
- Use a production database strategy if the user count or data volume grows.
- Configure a proper media-file storage and backup policy.
- Complete and test deployment configuration for the selected hosting provider.

### Test-suite gaps

- Some intended payment and billing tests in `travelerp/tests.py` are nested inside another test method, so they are not independently discovered by Django's test runner.
- More tests are needed for status transition rules if those rules are added.
- More tests are needed for demo cleanup completeness.
- More tests are needed for dashboard period boundaries and profitability expense semantics.
- More tests are needed for permissions once multi-user roles are introduced.

---

## 16. Recommended Next Development Order

1. Fix test discovery by moving nested test methods to the test class level.
2. Complete `remove_mock_data.py` so every seeded record type is removed safely.
3. Add custom finance and employee transport screens for easier daily use.
4. Add booking and trip edit workflows with clear permissions.
5. Define and enforce allowed trip status transitions.
6. Review dashboard and profitability filters against the business accounting rules.
7. Add invoice and GST workflows if required by the business.
8. Add production security configuration and environment-based settings.
9. Add backups, audit logging, and error monitoring.
10. Consider PostgreSQL and role-based access if the application becomes multi-user.

---

## 17. AI Context Summary

When working on this project, assume the following:

- This is a Django 6.0.2 TravelERP application.
- `core` contains master data and shared entities.
- `operations` contains bookings, trips, and employee transport.
- `finance` contains cost, payment, ledger, and settlement records.
- `statements` builds and renders customer/supplier statements.
- Most data entry is done in Django Admin.
- The public custom workflow is protected by login.
- A Booking is the customer request; a Trip is the actual operational and billing record.
- Trip billing is based on actual kilometres, days, fixed amount, or custom amount.
- Customer-billable expenses increase the trip total; supplier trip costs affect supplier payable and profitability.
- Rate cards are selected by exact vehicle first, then vehicle type, and copied to trips.
- Never assume that all planned product features are implemented: check the unfinished work section and the actual code before making changes.
