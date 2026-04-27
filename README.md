# ✈️ Airline Reservation System (AirBooking)

**CSE 305 Term Project** — Physical Asset Model with Streamlit Dashboard

---

## 👥 Team Members

- Chloe Darosa
- Sungmin Choo
- Jaeheon Park
- Jaehun Yoo

---

## 📋 Project Overview

A full-stack airline reservation system built with **PostgreSQL (Supabase)** and **Streamlit**.
The system supports two user roles:

| Role       | Capabilities                                                                 |
| ---------- | ---------------------------------------------------------------------------- |
| **Staff**  | Create flight schedules, generate flights, view revenue statistics           |
| **Customer** | Search flights, create bookings (seat selection + payment + ticketing), cancel bookings with refund |

### Core Operations

1. **Generate Flights from Schedule** — Create recurring schedules and generate individual flight records
2. **Flight Search** — Search by departure/arrival airport, date, and optional seat class
3. **Create Booking** — Atomic transaction: seat reservation → payment → ticketing
4. **Cancel Booking & Refund** — Atomic transaction: cancel → seat release → refund
5. **Revenue Statistics** — Revenue by time period, route, class breakdown, and load factor

### Advanced Features

- **Indexing & Query Optimization** — Indexes on frequently queried columns (flight date, booking status, routes, etc.)
- **Triggers & Stored Procedures** — Core business logic implemented as PL/pgSQL stored procedures via Supabase RPC

---

## 🗂️ Project Structure

```
cse305/
├── .env                      # Supabase connection credentials
├── 01_schema.sql             # DDL: tables, indexes, views
├── 02_functions.sql          # PL/pgSQL stored procedures (RPC)
├── 03_seed_sample_data.sql   # Sample data for testing
├── app.py                    # Streamlit application (main dashboard)
└── README.md                 # This file
```

---

## 🚀 How to Run

### Prerequisites

- **Python 3.9+**
- **Supabase** project with PostgreSQL database
- **pip** (Python package manager)

### Step 1: Install Python Dependencies

```bash
pip install streamlit supabase python-dotenv pandas
```

### Step 2: Configure Environment Variables

Create a `.env` file in the `cse305/` directory (or edit the existing one):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### Step 3: Set Up the Database (SQL)

> [!IMPORTANT]
> **If the SQL files have already been executed, you can skip this step entirely.**
> If you have already run them in the Supabase SQL Editor, proceed directly to Step 4.

Open **Supabase Dashboard → SQL Editor** and run the following files **in order**:

#### 3-1. Create Schema (Tables, Indexes, Views)

```
01_schema.sql
```

- Creates all tables (`AIRLINE`, `AIRPORT`, `AIRCRAFT`, `CUSTOMER`, `FLIGHT_SCHEDULE`, `FLIGHT`, `BOOKING`, `PAYMENT`, `REFUND`, `TICKET`, etc.).
- Creates indexes for search performance optimization.
- Creates 4 views (`AIRCRAFT_SUMMARY_VIEW`, `BOOKING_VIEW`, `REVENUE_STATS_VIEW`, `FLIGHT_AVAILABILITY_VIEW`).

#### 3-2. Create Stored Procedures (RPC Functions)

```
02_functions.sql
```

- `generate_flights()` — Auto-generates individual flights from recurring schedules
- `search_flights()` — Searches flights by departure/arrival airport, date, and seat class
- `create_booking()` — Creates a booking (seat reservation → payment → ticketing, atomic transaction)
- `cancel_booking()` — Cancels a booking and processes refund (atomic transaction)
- `get_revenue_report()` — Generates revenue statistics report

#### 3-3. Insert Sample Data

```
03_seed_sample_data.sql
```

- Inserts sample airlines, airports, aircraft, seat classes, customers, and other test data.

### Step 4: Run the Application

```bash
cd cse305
streamlit run app.py
```

The app will automatically open in your browser:

```
Local URL: http://localhost:8501
```

---

## 🗄️ Database Schema (Physical Asset Model)

```
AIRLINE ──< AIRCRAFT ──< SEAT_CLASS ──< SEAT_INVENTORY
                │
                ├──< FLIGHT_SCHEDULE ──< STOPOVER
                │           │
                │           └──< FLIGHT ──< BOOKING ──< PAYMENT ──< REFUND
                │                              │
                │                              └──< TICKET
                │
                └──────────────────── FLIGHT (aircraft_id FK)

CUSTOMER ──< BOOKING
AIRPORT  ──< FLIGHT_SCHEDULE (depart/dest)
```

**Key Design:**
- **Physical Asset Model**: Airlines own Aircraft → Aircraft have Seat Classes → Seat Classes contain physical Seat Inventory
- **Airline derivation**: Airline info is derived through `Aircraft → Airline` ownership chain (no redundant airline_id)
- **Atomic transactions**: Booking and cancellation use stored procedures to ensure atomicity

---

## 📊 Tech Stack

| Layer      | Technology                |
| ---------- | ------------------------- |
| Database   | PostgreSQL (Supabase)     |
| Backend    | PL/pgSQL Stored Procedures |
| Frontend   | Streamlit (Python)        |
| ORM/Client | Supabase Python SDK       |
