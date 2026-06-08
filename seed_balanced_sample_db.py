
"""
seed_balanced_sample_db.py

Purpose
-------
Create a more balanced sample database for:
1) Revenue Statistics
2) Indexing / Query Optimization

This script uses the existing helper logic/constants from seed_from_csv.py
but fixes the main bias by:
- selecting routes per carrier more evenly
- sampling flights per (carrier, month) instead of reading top rows only
- generating historical bookings in batches
- ensuring Business / First are not always zero on medium/long-haul routes

Run this AFTER:
  01_schema.sql
  02_functions.sql
  03_seed_sample_data.sql   (optional, but okay)
  04_grants.sql
"""

import argparse
import os
import random
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# Reuse your existing helper data/functions
from seed_from_csv import (
    CSV_PATH,
    TODAY,
    YEAR_SHIFT,
    parse_hhmm,
    distance_tier,
    phase_a_airlines,
    phase_b_airports,
    phase_c_aircraft,
    phase_d_seat_classes,
)

# --------------------------------------------------
# Config
# --------------------------------------------------

ZERO_UUID = "00000000-0000-0000-0000-000000000000"

CLASS_LOAD = {
    "short":  {"Economy": 0.55, "Business": 0.10, "First": 0.02},
    "medium": {"Economy": 0.63, "Business": 0.18, "First": 0.05},
    "long":   {"Economy": 0.70, "Business": 0.26, "First": 0.10},
}

MONTH_FACTOR = {
    1: 0.95,
    2: 0.90,
    3: 1.00,
    4: 1.08,
    5: 1.15,
    6: 1.22,
    7: 1.35,
    8: 1.30,
    9: 1.05,
    10: 1.00,
    11: 1.10,
    12: 1.28,
}

POPULAR_ROUTE_FACTOR = {
    ("JFK", "LAX"): 1.30,
    ("JFK", "SFO"): 1.25,
    ("JFK", "MIA"): 1.20,
    ("JFK", "SEA"): 1.18,
    ("LGA", "ORD"): 1.15,
    ("LGA", "MIA"): 1.12,
    ("EWR", "ATL"): 1.10,
    ("EWR", "DTW"): 1.05,
}

# --------------------------------------------------
# Utility
# --------------------------------------------------

def batch_insert(supabase: Client, table: str, rows: list[dict], batch_size: int = 500) -> int:
    if not rows:
        return 0

    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        supabase.table(table).insert(chunk).execute()
        total += len(chunk)
        print(f"    {table}: {total}/{len(rows)}", end="\r")
    print()
    return total


def clear_generated_data(supabase: Client, clear_schedules: bool) -> None:
    print("\n[Reset] Clearing generated data...")
    supabase.table("TICKET").delete().neq("ticket_id", ZERO_UUID).execute()
    supabase.table("REFUND").delete().neq("refund_id", ZERO_UUID).execute()
    supabase.table("PAYMENT").delete().neq("payment_id", ZERO_UUID).execute()
    supabase.table("BOOKING").delete().neq("booking_id", ZERO_UUID).execute()
    supabase.table("FLIGHT").delete().neq("flight_id", ZERO_UUID).execute()

    if clear_schedules:
        supabase.table("FLIGHT_SCHEDULE").delete().neq("schedule_id", ZERO_UUID).execute()

    print("  Done.")


def get_supabase() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return create_client(url, key)


# --------------------------------------------------
# Phase E (balanced schedules)
# --------------------------------------------------

def phase_e_balanced_schedules(
    df: pd.DataFrame,
    supabase: Client,
    airline_ids: dict[str, str],
    ac_map: dict[tuple, str],
    routes_per_carrier: int = 12,
):
    print("\n[E] Balanced flight schedules...")

    df_clean = df.dropna(subset=["sched_dep_time", "sched_arr_time"]).copy()
    df_clean["flight_number"] = df_clean["carrier"] + df_clean["flight"].astype(int).astype(str)

    grouped = (
        df_clean.groupby(["carrier", "flight_number", "origin", "dest"])
        .agg(
            rows=("carrier", "size"),
            sched_dep_time=("sched_dep_time", lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0]),
            sched_arr_time=("sched_arr_time", lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0]),
            distance=("distance", "median"),
        )
        .reset_index()
    )

    # choose top N routes per carrier by frequency
    selected = []
    for carrier, grp in grouped.groupby("carrier"):
        grp = grp.sort_values(["rows", "distance"], ascending=[False, False]).head(routes_per_carrier)
        selected.append(grp)

    selected_df = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()

    rows = []
    selected_keys = set()

    for _, r in selected_df.iterrows():
        carrier = r["carrier"]
        fn = r["flight_number"]
        origin = r["origin"]
        dest = r["dest"]

        dep_t = parse_hhmm(r["sched_dep_time"])
        arr_t = parse_hhmm(r["sched_arr_time"])
        if dep_t is None or arr_t is None:
            continue

        tier = distance_tier(float(r["distance"]))
        ac_id = ac_map.get((carrier, tier))
        if not ac_id:
            for fallback in ["medium", "short", "long"]:
                ac_id = ac_map.get((carrier, fallback))
                if ac_id:
                    break
        if not ac_id:
            continue

        # valid range across shifted year
        route_rows = df_clean[
            (df_clean["carrier"] == carrier) &
            (df_clean["flight_number"] == fn) &
            (df_clean["origin"] == origin) &
            (df_clean["dest"] == dest)
        ].copy()

        shifted_dates = [
            date(int(y) + YEAR_SHIFT, int(m), int(d))
            for y, m, d in zip(route_rows["year"], route_rows["month"], route_rows["day"])
        ]

        valid_from = min(shifted_dates).isoformat()
        valid_until = max(shifted_dates).isoformat()
        # derive actual days_of_week from all rows of this route
        route_rows = df_clean[
            (df_clean["carrier"] == carrier) &
            (df_clean["flight_number"] == fn) &
            (df_clean["origin"] == origin) &
            (df_clean["dest"] == dest)
        ].copy()

        shifted_dates = [
            date(int(y) + YEAR_SHIFT, int(m), int(d))
            for y, m, d in zip(route_rows["year"], route_rows["month"], route_rows["day"])
        ]
        dow_names = sorted({d.strftime("%a") for d in shifted_dates}, key=lambda x: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].index(x))
        dow_str = ",".join(dow_names)

        rows.append({
            "aircraft_id": ac_id,
            "depart_airport_iata": origin,
            "dest_airport_iata": dest,
            "flight_number": fn,
            "depart_time": dep_t.strftime("%H:%M:%S"),
            "arrival_time": arr_t.strftime("%H:%M:%S"),
            "days_of_week": dow_str,
            "valid_from": valid_from,
            "valid_until": valid_until,
        })
        selected_keys.add((carrier, fn, origin, dest))

    inserted = 0
    skipped = 0
    BATCH = 200
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        try:
            supabase.table("FLIGHT_SCHEDULE").upsert(
                chunk,
                on_conflict="flight_number,depart_time,arrival_time,days_of_week,valid_from,valid_until",
                ignore_duplicates=True,
            ).execute()
            inserted += len(chunk)
        except Exception:
            for row in chunk:
                try:
                    supabase.table("FLIGHT_SCHEDULE").insert(row).execute()
                    inserted += 1
                except Exception:
                    skipped += 1
        print(f"    FLIGHT_SCHEDULE: {min(i + BATCH, len(rows))}/{len(rows)}", end="\r")
    print()
    print(f"  → {inserted} schedules inserted, {skipped} skipped")

    all_sched = supabase.table("FLIGHT_SCHEDULE").select(
        "schedule_id,flight_number,depart_airport_iata,dest_airport_iata,aircraft_id"
    ).execute().data

    sched_map = {}
    for s in all_sched:
        key = (s["flight_number"], s["depart_airport_iata"], s["dest_airport_iata"])
        sched_map[key] = {
            "schedule_id": s["schedule_id"],
            "aircraft_id": s["aircraft_id"],
        }

    return sched_map, selected_keys


# --------------------------------------------------
# Phase F (balanced flights by carrier + month)
# --------------------------------------------------

def phase_f_balanced_flights(
    df: pd.DataFrame,
    supabase: Client,
    sched_map: dict,
    selected_keys: set,
    flights_per_carrier_month: int = 30,
    batch_size: int = 500,
):
    print("\n[F] Balanced flights...")

    df_clean = df.dropna(subset=["sched_dep_time", "sched_arr_time"]).copy()
    df_clean["flight_number"] = df_clean["carrier"] + df_clean["flight"].astype(int).astype(str)
    df_clean["shifted_date"] = [
        date(int(y) + YEAR_SHIFT, int(m), int(d)).isoformat()
        for y, m, d in zip(df_clean["year"], df_clean["month"], df_clean["day"])
    ]
    df_clean["month_num"] = df_clean["month"].astype(int)

    # keep only selected routes
    df_clean = df_clean[
        df_clean.apply(
            lambda r: (r["carrier"], r["flight_number"], r["origin"], r["dest"]) in selected_keys,
            axis=1
        )
    ].copy()

    # balanced sampling by (carrier, month)
    sampled_parts = []
    for (carrier, month_num), grp in df_clean.groupby(["carrier", "month_num"]):
        n = min(flights_per_carrier_month, len(grp))
        sampled_parts.append(grp.sample(n=n, random_state=42))

    sampled_df = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else pd.DataFrame()

    rows = []
    seen = set()

    for _, row in sampled_df.iterrows():
        key = (row["flight_number"], row["origin"], row["dest"])
        sched = sched_map.get(key)
        if not sched:
            continue

        schedule_id = sched["schedule_id"]
        aircraft_id = sched["aircraft_id"]
        shifted = row["shifted_date"]

        dedup_key = (schedule_id, shifted)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        dep_t = parse_hhmm(row["sched_dep_time"])
        arr_t = parse_hhmm(row["sched_arr_time"])
        if dep_t is None or arr_t is None:
            continue

        shifted_d = date.fromisoformat(shifted)
        dep_dt = datetime.combine(shifted_d, dep_t)
        arr_dt = datetime.combine(shifted_d, arr_t)
        if arr_dt <= dep_dt:
            arr_dt += timedelta(days=1)

        rows.append({
            "schedule_id": schedule_id,
            "aircraft_id": aircraft_id,
            "flight_date": shifted,
            "depart_time": dep_dt.isoformat() + "+00:00",
            "arrival_time": arr_dt.isoformat() + "+00:00",
            "status": "scheduled",
        })

    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        try:
            supabase.table("FLIGHT").upsert(
                chunk,
                on_conflict="schedule_id,flight_date",
                ignore_duplicates=True,
            ).execute()
        except Exception:
            supabase.table("FLIGHT").insert(chunk).execute()
        total += len(chunk)
        print(f"    FLIGHT: {total}/{len(rows)}", end="\r")
    print()
    print(f"  → {total} flights inserted")

    past_flights = (
        supabase.table("FLIGHT")
        .select("flight_id,aircraft_id,flight_date,FLIGHT_SCHEDULE!inner(depart_airport_iata,dest_airport_iata,flight_number)")
        .lt("flight_date", TODAY.isoformat())
        .eq("status", "scheduled")
        .execute()
        .data
    )

    return past_flights


# --------------------------------------------------
# Phase G (balanced historical bookings)
# --------------------------------------------------

def infer_tier_from_economy_price(econ_price: float) -> str:
    if econ_price >= 350:
        return "long"
    elif econ_price >= 180:
        return "medium"
    return "short"


def route_factor(dep: str, dest: str) -> float:
    return POPULAR_ROUTE_FACTOR.get((dep, dest), 1.0)


def phase_g_balanced_history(
    supabase: Client,
    past_flights: list[dict],
    batch_size: int = 500,
):
    print("\n[G] Balanced historical bookings...")

    if not past_flights:
        print("  No past flights found — skipping")
        return

    customers = supabase.table("CUSTOMER").select("customer_id").execute().data
    customer_ids = [c["customer_id"] for c in customers]
    if not customer_ids:
        print("  No customers found — skipping")
        return

    seat_classes = supabase.table("SEAT_CLASS").select("class_id,aircraft_id,class_name,price,seat_count").execute().data
    seat_inventory = supabase.table("SEAT_INVENTORY").select("seat_id,aircraft_id,class_id").execute().data
    existing_bookings = supabase.table("BOOKING").select("flight_id,seat_id").eq("status", "confirmed").execute().data
    booked_set = {(b["flight_id"], b["seat_id"]) for b in existing_bookings}

    seats_by_aircraft_class = {}
    class_meta = {}
    econ_price_by_aircraft = {}

    for sc in seat_classes:
        class_meta[(sc["aircraft_id"], sc["class_name"])] = sc
        if sc["class_name"] == "Economy":
            econ_price_by_aircraft[sc["aircraft_id"]] = float(sc["price"])

    for s in seat_inventory:
        key = (s["aircraft_id"], s["class_id"])
        seats_by_aircraft_class.setdefault(key, []).append(s["seat_id"])

    booking_rows = []
    payment_rows = []
    ticket_rows = []

    inserted = 0

    for i, flight in enumerate(past_flights, start=1):
        flight_id = flight["flight_id"]
        aircraft_id = flight["aircraft_id"]
        flight_date = date.fromisoformat(flight["flight_date"])
        dep = flight["FLIGHT_SCHEDULE"]["depart_airport_iata"]
        dest = flight["FLIGHT_SCHEDULE"]["dest_airport_iata"]

        econ_price = econ_price_by_aircraft.get(aircraft_id, 200.0)
        tier = infer_tier_from_economy_price(econ_price)

        month_factor = MONTH_FACTOR.get(flight_date.month, 1.0)
        r_factor = route_factor(dep, dest)

        for class_name in ["Economy", "Business", "First"]:
            meta = class_meta.get((aircraft_id, class_name))
            if not meta:
                continue

            class_id = meta["class_id"]
            base_price = float(meta["price"])
            seat_ids = seats_by_aircraft_class.get((aircraft_id, class_id), [])
            available = [sid for sid in seat_ids if (flight_id, sid) not in booked_set]

            if not available:
                continue

            load = CLASS_LOAD[tier][class_name] * month_factor * r_factor
            load = min(load, 0.95)

            target = round(len(available) * load)

            # prevent Business/First from always disappearing
            if class_name == "Business" and tier in ("medium", "long") and len(available) > 0:
                target = max(target, 1)
            if class_name == "First" and tier == "long" and len(available) > 0:
                target = max(target, 1)

            target = min(target, len(available))
            if target <= 0:
                continue

            chosen = random.sample(available, target)

            for seat_id in chosen:
                booking_id = str(uuid.uuid4())
                payment_id = str(uuid.uuid4())
                ticket_id = str(uuid.uuid4())

                days_before = random.randint(3, 60)
                booked_at = datetime.combine(
                    max(flight_date - timedelta(days=days_before), date(flight_date.year, 1, 1)),
                    datetime.min.time()
                ).replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
                booked_at_str = booked_at.isoformat() + "+00:00"

                booking_rows.append({
                    "booking_id": booking_id,
                    "flight_id": flight_id,
                    "customer_id": random.choice(customer_ids),
                    "seat_id": seat_id,
                    "status": "confirmed",
                    "price": base_price,
                    "booked_at": booked_at_str,
                })
                payment_rows.append({
                    "payment_id": payment_id,
                    "booking_id": booking_id,
                    "amount": base_price,
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

        if i % 100 == 0:
            print(f"    prepared bookings for {i}/{len(past_flights)} past flights")

    print(f"  → prepared {inserted} booking/payment/ticket rows")
    batch_insert(supabase, "BOOKING", booking_rows, batch_size=batch_size)
    batch_insert(supabase, "PAYMENT", payment_rows, batch_size=batch_size)
    batch_insert(supabase, "TICKET", ticket_rows, batch_size=batch_size)

    # past flights become arrived
    past_ids = [f["flight_id"] for f in past_flights]
    for i in range(0, len(past_ids), batch_size):
        chunk = past_ids[i:i + batch_size]
        supabase.table("FLIGHT").update({"status": "arrived"}).in_("flight_id", chunk).execute()

    print(f"  → inserted {inserted} balanced historical bookings")


# --------------------------------------------------
# Summary
# --------------------------------------------------

def print_summary(supabase: Client) -> None:
    print("\n──────────────────────────────────────")
    print("Final row counts:")
    for t in [
        "AIRLINE", "AIRPORT", "AIRCRAFT", "SEAT_CLASS", "SEAT_INVENTORY",
        "FLIGHT_SCHEDULE", "FLIGHT", "BOOKING", "PAYMENT", "TICKET"
    ]:
        r = supabase.table(t).select("*", count="exact", head=True).execute()
        print(f"  {t:<20} {r.count:>8}")
    print("──────────────────────────────────────")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Balanced sample DB generator for AirBooking")
    parser.add_argument("--reset", action="store_true", help="Delete FLIGHT + BOOKING family before reseeding")
    parser.add_argument("--reset-schedules", action="store_true", help="Also delete FLIGHT_SCHEDULE")
    parser.add_argument("--routes-per-carrier", type=int, default=12)
    parser.add_argument("--flights-per-carrier-month", type=int, default=30)
    parser.add_argument("--batch", type=int, default=500)
    args = parser.parse_args()

    supabase = get_supabase()

    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    print(f"  {len(df):,} rows loaded")

    if args.reset:
        clear_generated_data(supabase, clear_schedules=args.reset_schedules)

    # A–D master data
    airline_ids = phase_a_airlines(df, supabase)
    phase_b_airports(df, supabase)
    ac_map = phase_c_aircraft(df, supabase, airline_ids)
    phase_d_seat_classes(supabase, ac_map)

    # E–G balanced data generation
    sched_map, selected_keys = phase_e_balanced_schedules(
        df,
        supabase,
        airline_ids,
        ac_map,
        routes_per_carrier=args.routes_per_carrier,
    )

    past_flights = phase_f_balanced_flights(
        df,
        supabase,
        sched_map,
        selected_keys,
        flights_per_carrier_month=args.flights_per_carrier_month,
        batch_size=args.batch,
    )

    phase_g_balanced_history(
        supabase,
        past_flights,
        batch_size=args.batch,
    )

    print_summary(supabase)
    print("\nDone. Run `streamlit run app.py` and open Revenue Statistics.")


if __name__ == "__main__":
    main()