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

> **Where to find `SUPABASE_SERVICE_ROLE_KEY`:** Supabase Dashboard → Project Settings → API → *service_role* (secret).
> This key is required only by `seed_from_csv.py` (the bulk ETL). It bypasses RLS for large inserts.
> **Never commit this key to git** — keep `.env` in `.gitignore`.

### 3. Run SQL Files in Order

Open **Supabase Dashboard → SQL Editor** and execute in this exact order:

| Step | File | What it does |
|---|---|---|
| 1 | `01_schema.sql` | Drops and recreates all tables, indexes, and views |
| 2 | `02_functions.sql` | Creates triggers and stored procedures |
| 3 | `03_seed_sample_data.sql` | Inserts demo accounts (STAFF + CUSTOMER) and two demo stopover schedules |
| 4 | `04_grants.sql` | Grants schema USAGE + table / view / function privileges, and disables Row Level Security on every table |

> **Important:** `01_schema.sql` starts with `DROP TABLE IF EXISTS ... CASCADE` for all tables.
> Re-running it will **delete all data** and re-arm Supabase's default RLS.
> Always finish with `04_grants.sql` to restore Data-API access.

> **Symptom if step 4 is skipped:** Login returns "Invalid email or password" even with correct credentials, because the SELECT against `CUSTOMER` / `STAFF` silently returns 0 rows under the default-enabled RLS.

> **Symptom — `permission denied for schema public`:** The ETL (or app) cannot read or write any table.
> Root cause: Supabase's updated Data API policy (effective 2026-05-30) requires an explicit
> `GRANT USAGE ON SCHEMA public` — previously this was implicit. The current `04_grants.sql` includes
> this grant. **Fix:** re-run `04_grants.sql` in the SQL Editor, then retry the ETL.

### 4. Load Real Flight Data (ETL)

Run the Python ETL script to load the **nycflights13** dataset (336,776 real US-domestic flights from 2013, date-shifted to 2026):

```bash
# Smoke test — loads ~2 000 flights + 200 historical bookings (~1 min)
python seed_from_csv.py --limit 2000 --with-history 200

# Full load — all 336 k flights + 5 000 historical bookings (~10–15 min)
python seed_from_csv.py --truncate --with-history 5000
```

**What the ETL adds on top of `03_seed_sample_data.sql`:**
- 16 US carriers (AA, DL, UA, B6, WN, AS, HA, F9, …)
- ~108 US airports (EWR, LGA, JFK + 105 destinations)
- Distance-tiered fleet: short/medium/long-haul aircraft per carrier
- ~3,000 flight schedules (one per unique carrier + flight# + route)
- Up to 336,776 individual flights (date-shifted 2013 → 2026)
- Historical BOOKING + PAYMENT + TICKET on past-dated flights (for revenue demo)
- Past flights (before 2026-05-30) are then flipped to `arrived`

**Pricing model:** Economy base varies by distance tier (short < 700 mi → $120; medium → $200; long → $380). Business ≈ 2.5× Economy; First ≈ 5× Economy. Prices are stored on the aircraft's `SEAT_CLASS`, consistent with the physical-asset schema design.

**Demo stopover schedules** (loaded by `03_seed_sample_data.sql`, not the CSV) are kept to demonstrate the 15%-per-stop discount feature — the CSV contains only direct flights.

### 5. Run the Application

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied for schema public` (ETL or app) | Supabase policy (effective 2026-05-30) now requires explicit `GRANT USAGE ON SCHEMA public`. | Re-run `04_grants.sql` in the Supabase SQL Editor, then retry. |
| `Invalid email or password` on login (credentials are correct) | `04_grants.sql` was not run after the last schema reset, so RLS is active and all SELECTs return 0 rows. | Re-run `04_grants.sql`. |
| ETL prints `ERROR: … SUPABASE_SERVICE_ROLE_KEY must be set` | `.env` is missing `SUPABASE_SERVICE_ROLE_KEY`. | Add it: Supabase Dashboard → Project Settings → API → *service_role* (secret). |
| ETL hangs or is very slow | Network throttling with 336 k rows. | Use `--limit 5000` for a quick demo load, or let it run to completion (~10–15 min). |
| App dropdowns show no airports after full reset | `03_seed_sample_data.sql` or the ETL was not run yet. | Run SQL files in order (steps 1–4), then run the ETL. |

### Full reset + reload procedure

If you need to start completely fresh:

```bash
# 1. In Supabase SQL Editor (in this order):
#    01_schema.sql  →  02_functions.sql  →  03_seed_sample_data.sql  →  04_grants.sql

# 2. In your terminal — smoke test first:
python seed_from_csv.py --limit 2000 --with-history 200

# 3. If smoke test passes, full load:
python seed_from_csv.py --truncate --with-history 5000

# 4. Launch the app:
streamlit run app.py
```

---

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Customer | `alice@example.com` | `1234` |
| Customer | `bob@example.com` | `1234` |
| Customer | `charlie@example.com` | `1234` |
| Staff (Admin) | `admin@airbooking.local` | `1234` |

---

## How to Use the Application

### Authentication (Sidebar)

- **Login tab**: Enter email and password. The app checks the `CUSTOMER` table first, then `STAFF`. On success, role-based navigation is shown in the main area.
- **Register tab**: Creates a new Customer account. Staff accounts are seeded directly — no self-registration for staff.
- **Logout**: Available in the sidebar after login.

---

### Customer Portal

After logging in as a Customer, three tabs are shown:

#### Tab 1 — Search & Book Flights

**Search:**
1. Pick **Departure Airport** and **Arrival Airport** from the dropdowns
2. Pick a **Travel Date** and optionally filter by **Seat Class**
3. Click **Search** — results show flight, airline, full route (with stopovers in the middle), departure/arrival times, class, stop count, base price, **effective price**, and available seats. Results are sorted by effective price ascending so stopover deals surface first. No UUIDs are shown.

> **Stopover pricing:** Flights with stopovers receive a **15% discount per stop**, computed in `FLIGHT_AVAILABILITY_VIEW`. A 2-stop itinerary is 30% cheaper, capped at 60% off.

> Sample routes in seed data include `ICN→JFK` (KE001, Mon/Wed/Fri), `HND→LHR` (NH106), `SIN→LHR` (SQ322), `DXB→JFK` (EK202 daily), plus 6 stopover routes such as `ICN→DXB→LHR` (EK350) and `LHR→SFO→SEA→YVR` (BA284, 2 stops). Individual flights must first be generated by Staff via the Flights tab.

**Book directly from results:**
1. After searching, the **Create a Booking** expander auto-populates a selectbox of your search results — labels like `KE001 — ICN → DXB → LHR — 2026-05-15 23:00 — Economy — $297.50 • 1 stop`.
2. Pick the flight; class is locked from the selection. A metrics strip shows class, stop count, and effective price (with the delta vs the direct fare for stopover flights).
3. Pick a **Seat** from the dropdown — only seats currently available for that flight and class appear.
4. Click **Confirm Booking** — the system atomically creates the booking, processes payment at the effective price, and issues a ticket.

#### Tab 2 — My Bookings

1. Click **Load My Bookings** to see all active (confirmed) bookings.
2. Pick a booking from the dropdown — labels look like `KE001 — ICN→JFK — 2026-05-15 — Seat 1A — $1500.00`.
3. Click **Cancel Booking** — the system atomically cancels the booking, marks the payment as refunded, and records a refund entry.

---

### Staff Dashboard

After logging in as Staff, four tabs are shown:

#### Tab 1 — Flights

**Create Schedule & Generate Flights:**
1. Select an aircraft (airline is auto-derived from aircraft ownership)
2. Set departure/arrival airports, flight number, times, operating days
3. Set the schedule validity period (Valid From / Valid Until)
4. Set the generation date range (individual flights to create)
5. Click **Create Schedule & Generate Flights** — inserts a `FLIGHT_SCHEDULE` record and calls `generate_flights()`

**View Existing Flights:**
- Pick a date range and click **Load Flights** to see all flights with their availability

#### Tab 2 — Master Data

Full CRUD for all reference tables:

| Sub-tab | Table | Operations |
|---|---|---|
| Airlines | `AIRLINE` | Add (IATA code, name, country) / Delete |
| Airports | `AIRPORT` | Add (IATA code, name, city, country) / Delete |
| Aircraft | `AIRCRAFT` | Add (select airline, enter model) / Delete |
| Seat Classes | `SEAT_CLASS` | Add (select aircraft, class, seat count, price) / Delete |

> **Note:** Adding a Seat Class triggers **automatic seat inventory generation** (see Triggers Demo). Deleting an Airline cascades to its Aircraft → Seat Classes → Seat Inventory.

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
2. **Indexing & Query Optimization** — index catalog, a `bulk_generate_test_bookings(N, seed)` panel that loads thousands of random bookings, and live `EXPLAIN (ANALYZE, BUFFERS)` panels for both `search_flights` and `get_revenue_report`. Use this to demonstrate index usage on a scaled dataset.

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

Thin wrappers that execute `EXPLAIN (ANALYZE, BUFFERS, TIMING, FORMAT TEXT)` around the corresponding core query and return one text row per plan line. Powers the live executor-plan panels in the app.

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
