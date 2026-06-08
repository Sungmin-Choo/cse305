#!/usr/bin/env python3

import os
import uuid
import random
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client

START_DATE = date(2026, 4, 1)
END_DATE   = date(2026, 8, 31)
TODAY = date(2026, 6, 8)

DAY_NAME_TO_WEEKDAY = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
    "Fri": 4, "Sat": 5, "Sun": 6,
}

NETWORK = {
    "KE": [
        ("KE101", "ICN", "NRT", "09:00:00", "11:20:00", "Mon,Wed,Fri,Sun"),
        ("KE201", "ICN", "LHR", "10:00:00", "17:30:00", "Tue,Thu,Sat"),
        ("KE301", "ICN", "YVR", "12:00:00", "22:00:00", "Mon,Thu,Sat"),
        ("KE401", "ICN", "LAX", "14:00:00", "23:00:00", "Tue,Fri,Sun"),
        ("KE501", "ICN", "DXB", "08:30:00", "13:30:00", "Wed,Sat"),
        ("KE601", "ICN", "JFK", "10:30:00", "11:20:00", "Mon,Wed,Fri,Sun"),
    ],
    "EK": [
        ("EK111", "DXB", "ICN", "09:30:00", "22:00:00", "Mon,Wed,Fri"),
        ("EK211", "DXB", "LHR", "07:00:00", "12:00:00", "Daily"),
        ("EK311", "DXB", "YVR", "10:30:00", "18:30:00", "Tue,Thu,Sat"),
        ("EK411", "DXB", "NRT", "02:00:00", "16:00:00", "Mon,Thu,Sun"),
        ("EK511", "DXB", "JFK", "16:00:00", "22:00:00", "Wed,Sat"),
    ],
    "BA": [
        ("BA101", "LHR", "ICN", "11:00:00", "06:30:00", "Tue,Thu,Sat"),
        ("BA201", "LHR", "DXB", "09:00:00", "18:30:00", "Daily"),
        ("BA301", "LHR", "YVR", "13:00:00", "22:00:00", "Mon,Wed,Fri"),
        ("BA401", "LHR", "JFK", "18:00:00", "21:00:00", "Daily"),
    ],
    "AA": [
        ("AA001", "JFK", "LAX", "08:00:00", "11:10:00", "Daily"),
        ("AA059", "JFK", "SFO", "09:00:00", "12:25:00", "Daily"),
        ("AA141", "JFK", "MIA", "07:30:00", "10:45:00", "Mon,Wed,Fri,Sun"),
        ("AA313", "LGA", "ORD", "06:45:00", "08:20:00", "Daily"),
        ("AA711", "LGA", "DFW", "10:15:00", "13:35:00", "Tue,Thu,Sat"),
    ],
    "B6": [
        ("B61783", "JFK", "MCO", "08:15:00", "11:05:00", "Daily"),
        ("B6505", "EWR", "FLL", "09:00:00", "12:05:00", "Daily"),
        ("B6359", "JFK", "BUR", "07:50:00", "11:15:00", "Mon,Wed,Fri,Sun"),
        ("B697", "JFK", "DEN", "13:00:00", "16:00:00", "Tue,Thu,Sat"),
        ("B6111", "JFK", "SEA", "15:00:00", "18:45:00", "Mon,Fri,Sun"),
    ],
    "DL": [
        ("DL201", "JFK", "ATL", "07:00:00", "09:30:00", "Daily"),
        ("DL301", "JFK", "DTW", "10:30:00", "12:20:00", "Mon,Wed,Fri"),
        ("DL401", "JFK", "MSP", "12:15:00", "14:35:00", "Tue,Thu,Sat"),
        ("DL501", "LGA", "MIA", "08:45:00", "11:55:00", "Daily"),
    ],
    "UA": [
        ("UA101", "EWR", "ORD", "07:20:00", "09:00:00", "Daily"),
        ("UA201", "EWR", "DEN", "09:30:00", "11:50:00", "Daily"),
        ("UA301", "EWR", "IAH", "12:00:00", "14:55:00", "Mon,Wed,Fri,Sun"),
        ("UA401", "EWR", "LAX", "16:00:00", "19:20:00", "Tue,Thu,Sat"),
    ],
    "WN": [
        ("WN101", "BWI", "MCO", "06:50:00", "09:15:00", "Daily"),
        ("WN201", "BWI", "TPA", "10:15:00", "12:35:00", "Mon,Wed,Fri,Sun"),
        ("WN301", "MDW", "DEN", "08:40:00", "10:20:00", "Daily"),
        ("WN401", "MDW", "LAS", "13:10:00", "15:35:00", "Tue,Thu,Sat"),
    ],
    "VX": [
        ("VX101", "JFK", "LAX", "11:00:00", "14:15:00", "Daily"),
        ("VX201", "JFK", "SFO", "15:45:00", "19:10:00", "Mon,Wed,Fri,Sun"),
    ],
    "AS": [
        ("AS101", "JFK", "SEA", "07:30:00", "11:05:00", "Daily"),
        ("AS201", "LAX", "SEA", "13:00:00", "15:40:00", "Daily"),
    ],
    "HA": [
        ("HA101", "LAX", "HNL", "09:00:00", "12:20:00", "Daily"),
        ("HA201", "SEA", "HNL", "11:00:00", "14:55:00", "Tue,Thu,Sat"),
    ],
    "9E": [
        ("9E101", "JFK", "CVG", "08:20:00", "10:40:00", "Daily"),
        ("9E201", "JFK", "BUF", "13:10:00", "14:35:00", "Mon,Wed,Fri"),
    ],
    "EV": [
        ("EV101", "EWR", "DSM", "07:10:00", "09:10:00", "Mon,Wed,Fri"),
        ("EV201", "EWR", "GSP", "11:30:00", "13:20:00", "Tue,Thu,Sat"),
    ],
    "MQ": [
        ("MQ101", "JFK", "RIC", "06:40:00", "08:10:00", "Daily"),
        ("MQ201", "JFK", "TYS", "15:00:00", "17:10:00", "Mon,Wed,Fri"),
    ],
    "US": [
        ("US101", "LGA", "CLT", "08:00:00", "10:15:00", "Daily"),
        ("US201", "LGA", "PHX", "13:10:00", "16:30:00", "Tue,Thu,Sat"),
    ],
    "FL": [
        ("FL101", "ATL", "MCO", "09:10:00", "10:35:00", "Daily"),
        ("FL201", "ATL", "TPA", "14:20:00", "15:45:00", "Mon,Wed,Fri,Sun"),
    ],
    "F9": [
        ("F9101", "DEN", "LAS", "08:30:00", "09:45:00", "Daily"),
        ("F9201", "DEN", "SLC", "13:40:00", "15:05:00", "Tue,Thu,Sat"),
    ],
    "YV": [
        ("YV101", "PHX", "TUL", "07:15:00", "09:10:00", "Mon,Wed,Fri"),
        ("YV201", "PHX", "ABQ", "12:20:00", "13:35:00", "Daily"),
    ],
    "OO": [
        ("OO101", "SLC", "PDX", "09:00:00", "11:05:00", "Daily"),
        ("OO201", "SLC", "BOI", "14:10:00", "15:20:00", "Tue,Thu,Sat"),
    ],
}

POPULARITY = {
    ("ICN", "JFK"): 1.8,
    ("ICN", "LAX"): 1.45,
    ("ICN", "LHR"): 1.30,
    ("DXB", "LHR"): 1.35,
    ("DXB", "JFK"): 1.40,
    ("LHR", "JFK"): 1.38,
    ("JFK", "LAX"): 1.40,
    ("JFK", "SFO"): 1.32,
    ("JFK", "SEA"): 1.20,
    ("LGA", "ORD"): 1.15,
    ("EWR", "LAX"): 1.22,
    ("LAX", "HNL"): 1.25,
}

MONTH_FACTOR = {
    5: 1.00,
    6: 1.12,
}

CLASS_LOAD = {
    "Economy": 0.62,
    "Business": 0.22,
    "First": 0.10,
}

# All bulk-generated bookings are owned by a single mock "pool" customer so the
# three demo accounts (alice/bob/charlie) are not flooded in their My Bookings.
POOL_EMAIL = "pool@demo.local"
POOL_NAME = "Demo Pool"

# Max confirmed bookings shown in each demo account's My Bookings tab.
DEMO_KEEP = {
    "alice@example.com": 3,
    "bob@example.com": 2,
    "charlie@example.com": 5,
}

BATCH_SIZE = 500


def batch_insert(supabase, table_name, rows, batch_size=BATCH_SIZE):
    if not rows:
        return 0
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        supabase.table(table_name).insert(chunk).execute()
        total += len(chunk)
        print(f"    {table_name}: {total}/{len(rows)}", end="\r")
    print()
    return total


def parse_days_of_week(days_str):
    if days_str == "Daily":
        return {0, 1, 2, 3, 4, 5, 6}
    return {
        DAY_NAME_TO_WEEKDAY[p.strip()]
        for p in days_str.split(",")
        if p.strip() in DAY_NAME_TO_WEEKDAY
    }


def combine_datetimes(flight_date, depart_time_str, arrival_time_str):
    dep_t = datetime.strptime(depart_time_str, "%H:%M:%S").time()
    arr_t = datetime.strptime(arrival_time_str, "%H:%M:%S").time()

    dep_dt = datetime.combine(flight_date, dep_t)
    arr_dt = datetime.combine(flight_date, arr_t)
    if arr_dt <= dep_dt:
        arr_dt += timedelta(days=1)

    return dep_dt.isoformat() + "+00:00", arr_dt.isoformat() + "+00:00"


def clear_data(supabase, reset_schedules=False):
    print("\n[Reset] Clearing generated data...")
    supabase.table("TICKET").delete().neq("ticket_id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("REFUND").delete().neq("refund_id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("PAYMENT").delete().neq("payment_id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("BOOKING").delete().neq("booking_id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("FLIGHT").delete().neq("flight_id", "00000000-0000-0000-0000-000000000000").execute()
    if reset_schedules:
        supabase.table("FLIGHT_SCHEDULE").delete().neq("schedule_id", "00000000-0000-0000-0000-000000000000").execute()
    print("  Done.")


def get_maps(supabase):
    airlines = supabase.table("AIRLINE").select("airline_id,iata_code,name").execute().data
    airports = supabase.table("AIRPORT").select("airport_id,iata_code,name,city,country").execute().data
    aircraft = supabase.table("AIRCRAFT").select("aircraft_id,airline_id,model").execute().data
    seat_classes = supabase.table("SEAT_CLASS").select("class_id,aircraft_id,class_name,price,seat_count").execute().data
    seat_inventory = supabase.table("SEAT_INVENTORY").select("seat_id,aircraft_id,class_id").execute().data

    airline_map = {a["iata_code"]: a for a in airlines}
    airport_map = {a["iata_code"]: a for a in airports}

    aircraft_by_airline = {}
    for a in aircraft:
        aircraft_by_airline.setdefault(a["airline_id"], []).append(a)

    seat_class_map = {}
    for sc in seat_classes:
        seat_class_map[(sc["aircraft_id"], sc["class_name"])] = sc

    seats_by_aircraft_class = {}
    for s in seat_inventory:
        seats_by_aircraft_class.setdefault((s["aircraft_id"], s["class_id"]), []).append(s["seat_id"])

    return airline_map, airport_map, aircraft_by_airline, seat_class_map, seats_by_aircraft_class


def create_schedules(supabase, airline_map, airport_map, aircraft_by_airline):
    print("\n[1] Creating schedules (batched)...")

    existing_rows = supabase.table("FLIGHT_SCHEDULE").select(
        "schedule_id, flight_number, depart_airport_iata, dest_airport_iata, aircraft_id"
    ).execute().data

    existing_map = {
        (r["flight_number"], r["depart_airport_iata"], r["dest_airport_iata"]): r
        for r in existing_rows
    }

    schedule_insert_rows = []
    desired_schedule_specs = []

    for airline_iata, routes in NETWORK.items():
        airline = airline_map.get(airline_iata)
        if not airline:
            print(f"  Skipping {airline_iata}: airline not in DB")
            continue

        airline_aircraft = aircraft_by_airline.get(airline["airline_id"], [])
        if not airline_aircraft:
            print(f"  Skipping {airline_iata}: no aircraft in DB")
            continue

        aircraft_id = airline_aircraft[0]["aircraft_id"]

        for flight_no, origin, dest, dep_t, arr_t, dow in routes:
            if origin not in airport_map or dest not in airport_map:
                print(f"  Skipping {flight_no}: missing airport {origin} or {dest}")
                continue

            key = (flight_no, origin, dest)
            desired_schedule_specs.append({
                "key": key,
                "aircraft_id": aircraft_id,
                "airline_iata": airline_iata,
                "flight_number": flight_no,
                "origin": origin,
                "dest": dest,
                "depart_time": dep_t,
                "arrival_time": arr_t,
                "days_of_week": dow,
            })

            if key not in existing_map:
                schedule_insert_rows.append({
                    "aircraft_id": aircraft_id,
                    "depart_airport_iata": origin,
                    "dest_airport_iata": dest,
                    "flight_number": flight_no,
                    "depart_time": dep_t,
                    "arrival_time": arr_t,
                    "days_of_week": dow,
                    "valid_from": START_DATE.isoformat(),
                    "valid_until": END_DATE.isoformat(),
                })

    if schedule_insert_rows:
        batch_insert(supabase, "FLIGHT_SCHEDULE", schedule_insert_rows)

    all_rows = supabase.table("FLIGHT_SCHEDULE").select(
        "schedule_id, flight_number, depart_airport_iata, dest_airport_iata, aircraft_id"
    ).execute().data

    final_map = {
        (r["flight_number"], r["depart_airport_iata"], r["dest_airport_iata"]): r
        for r in all_rows
    }

    schedules = []
    for s in desired_schedule_specs:
        row = final_map.get(s["key"])
        if not row:
            continue
        schedules.append({
            "schedule_id": row["schedule_id"],
            "aircraft_id": row["aircraft_id"],
            "airline_iata": s["airline_iata"],
            "flight_number": s["flight_number"],
            "origin": s["origin"],
            "dest": s["dest"],
            "depart_time": s["depart_time"],
            "arrival_time": s["arrival_time"],
            "days_of_week": s["days_of_week"],
        })

    print(f"  Created/loaded schedules: {len(schedules)}")
    return schedules


def generate_flights(supabase, schedules, one_per_route=False, one_per_month=False):
    print("\n[2] Generating flights (batched)...")

    existing_rows = supabase.table("FLIGHT").select("schedule_id, flight_date").execute().data
    existing_set = {(r["schedule_id"], r["flight_date"]) for r in existing_rows}

    flight_rows = []
    generated = 0

    for s in schedules:
        weekdays = parse_days_of_week(s["days_of_week"])
        d = START_DATE
        months_done = set()  # used by one_per_month mode

        while d <= END_DATE:
            if d.weekday() in weekdays:
                month_key = (d.year, d.month)
                if one_per_month and month_key in months_done:
                    d += timedelta(days=1)
                    continue

                key = (s["schedule_id"], d.isoformat())
                if key not in existing_set:
                    depart_dt, arrival_dt = combine_datetimes(d, s["depart_time"], s["arrival_time"])
                    flight_rows.append({
                        "schedule_id": s["schedule_id"],
                        "aircraft_id": s["aircraft_id"],
                        "flight_date": d.isoformat(),
                        "depart_time": depart_dt,
                        "arrival_time": arrival_dt,
                        "status": "scheduled",
                    })
                    existing_set.add(key)
                    generated += 1

                    if one_per_route:
                        break
                    if one_per_month:
                        months_done.add(month_key)
            d += timedelta(days=1)

    batch_insert(supabase, "FLIGHT", flight_rows)
    print(f"  Generated flights: {generated}")


def ensure_pool_customer(supabase):
    existing = supabase.table("CUSTOMER").select("customer_id").eq("email", POOL_EMAIL).execute().data
    if existing:
        return existing[0]["customer_id"]

    inserted = supabase.table("CUSTOMER").insert({
        "email": POOL_EMAIL,
        "password": "1234",
        "name": POOL_NAME,
    }).execute().data
    print(f"  Created pool customer: {POOL_EMAIL}")
    return inserted[0]["customer_id"]


def assign_demo_bookings(supabase):
    print("\n[4] Capping demo-account bookings (reassign from pool)...")

    demo_rows = supabase.table("CUSTOMER").select("customer_id,email") \
        .in_("email", list(DEMO_KEEP.keys())).execute().data
    demo_id_by_email = {r["email"]: r["customer_id"] for r in demo_rows}

    pool = supabase.table("CUSTOMER").select("customer_id").eq("email", POOL_EMAIL).execute().data
    if not pool:
        print("  No pool customer found. Skipping demo cap.")
        return
    pool_id = pool[0]["customer_id"]

    # Pool-owned confirmed bookings, newest flight first (most likely upcoming).
    candidates = supabase.table("BOOKING") \
        .select("booking_id, FLIGHT!inner(flight_date)") \
        .eq("customer_id", pool_id).eq("status", "confirmed").execute().data
    candidates.sort(key=lambda b: b["FLIGHT"]["flight_date"], reverse=True)

    used = set()
    for email, target in DEMO_KEEP.items():
        demo_id = demo_id_by_email.get(email)
        if not demo_id:
            print(f"  Skipping {email}: account not in DB")
            continue

        existing = supabase.table("BOOKING").select("booking_id", count="exact") \
            .eq("customer_id", demo_id).eq("status", "confirmed").execute().count or 0
        need = max(0, target - existing)

        moved = 0
        for b in candidates:
            if moved >= need:
                break
            if b["booking_id"] in used:
                continue
            supabase.table("BOOKING").update({"customer_id": demo_id}) \
                .eq("booking_id", b["booking_id"]).execute()
            used.add(b["booking_id"])
            moved += 1

        print(f"  {email}: {existing + moved}/{target} confirmed bookings")


def generate_bookings(supabase, seat_class_map, seats_by_aircraft_class, pool_customer_id):
    print("\n[3] Generating bookings/payment/tickets...")

    flights = supabase.table("FLIGHT").select(
        "flight_id, aircraft_id, flight_date, FLIGHT_SCHEDULE!inner(depart_airport_iata,dest_airport_iata,flight_number)"
    ).execute().data

    booking_rows = []
    payment_rows = []
    ticket_rows = []

    booked_set = set()
    existing = supabase.table("BOOKING").select("flight_id,seat_id").eq("status", "confirmed").execute().data
    for b in existing:
        booked_set.add((b["flight_id"], b["seat_id"]))

    inserted = 0

    for flight in flights:
        flight_id = flight["flight_id"]
        aircraft_id = flight["aircraft_id"]
        flight_date = date.fromisoformat(flight["flight_date"])
        dep = flight["FLIGHT_SCHEDULE"]["depart_airport_iata"]
        dest = flight["FLIGHT_SCHEDULE"]["dest_airport_iata"]

        route_factor = POPULARITY.get((dep, dest), 1.0)
        month_factor = MONTH_FACTOR.get(flight_date.month, 1.0)

        for class_name in ["Economy", "Business", "First"]:
            sc = seat_class_map.get((aircraft_id, class_name))
            if not sc:
                continue

            class_id = sc["class_id"]
            price = float(sc["price"])
            seat_ids = seats_by_aircraft_class.get((aircraft_id, class_id), [])
            available = [sid for sid in seat_ids if (flight_id, sid) not in booked_set]

            if not available:
                continue

            load = CLASS_LOAD[class_name] * route_factor * month_factor
            load = min(load, 0.92)

            target = int(len(available) * load)

            if class_name == "Business" and route_factor >= 1.2 and len(available) > 0:
                target = max(target, 1)
            if class_name == "First" and route_factor >= 1.25 and len(available) > 0:
                target = max(target, 1)

            target = min(target, len(available))
            if target <= 0:
                continue

            chosen = random.sample(available, target)

            for seat_id in chosen:
                booking_id = str(uuid.uuid4())
                payment_id = str(uuid.uuid4())
                ticket_id = str(uuid.uuid4())

                days_before = random.randint(1, 20)
                booked_at_date = max(START_DATE, flight_date - timedelta(days=days_before))
                booked_at = datetime.combine(
                    booked_at_date,
                    datetime.min.time()
                ).replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
                booked_at_str = booked_at.isoformat() + "+00:00"

                booking_rows.append({
                    "booking_id": booking_id,
                    "flight_id": flight_id,
                    "customer_id": pool_customer_id,
                    "seat_id": seat_id,
                    "status": "confirmed",
                    "price": price,
                    "booked_at": booked_at_str,
                })
                payment_rows.append({
                    "payment_id": payment_id,
                    "booking_id": booking_id,
                    "amount": price,
                    "method": "credit_card",
                    "status": "completed",
                    "paid_at": booked_at_str,
                })
                ticket_rows.append({
                    "ticket_id": ticket_id,
                    "booking_id": booking_id,
                    "issued_at": booked_at_str,
                })

                booked_set.add((flight_id, seat_id))
                inserted += 1

    batch_insert(supabase, "BOOKING", booking_rows)
    batch_insert(supabase, "PAYMENT", payment_rows)
    batch_insert(supabase, "TICKET", ticket_rows)

    print(f"  Inserted synthetic bookings: {inserted}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate route-based airline network seed data")
    parser.add_argument("--reset", action="store_true", help="Delete TICKET/REFUND/PAYMENT/BOOKING/FLIGHT first")
    parser.add_argument("--reset-schedules", action="store_true", help="Also delete FLIGHT_SCHEDULE first")
    parser.add_argument("--one-per-route", action="store_true", help="Generate exactly 1 FLIGHT per route")
    parser.add_argument("--one-per-month", action="store_true", help="Generate 1 FLIGHT per route per calendar month")
    parser.add_argument("--with-bookings", action="store_true", help="Also generate BOOKING/PAYMENT/TICKET")
    args = parser.parse_args()

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    supabase = create_client(supabase_url, supabase_key)

    if args.reset:
        clear_data(supabase, reset_schedules=args.reset_schedules)

    airline_map, airport_map, aircraft_by_airline, seat_class_map, seats_by_aircraft_class = get_maps(supabase)

    schedules = create_schedules(supabase, airline_map, airport_map, aircraft_by_airline)
    generate_flights(supabase, schedules, one_per_route=args.one_per_route, one_per_month=args.one_per_month)

    if args.with_bookings:
        pool_id = ensure_pool_customer(supabase)
        generate_bookings(supabase, seat_class_map, seats_by_aircraft_class, pool_id)
        assign_demo_bookings(supabase)

    print("\nDone.")
    print(f"Date range: {START_DATE} ~ {END_DATE}")
    if args.one_per_route:
        mode_label = "one flight per route"
    elif args.one_per_month:
        mode_label = "one flight per route per month"
    else:
        mode_label = "all valid operating days"
    print(f"Mode: {mode_label}")
    print(f"Bookings generated: {'yes' if args.with_bookings else 'no'}")


if __name__ == "__main__":
    main()