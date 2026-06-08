#!/usr/bin/env python3
"""
generate_booking_test_flights.py

Generate exactly ONE FLIGHT per unique route using existing FLIGHT_SCHEDULE rows.

Rules:
- date range: 2026-05-01 ~ 2026-06-10
- one FLIGHT per route (depart_airport_iata, dest_airport_iata)
- choose the first valid operating date in that range
- if a FLIGHT already exists for that schedule/date, skip it

Use this for booking tests, not for large-scale revenue seeding.
"""

import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client

START_DATE = date(2026, 5, 1)
END_DATE = date(2026, 6, 10)

DAY_NAME_TO_WEEKDAY = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}


def parse_days_of_week(days_str: str) -> set[int]:
    if not days_str:
        return set()
    parts = [p.strip() for p in days_str.split(",") if p.strip()]
    return {DAY_NAME_TO_WEEKDAY[p] for p in parts if p in DAY_NAME_TO_WEEKDAY}


def combine_datetimes(flight_date: date, depart_time_str: str, arrival_time_str: str):
    dep_t = datetime.strptime(depart_time_str, "%H:%M:%S").time()
    arr_t = datetime.strptime(arrival_time_str, "%H:%M:%S").time()

    dep_dt = datetime.combine(flight_date, dep_t)
    arr_dt = datetime.combine(flight_date, arr_t)

    # overnight arrival
    if arr_dt <= dep_dt:
        arr_dt += timedelta(days=1)

    return dep_dt.isoformat() + "+00:00", arr_dt.isoformat() + "+00:00"


def find_first_operating_date(valid_from: date, valid_until: date, weekdays: set[int]) -> date | None:
    actual_start = max(START_DATE, valid_from)
    actual_end = min(END_DATE, valid_until)

    if actual_start > actual_end:
        return None

    d = actual_start
    while d <= actual_end:
        if d.weekday() in weekdays:
            return d
        d += timedelta(days=1)

    return None


def main():
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    supabase = create_client(supabase_url, supabase_key)

    print("Loading FLIGHT_SCHEDULE rows...")
    schedules = supabase.table("FLIGHT_SCHEDULE").select(
        "schedule_id, aircraft_id, depart_airport_iata, dest_airport_iata, "
        "flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until"
    ).execute().data

    if not schedules:
        print("No FLIGHT_SCHEDULE rows found.")
        print("You need schedules first.")
        return

    # route당 1개만: 첫 스케줄 하나만 선택
    selected_by_route = {}
    for s in schedules:
        route_key = (s["depart_airport_iata"], s["dest_airport_iata"])
        if route_key not in selected_by_route:
            selected_by_route[route_key] = s

    print(f"Selected {len(selected_by_route)} unique routes.")

    inserted = 0
    skipped = 0

    for route_key, s in selected_by_route.items():
        valid_from = date.fromisoformat(s["valid_from"])
        valid_until = date.fromisoformat(s["valid_until"])
        weekdays = parse_days_of_week(s["days_of_week"])

        if not weekdays:
            print(f"Skipping {s['flight_number']} ({route_key[0]}->{route_key[1]}): empty days_of_week")
            skipped += 1
            continue

        flight_date = find_first_operating_date(valid_from, valid_until, weekdays)
        if not flight_date:
            print(f"Skipping {s['flight_number']} ({route_key[0]}->{route_key[1]}): no valid date in range")
            skipped += 1
            continue

        # 이미 있으면 skip
        existing = supabase.table("FLIGHT").select("flight_id").eq("schedule_id", s["schedule_id"]).eq(
            "flight_date", flight_date.isoformat()
        ).limit(1).execute().data

        if existing:
            print(f"Already exists: {s['flight_number']} {route_key[0]}->{route_key[1]} on {flight_date}")
            skipped += 1
            continue

        depart_dt, arrival_dt = combine_datetimes(
            flight_date,
            s["depart_time"],
            s["arrival_time"],
        )

        supabase.table("FLIGHT").insert({
            "schedule_id": s["schedule_id"],
            "aircraft_id": s["aircraft_id"],
            "flight_date": flight_date.isoformat(),
            "depart_time": depart_dt,
            "arrival_time": arrival_dt,
            "status": "scheduled",
        }).execute()

        print(f"Inserted: {s['flight_number']} {route_key[0]}->{route_key[1]} on {flight_date}")
        inserted += 1

    print("\nDone.")
    print(f"Inserted: {inserted}")
    print(f"Skipped:  {skipped}")


if __name__ == "__main__":
    main()