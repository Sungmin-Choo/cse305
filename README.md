# AirBooking — Airline Reservation System

**CSE 305: Principles of Database Systems, Spring 2026**  
SUNY Korea — Term Project

---

## Team Members

| Name | Email |
|---|---|
| Chloe Darosa | elisabethchloe.mbimbedarosa@stonybrook.edu |
| Sungmin Choo | sungmin.choo@stonybrook.edu |
| Jaeheon Park | jaeheon.park@stonybrook.edu |
| Jaehun Yoo   | jaehun.yoo@stonybrook.edu |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL via Supabase |
| Backend Logic | PL/pgSQL (Triggers + Stored Procedures) |
| Frontend | Streamlit (Python) |
| DB Client | Supabase Python SDK |

---

## Project Structure

```
cse305/
├── 01_schema.sql           # DDL: tables, indexes, views
├── 02_functions.sql        # Triggers and stored procedures
├── 03_seed_sample_data.sql # Demo accounts + 2 stopover demo schedules
├── 04_grants.sql           # RLS disable + anon privileges
├── seed_from_csv.py        # ETL: loads nycflights13 flights.csv → Supabase
├── flights.csv             # nycflights13 dataset (336,776 rows, not committed)
├── app.py                  # Streamlit application
├── .env                    # Supabase credentials (not committed)
└── README.md
```

---

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install streamlit supabase python-dotenv pandas
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

> **Where to find keys:** Supabase Dashboard → Project Settings → API.
> `SUPABASE_ANON_KEY` is the public key used by the app.
> `SUPABASE_SERVICE_ROLE_KEY` is the secret key — required by `seed_from_csv.py` only.
> **Never commit `.env` to git.**

### 3. Initialize the Database

Open **Supabase Dashboard → SQL Editor** and run these four files **in order**:

| # | File | What it does |
|---|---|---|
| 1 | `01_schema.sql` | Drops and recreates all tables, indexes, and views |
| 2 | `02_functions.sql` | Creates all triggers and stored procedures |
| 3 | `03_seed_sample_data.sql` | Inserts demo accounts, airlines, airports, aircraft, schedules, and auto-generates flights for the next 60 days |
| 4 | `04_grants.sql` | Grants all privileges and disables Row Level Security |

> ⚠️ `01_schema.sql` drops **all tables and data**. Always finish with `04_grants.sql` — skipping it causes login failures (RLS blocks every query).

### 4. Load Demo Booking Data

Run the network seed script to generate 800+ synthetic bookings for realistic revenue statistics:

```bash
python generate_airline_network_seed.py --reset --reset-schedules --one-per-month --with-bookings
```

This script:
- Creates routes and flights across the demo airline network
- Generates 800+ confirmed bookings owned by a pool account (`pool@demo.local`)
- Caps demo account bookings at realistic counts: **alice = 3, bob = 2, charlie = 5**
- Leaves revenue/load-factor totals unaffected (all bookings are counted)

### 5. Run the Application

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Customer | `alice@example.com` | `1234` |
| Customer | `bob@example.com` | `1234` |
| Customer | `charlie@example.com` | `1234` |
| Staff (Admin) | `admin@airbooking.local` | `1234` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid email or password` (credentials are correct) | `04_grants.sql` was not run — RLS is active, all SELECTs return 0 rows. | Re-run `04_grants.sql` in SQL Editor. |
| `permission denied for schema public` | Supabase now requires explicit `GRANT USAGE ON SCHEMA public`. | Re-run `04_grants.sql`. |
| `SUPABASE_SERVICE_ROLE_KEY must be set` | `.env` is missing the service role key. | Add it: Dashboard → Project Settings → API → *service_role*. |
| App shows no airports after reset | `03_seed_sample_data.sql` was not run. | Re-run all 4 SQL files in order. |
| Bulk Generator returns 0 new bookings | All (flight × seat) slots are already taken. | Re-run the 4 SQL files + seed script to reset data, then try again. |
| EXPLAIN shows "Function Scan" only | `02_functions.sql` has not been re-run after the fix. | Re-run `02_functions.sql` + `04_grants.sql` in SQL Editor. |

### Full Reset Procedure

```bash
# Step 1 — Supabase SQL Editor (run in this exact order):
#   01_schema.sql → 02_functions.sql → 03_seed_sample_data.sql → 04_grants.sql

# Step 2 — Generate demo booking data:
python generate_airline_network_seed.py --reset --reset-schedules --one-per-month --with-bookings

# Step 3 — Launch the app:
streamlit run app.py
```

### Optional: Scale Demo (CSV ETL)

Only needed if you want to demonstrate EXPLAIN ANALYZE on a very large dataset (336k US-domestic flights from nycflights13):

```bash
# Master data only (airlines, airports, aircraft, seat classes) — safe to run alongside demo data
python seed_from_csv.py

# Full scale load: all 336k flights + historical bookings
python seed_from_csv.py --with-flights --with-history 5000
```

> This is **not required** for the Final Demonstration. The network seed script (Step 4 above) provides sufficient data for all demos including EXPLAIN ANALYZE.

### Schema Migration (existing live data only)

To add the `itinerary_id` column to an existing `BOOKING` table without a full reset:

```sql
ALTER TABLE public."BOOKING" ADD COLUMN IF NOT EXISTS itinerary_id uuid NULL;
CREATE INDEX IF NOT EXISTS idx_booking_itinerary ON public."BOOKING" (itinerary_id);
```

Then re-run `02_functions.sql` and `04_grants.sql`.

---

## How to Use the Application

### Authentication (Sidebar)

- **Login tab**: Enter email and password. The app checks the `CUSTOMER` table first, then `STAFF`. On success, role-based navigation is shown in the main area.
- **Register tab**: Creates a new Customer account. Staff accounts are seeded directly — no self-registration for staff.
- **Logout**: Available in the sidebar after login.

---

### Customer Portal

After logging in as a Customer, two tabs are shown:

#### Tab 1 — Search & Book Flights

**Search:**
1. Pick **Departure Airport** and **Arrival Airport** from the dropdowns
2. Pick a **Travel Date** and optionally filter by **Seat Class**
3. Toggle **Include dynamic connections** to also search for two-leg A→hub→B itineraries
4. Click **Search Flights** — results appear as **cards**, sorted by price ascending

**Configure results:**  
Above the cards: sort by Price ↑/↓, Departure time, or Arrival time; toggle Direct / Connections only; filter by airline.

**Direct flight card:**  
Shows flight number, airline, route, times, class, price. Click **Book →** to open an inline seat picker on the same card; select a seat and click **Confirm Booking**.

> **Pre-defined stopover routes** (e.g. `EK350 ICN→DXB→LHR`) appear as direct cards tagged "1 stop (multi-leg route)" with the 15%/stop discount already applied.

**Connection card:**  
Shows two flight numbers, airline, hub airport, layover duration, per-leg times, class, and **total price with savings vs full price**. Click **Book →** to open two inline seat pickers (one per leg); select seats and click **Confirm Itinerary**.

> **Connection pricing:** `(leg1 + leg2) × 0.85`, capped at 90% of the cheapest direct fare — always cheaper than direct.  
> Demo connection routes: `ICN→DXB→LHR` (EK101 + EK201, Economy $765 vs direct EK601 $1000), `ICN→NRT→LAX` (KE101 + KE202, Economy $646 vs direct KE017 $950).

**All booking IDs are handled internally** — no UUID copy-pasting at any step.

#### Tab 2 — My Bookings

1. Click **Load My Bookings** to see confirmed bookings as cards
2. **Direct bookings**: one card per booking with a **Cancel** button
3. **Connection bookings**: both legs grouped into one card (identified by shared `itinerary_id`) with a **Cancel All** button that atomically refunds both legs
4. Refund history section shows all completed refunds

---

### Staff Dashboard

After logging in as Staff, four tabs are shown in demo order:

#### Tab 1 — Master Data

**Create Schedule & Generate Flights:**
1. Select an aircraft (airline is auto-derived from aircraft ownership)
2. Set departure/arrival airports, flight number, times, operating days
3. Set the schedule validity period (Valid From / Valid Until)
4. Set the generation date range (individual flights to create)
5. Click **Create Schedule & Generate Flights** — inserts a `FLIGHT_SCHEDULE` record and calls `generate_flights()`

**View Existing Flights:**
- Pick a date range and click **Load Flights** to see all flights with their availability

#### Tab 2 — Master Data

Full CRUD for all reference tables (shown first in the demo sequence):


| Sub-tab | Table | Operations |
|---|---|---|
| Airlines | `AIRLINE` | Add (IATA code, name, country) / Delete |
| Airports | `AIRPORT` | Add (IATA code, name, city, country) / Delete |
| Aircraft | `AIRCRAFT` | Add (select airline, enter model) / Delete |
| Seat Classes | `SEAT_CLASS` | Add (select aircraft, class, seat count, price) / Delete |

> **Note:** Adding a Seat Class triggers **automatic seat inventory generation** (see Triggers Demo). Deleting an Airline cascades to its Aircraft → Seat Classes → Seat Inventory.

#### Tab 2 — Flights

**Create Schedule:** Select aircraft, set route/flight#/times/days/validity, click **Create Schedule**.

**Generate Flights:** Select a schedule and date range, click **Generate Flights** → calls `generate_flights()`.

**View Existing Flights:** Pick a date range and click **Load Flights**.

#### Tab 3 — Revenue Statistics

Click **Generate Revenue Report** to see:
- A totals strip: total revenue, flights with bookings, routes sold.
- Revenue breakdown table by flight, seat class, and route.
- `class_revenue_pct`: each class's revenue as a percentage of that flight's total.
- `class_load_factor_pct`: confirmed bookings in this class ÷ seats in this class × 100.
- `flight_load_factor_pct`: confirmed bookings on the whole flight ÷ total seats on the aircraft × 100.
- Bar charts: Revenue by Month, by Quarter, by Route (ranked), and by Seat Class.

#### Tab 4 — Advanced Features

Showcases **both** advanced features from the project brief:

1. **Triggers & Stored Procedures** — interactive demos of the three database triggers with live SQL code and live execution. See the [Triggers section](#triggers) below for details.
   - *Demo 2 (`trg_validate_booking`)* selects a seat from the **same aircraft** as the chosen flight, so the status-check path fires as expected (not the aircraft-mismatch path).
2. **Indexing & Query Optimization** — index catalog, a `bulk_generate_test_bookings(N, seed)` panel that loads random bookings, and live **side-by-side** `EXPLAIN ANALYZE` panels for both `search_flights` and `get_revenue_report`.
   - After clicking **Run Bulk Generator**, the N most-recently-created bookings are shown in a scrollable results table.
   - Each EXPLAIN panel shows two plans: **With Indexes** (current schema) on the left and **Without Indexes** (simulated via `SET LOCAL enable_indexscan/enable_bitmapscan = off`) on the right, making the index benefit directly visible. Plans are produced by inlining the base SQL — not by wrapping the function call — so PostgreSQL expands the view and reveals real `Index Scan` / `Seq Scan` nodes.

---

## Database Schema

### Entity-Relationship Overview

```
AIRLINE ──< AIRCRAFT ──< SEAT_CLASS ──< SEAT_INVENTORY
                │
                ├──< FLIGHT_SCHEDULE ──< STOPOVER
                │           │
                └──────────>└──< FLIGHT ──< BOOKING ──< PAYMENT ──< REFUND
                                               │
                                               └──< TICKET

CUSTOMER ──< BOOKING
AIRPORT  ──< FLIGHT_SCHEDULE (depart / dest)
AIRPORT  ──< STOPOVER
```

### Key Design Decisions

**Physical Asset Model**  
Airlines own Aircraft. Aircraft have Seat Classes. Seat Classes contain physical Seat Inventory rows. The airline of any flight is always derived via `Flight → Aircraft → Airline` — never stored redundantly.

**Aircraft assignment on Flight**  
`FLIGHT.aircraft_id` duplicates `FLIGHT_SCHEDULE.aircraft_id` intentionally: it allows individual flights to be reassigned to a different aircraft (common in real operations) without changing the schedule.

**Partial Unique Index for Bookings**  
```sql
CREATE UNIQUE INDEX booking_active_seat_unique
  ON public."BOOKING" (flight_id, seat_id)
  WHERE status != 'cancelled';
```
This prevents double-booking the same seat on the same flight while allowing cancelled bookings to free the seat for rebooking.

**ticket_no is computed, not stored**  
`TICKET` stores only `booking_id` and `issued_at`. The ticket number displayed in the UI is computed as `'TK-' || replace(booking_id::text, '-', '')` inside `BOOKING_VIEW`. This avoids storing a value that is 100% derivable from the primary key.

---

## SQL Implementation

### Views

| View | Purpose |
|---|---|
| `FLIGHT_AVAILABILITY_VIEW` | Used by flight search. Computes `available_seats = seat_count − confirmed bookings` per class per flight |
| `BOOKING_VIEW` | Used by customers to see booking details including airline, seat, ticket number |
| `REVENUE_STATS_VIEW` | Used by staff. Aggregates revenue, booking count, and load factor per flight per class |
| `AIRCRAFT_SUMMARY_VIEW` | Shows each aircraft with its airline name and total seat count |

### Stored Procedures

All core operations are implemented as PL/pgSQL functions callable via Supabase RPC.

#### `generate_flights(p_start_date, p_end_date)`

Iterates every `FLIGHT_SCHEDULE` × every date in the given range. For each combination:
- Skips dates outside the schedule's `valid_from`/`valid_until`
- Matches the date's day-of-week against `days_of_week` (e.g. `'Mon,Wed,Fri'`)
- Skips dates where a flight already exists (`NOT EXISTS` check)
- Handles overnight flights: if `arrival_time ≤ depart_time`, adds 1 day to arrival datetime

```sql
SELECT public.generate_flights('2026-05-01', '2026-05-31');
-- Returns: "N individual flights have been generated from the recurring schedules."
```

#### `search_flights(p_dep_iata, p_arr_iata, p_travel_date, p_class_name)`

Queries `FLIGHT_AVAILABILITY_VIEW` filtered by route, date, class, and `available_seats > 0`. Returns `effective_price` (15% discount per stopover, computed in the view via `ROUND(base_price * GREATEST(1 - 0.15 * stop_count, 0.40), 2)`) and `stop_count`. Also fetches stopover airports using `string_agg` ordered by `stop_order`. Sorted by `effective_price` ascending.

```sql
SELECT * FROM public.search_flights('ICN', 'LHR', '2026-05-12', NULL);
-- EK350 (1 stop) appears with effective_price = base_price * 0.85
```

#### `create_booking(p_customer_id, p_flight_id, p_seat_id, p_amount)`

Atomic transaction — all three steps succeed or all roll back:
1. **INSERT BOOKING** — `trg_validate_booking` fires here and blocks invalid requests
2. **INSERT PAYMENT** — records the charge as `completed`
3. **INSERT TICKET** — records ticket issuance timestamp

A `unique_violation` on `booking_active_seat_unique` (seat already taken) is caught and rethrown as a human-readable exception.

```sql
SELECT public.create_booking(
  'customer-uuid', 'flight-uuid', 'seat-uuid', 350.00
);
-- Returns: booking_id (uuid)
```

#### `cancel_booking(p_booking_id)`

Atomic transaction:
1. **DELETE TICKET** (must delete first due to FK)
2. **UPDATE BOOKING** → `status = 'cancelled'`
3. **UPDATE PAYMENT** → `status = 'refunded'`
4. **INSERT REFUND** → `status = 'completed'`, `refunded_at = now()`

Uses `FOR UPDATE` lock on the PAYMENT row to prevent race conditions.

```sql
SELECT public.cancel_booking('booking-uuid');
-- Returns: "Booking <id> has been successfully cancelled and refunded."
```

#### `get_revenue_report()`

Reads from `REVENUE_STATS_VIEW` and adds `class_revenue_pct`:

```sql
ROUND(100 * v.revenue / NULLIF(SUM(v.revenue) OVER (PARTITION BY v.flight_id), 0), 2)
```

The window function partitions by `flight_id` (which is itself unique per `(schedule, date)`), so each class's revenue is shown as a percentage of that flight's total. The procedure returns two load-factor columns:

- `class_load_factor_pct` — confirmed bookings in this class ÷ seats in this class × 100.
- `flight_load_factor_pct` — confirmed bookings on the whole flight ÷ total seats on the aircraft × 100.

#### `bulk_generate_test_bookings(p_count int, p_seed int)`

Inserts `p_count` random confirmed bookings (each with a paired PAYMENT and TICKET) across existing scheduled flights, respecting the partial unique index. `setseed(p_seed)` makes the selection reproducible. Used by the **Advanced Features → Indexing & Query Optimization** demo to scale the dataset before running `EXPLAIN ANALYZE`.

#### `explain_search_flights(...)` / `explain_revenue_report()`

Execute `EXPLAIN (ANALYZE, BUFFERS, TIMING, FORMAT TEXT)` on the **inlined base SQL** (not on the function call), so the plan reveals actual `Index Scan` / `Seq Scan` nodes on the underlying tables. Each function returns **two plans** back-to-back:

1. **With Indexes** — normal execution using the indexes defined in `01_schema.sql`.
2. **Without Indexes (simulated)** — same query with `SET LOCAL enable_indexscan = off; enable_bitmapscan = off`, forcing sequential scans. The setting is scoped to the function call and reverts automatically.

The app renders these as two labelled code boxes side-by-side, satisfying the project requirement to demonstrate execution plans *with and without* indexes.

---

## Triggers

### Trigger 1 — `trg_auto_generate_seats`

**Fires:** `AFTER INSERT ON SEAT_CLASS` (once per row)  
**Purpose:** Automatically populates `SEAT_INVENTORY` with physical seat rows when a seat class is created.

Seat numbering layout:

| Class | Start Row | Columns | Seats/Row |
|---|---|---|---|
| First | 1 | A, B | 2 |
| Business | 10 | A, B, C, D | 4 |
| Economy | 20 | A, B, C, D, E, F | 6 |

Example: Economy with `seat_count = 6` generates `20A, 20B, 20C, 20D, 20E, 20F`.

**Why this matters:** Staff never manually inserts seat rows. Adding a Seat Class is the sole entry point — the trigger ensures seat inventory always matches the declared count.

### Trigger 2 — `trg_validate_booking`

**Fires:** `BEFORE INSERT ON BOOKING` (once per row)  
**Purpose:** Enforces two integrity constraints that cannot be expressed as simple FK constraints:

1. **Flight must be in `'scheduled'` status** — prevents booking departed, arrived, or cancelled flights
2. **Seat must belong to the same aircraft as the flight** — prevents a customer from booking a seat from a different aircraft

If either check fails, the INSERT is aborted with a descriptive exception. No booking row is written.

### Trigger 3 — `trg_guard_seat_class_update` + `trg_regenerate_seats_after_update`

**Fires:** `BEFORE UPDATE` and `AFTER UPDATE ON SEAT_CLASS`  
**Purpose:** Manages seat count changes safely.

- If `seat_count` is unchanged → both triggers skip (no-op)
- If `seat_count` changes **and active bookings exist** → `BEFORE` trigger raises exception, blocking the update
- If `seat_count` changes **and no active bookings** → `BEFORE` trigger deletes all existing `SEAT_INVENTORY` rows, then `AFTER` trigger regenerates them with the new count

This two-trigger pattern is necessary because you cannot both delete old rows and insert new ones in a single `BEFORE` trigger (the BEFORE trigger cannot observe its own side effects).

---

## Indexes

Created in `01_schema.sql` for query optimization:

| Index | Table | Columns | Optimizes |
|---|---|---|---|
| `idx_flight_date` | `FLIGHT` | `flight_date` | Date-based flight search |
| `idx_flight_status` | `FLIGHT` | `status` | Filtering active/cancelled flights |
| `idx_schedule_route` | `FLIGHT_SCHEDULE` | `depart_airport_iata, dest_airport_iata` | Route lookup |
| `idx_schedule_valid` | `FLIGHT_SCHEDULE` | `valid_from, valid_until` | Schedule validity filtering |
| `idx_booking_customer` | `BOOKING` | `customer_id` | Loading a customer's bookings |
| `idx_booking_flight` | `BOOKING` | `flight_id` | Seat availability count per flight |
| `idx_booking_status` | `BOOKING` | `status` | Filtering confirmed/cancelled |
| `idx_seat_aircraft` | `SEAT_INVENTORY` | `aircraft_id` | Seat lookup by aircraft |
| `idx_seat_class` | `SEAT_INVENTORY` | `class_id` | Seat lookup by class |
| `idx_stopover_schedule` | `STOPOVER` | `schedule_id` | Stopover list for a route |

The partial unique index `booking_active_seat_unique ON BOOKING (flight_id, seat_id) WHERE status != 'cancelled'` acts as both a constraint and an index, covering the most performance-critical booking query.
