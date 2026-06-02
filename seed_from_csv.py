#!/usr/bin/env python3
"""
seed_from_csv.py — ETL: nycflights13 → AirBooking Supabase

Loads the nycflights13 CSV (flights.csv, 336,776 rows) into the AirBooking
database without touching the existing schema.  Run this AFTER the four SQL
files (01 → 02 → 03 → 04_grants).

Phases
------
A  AIRLINE      — 16 US carriers from the CSV
B  AIRPORT      — 3 origins + 105 destinations (curated names where known)
C  AIRCRAFT     — distance-tiered fleet (≤3 aircraft per carrier)
D  SEAT_CLASS   — 3 classes per aircraft; trigger auto-creates SEAT_INVENTORY
   [Phases E–H run only with --with-flights]
E  FLIGHT_SCHEDULE — one schedule per distinct (carrier, flight#, origin, dest)
F  FLIGHT       — one row per (schedule, date); dates shifted 2013→2026
G  BOOKING+PAYMENT+TICKET — historical bookings on past-dated flights
H  status flip  — past flights (< 2026-05-30) → arrived

Usage
-----
  python seed_from_csv.py                        # master data only (A–D)
  python seed_from_csv.py --with-flights         # full run including schedules & flights
  python seed_from_csv.py --with-flights --limit 5000           # cap at 5 000 flights
  python seed_from_csv.py --with-flights --with-history 2000    # also create 2 000 historical bookings
  python seed_from_csv.py --with-flights --truncate             # clear FLIGHT+BOOKING first, then reload
  python seed_from_csv.py --with-flights --truncate --with-history 5000  # full clean reload + history

Default (no --with-flights): loads only airlines, airports, aircraft, and seat classes from CSV.
Schedules and flights are created by the staff via the app (or via 03_seed_sample_data.sql for demos).

Requirements
------------
  pip install supabase python-dotenv pandas
  .env must contain SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import os
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

TODAY = date(2026, 5, 30)   # flights before this date → arrived; on/after → scheduled
YEAR_SHIFT = 13             # 2013 → 2026
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flights.csv")

DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ──────────────────────────────────────────────
# Lookup tables
# ──────────────────────────────────────────────

CARRIER_INFO: dict[str, tuple[str, str]] = {
    "9E": ("Endeavor Air",        "United States"),
    "AA": ("American Airlines",   "United States"),
    "AS": ("Alaska Airlines",     "United States"),
    "B6": ("JetBlue Airways",     "United States"),
    "DL": ("Delta Air Lines",     "United States"),
    "EV": ("ExpressJet Airlines", "United States"),
    "F9": ("Frontier Airlines",   "United States"),
    "FL": ("AirTran Airways",     "United States"),
    "HA": ("Hawaiian Airlines",   "United States"),
    "MQ": ("Envoy Air",           "United States"),
    "OO": ("SkyWest Airlines",    "United States"),
    "UA": ("United Airlines",     "United States"),
    "US": ("US Airways",          "United States"),
    "VX": ("Virgin America",      "United States"),
    "WN": ("Southwest Airlines",  "United States"),
    "YV": ("Mesa Air",            "United States"),
}

# (name, city, country) for known airports; others get a generated fallback
AIRPORT_INFO: dict[str, tuple[str, str, str]] = {
    "EWR": ("Newark Liberty International Airport",               "Newark",          "United States"),
    "JFK": ("John F. Kennedy International Airport",              "New York",        "United States"),
    "LGA": ("LaGuardia Airport",                                  "New York",        "United States"),
    "ABQ": ("Albuquerque International Sunport",                  "Albuquerque",     "United States"),
    "ACK": ("Nantucket Memorial Airport",                         "Nantucket",       "United States"),
    "ALB": ("Albany International Airport",                       "Albany",          "United States"),
    "ANC": ("Ted Stevens Anchorage International Airport",        "Anchorage",       "United States"),
    "ATL": ("Hartsfield-Jackson Atlanta International Airport",   "Atlanta",         "United States"),
    "AUS": ("Austin-Bergstrom International Airport",             "Austin",          "United States"),
    "AVL": ("Asheville Regional Airport",                         "Asheville",       "United States"),
    "BDL": ("Bradley International Airport",                      "Hartford",        "United States"),
    "BGR": ("Bangor International Airport",                       "Bangor",          "United States"),
    "BHM": ("Birmingham-Shuttlesworth International Airport",     "Birmingham",      "United States"),
    "BNA": ("Nashville International Airport",                    "Nashville",       "United States"),
    "BOS": ("Boston Logan International Airport",                 "Boston",          "United States"),
    "BQN": ("Rafael Hernandez International Airport",             "Aguadilla",       "Puerto Rico"),
    "BTV": ("Burlington International Airport",                   "Burlington",      "United States"),
    "BUF": ("Buffalo Niagara International Airport",              "Buffalo",         "United States"),
    "BUR": ("Hollywood Burbank Airport",                          "Burbank",         "United States"),
    "BWI": ("Baltimore/Washington International Airport",         "Baltimore",       "United States"),
    "BZN": ("Bozeman Yellowstone International Airport",          "Bozeman",         "United States"),
    "CAE": ("Columbia Metropolitan Airport",                      "Columbia",        "United States"),
    "CAK": ("Akron-Canton Airport",                               "Akron",           "United States"),
    "CHO": ("Charlottesville-Albemarle Airport",                  "Charlottesville", "United States"),
    "CHS": ("Charleston International Airport",                   "Charleston",      "United States"),
    "CLE": ("Cleveland Hopkins International Airport",            "Cleveland",       "United States"),
    "CLT": ("Charlotte Douglas International Airport",            "Charlotte",       "United States"),
    "CMH": ("John Glenn Columbus International Airport",          "Columbus",        "United States"),
    "CRW": ("Yeager Airport",                                     "Charleston",      "United States"),
    "CVG": ("Cincinnati/Northern Kentucky International Airport", "Cincinnati",      "United States"),
    "DAY": ("Dayton International Airport",                       "Dayton",          "United States"),
    "DCA": ("Ronald Reagan Washington National Airport",          "Washington D.C.", "United States"),
    "DEN": ("Denver International Airport",                       "Denver",          "United States"),
    "DFW": ("Dallas/Fort Worth International Airport",            "Dallas",          "United States"),
    "DSM": ("Des Moines International Airport",                   "Des Moines",      "United States"),
    "DTW": ("Detroit Metropolitan Airport",                       "Detroit",         "United States"),
    "EGE": ("Eagle County Regional Airport",                      "Eagle",           "United States"),
    "EYW": ("Key West International Airport",                     "Key West",        "United States"),
    "FLL": ("Fort Lauderdale-Hollywood International Airport",    "Fort Lauderdale", "United States"),
    "GRR": ("Gerald R. Ford International Airport",               "Grand Rapids",    "United States"),
    "GSO": ("Piedmont Triad International Airport",               "Greensboro",      "United States"),
    "GSP": ("Greenville-Spartanburg International Airport",       "Greenville",      "United States"),
    "HDN": ("Yampa Valley Airport",                               "Hayden",          "United States"),
    "HNL": ("Daniel K. Inouye International Airport",             "Honolulu",        "United States"),
    "HOU": ("William P. Hobby Airport",                           "Houston",         "United States"),
    "IAD": ("Washington Dulles International Airport",            "Washington D.C.", "United States"),
    "IAH": ("George Bush Intercontinental Airport",               "Houston",         "United States"),
    "ILM": ("Wilmington International Airport",                   "Wilmington",      "United States"),
    "IND": ("Indianapolis International Airport",                 "Indianapolis",    "United States"),
    "JAC": ("Jackson Hole Airport",                               "Jackson",         "United States"),
    "JAX": ("Jacksonville International Airport",                 "Jacksonville",    "United States"),
    "LAS": ("Harry Reid International Airport",                   "Las Vegas",       "United States"),
    "LAX": ("Los Angeles International Airport",                  "Los Angeles",     "United States"),
    "LEX": ("Blue Grass Airport",                                 "Lexington",       "United States"),
    "LGA": ("LaGuardia Airport",                                  "New York",        "United States"),
    "LGB": ("Long Beach Airport",                                 "Long Beach",      "United States"),
    "MCI": ("Kansas City International Airport",                  "Kansas City",     "United States"),
    "MCO": ("Orlando International Airport",                      "Orlando",         "United States"),
    "MDW": ("Chicago Midway International Airport",               "Chicago",         "United States"),
    "MEM": ("Memphis International Airport",                      "Memphis",         "United States"),
    "MHT": ("Manchester-Boston Regional Airport",                 "Manchester",      "United States"),
    "MIA": ("Miami International Airport",                        "Miami",           "United States"),
    "MKE": ("Milwaukee Mitchell International Airport",           "Milwaukee",       "United States"),
    "MSN": ("Dane County Regional Airport",                       "Madison",         "United States"),
    "MSP": ("Minneapolis-Saint Paul International Airport",       "Minneapolis",     "United States"),
    "MSY": ("Louis Armstrong New Orleans International Airport",  "New Orleans",     "United States"),
    "MTJ": ("Montrose Regional Airport",                          "Montrose",        "United States"),
    "MVY": ("Martha's Vineyard Airport",                          "Vineyard Haven",  "United States"),
    "MYR": ("Myrtle Beach International Airport",                 "Myrtle Beach",    "United States"),
    "OAK": ("Oakland International Airport",                      "Oakland",         "United States"),
    "OKC": ("Will Rogers World Airport",                          "Oklahoma City",   "United States"),
    "OMA": ("Eppley Airfield",                                    "Omaha",           "United States"),
    "ORD": ("O'Hare International Airport",                       "Chicago",         "United States"),
    "ORF": ("Norfolk International Airport",                      "Norfolk",         "United States"),
    "PBI": ("Palm Beach International Airport",                   "West Palm Beach", "United States"),
    "PDX": ("Portland International Airport",                     "Portland",        "United States"),
    "PHL": ("Philadelphia International Airport",                 "Philadelphia",    "United States"),
    "PHX": ("Phoenix Sky Harbor International Airport",           "Phoenix",         "United States"),
    "PIT": ("Pittsburgh International Airport",                   "Pittsburgh",      "United States"),
    "PSE": ("Mercedita Airport",                                  "Ponce",           "Puerto Rico"),
    "PSP": ("Palm Springs International Airport",                 "Palm Springs",    "United States"),
    "PVD": ("T.F. Green International Airport",                   "Providence",      "United States"),
    "PWM": ("Portland International Jetport",                     "Portland",        "United States"),
    "RDU": ("Raleigh-Durham International Airport",               "Raleigh",         "United States"),
    "RIC": ("Richmond International Airport",                     "Richmond",        "United States"),
    "ROC": ("Greater Rochester International Airport",            "Rochester",       "United States"),
    "RSW": ("Southwest Florida International Airport",            "Fort Myers",      "United States"),
    "SAN": ("San Diego International Airport",                    "San Diego",       "United States"),
    "SAT": ("San Antonio International Airport",                  "San Antonio",     "United States"),
    "SAV": ("Savannah/Hilton Head International Airport",         "Savannah",        "United States"),
    "SBN": ("South Bend International Airport",                   "South Bend",      "United States"),
    "SDF": ("Louisville Muhammad Ali International Airport",      "Louisville",      "United States"),
    "SEA": ("Seattle-Tacoma International Airport",               "Seattle",         "United States"),
    "SFO": ("San Francisco International Airport",                "San Francisco",   "United States"),
    "SJC": ("Norman Y. Mineta San Jose International Airport",    "San Jose",        "United States"),
    "SJU": ("Luis Munoz Marin International Airport",             "San Juan",        "Puerto Rico"),
    "SLC": ("Salt Lake City International Airport",               "Salt Lake City",  "United States"),
    "SMF": ("Sacramento International Airport",                   "Sacramento",      "United States"),
    "SNA": ("John Wayne Airport",                                 "Santa Ana",       "United States"),
    "SRQ": ("Sarasota-Bradenton International Airport",           "Sarasota",        "United States"),
    "STL": ("St. Louis Lambert International Airport",            "St. Louis",       "United States"),
    "STT": ("Cyril E. King Airport",                              "Charlotte Amalie","U.S. Virgin Islands"),
    "SYR": ("Syracuse Hancock International Airport",             "Syracuse",        "United States"),
    "TPA": ("Tampa International Airport",                        "Tampa",           "United States"),
    "TUL": ("Tulsa International Airport",                        "Tulsa",           "United States"),
    "TVC": ("Cherry Capital Airport",                             "Traverse City",   "United States"),
    "TYS": ("McGhee Tyson Airport",                               "Knoxville",       "United States"),
    "XNA": ("Northwest Arkansas National Airport",                "Fayetteville",    "United States"),
}

# Aircraft models by carrier type and distance tier
REGIONAL_CARRIERS = {"9E", "EV", "MQ", "OO", "YV"}
TIER_MODELS: dict[str, dict[str, str]] = {
    "regional": {
        "short":  "Embraer E175",
        "medium": "Embraer E190",
        "long":   "Bombardier CRJ-900",
    },
    "mainline": {
        "short":  "Boeing 737-700",
        "medium": "Boeing 737-800",
        "long":   "Boeing 757-200",
    },
}

# Seat counts per tier
TIER_SEATS: dict[str, dict[str, int]] = {
    "short":  {"First": 2, "Business": 4,  "Economy": 18},
    "medium": {"First": 2, "Business": 6,  "Economy": 24},
    "long":   {"First": 4, "Business": 8,  "Economy": 30},
}

# Prices: Economy base; Business ≈ 2.5×; First ≈ 5×
TIER_PRICES: dict[str, dict[str, float]] = {
    "short":  {"First": 600.00,  "Business": 300.00, "Economy": 120.00},
    "medium": {"First": 1000.00, "Business": 500.00, "Economy": 200.00},
    "long":   {"First": 1900.00, "Business": 950.00, "Economy": 380.00},
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def parse_hhmm(val) -> time | None:
    """Parse a HHMM integer (e.g. 515 → 05:15, 2359 → 23:59)."""
    try:
        t = int(float(val))
        h, m = t // 100, t % 100
        if h == 24:
            h = 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return time(h, m)
    except (ValueError, TypeError):
        return None


def distance_tier(miles: float) -> str:
    if miles < 700:
        return "short"
    elif miles < 1800:
        return "medium"
    return "long"


def batch_upsert(supabase: Client, table: str, rows: list[dict],
                 conflict_col: str, batch_size: int = 500) -> int:
    """Upsert rows in batches; returns total inserted/updated count."""
    if not rows:
        return 0
    n = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i: i + batch_size]
        supabase.table(table).upsert(chunk, on_conflict=conflict_col).execute()
        n += len(chunk)
        print(f"    {table}: {min(i + batch_size, len(rows))}/{len(rows)}", end="\r")
    print()
    return n


def batch_insert(supabase: Client, table: str, rows: list[dict],
                 batch_size: int = 500) -> int:
    """Plain insert (no conflict handling) in batches."""
    if not rows:
        return 0
    n = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i: i + batch_size]
        supabase.table(table).insert(chunk).execute()
        n += len(chunk)
        print(f"    {table}: {min(i + batch_size, len(rows))}/{len(rows)}", end="\r")
    print()
    return n


def days_of_week_str(year_col, month_col, day_col) -> str:
    """Given iterables of (year, month, day), return e.g. 'Mon,Wed,Fri'."""
    dow_set: set[int] = set()
    for y, m, d in zip(year_col, month_col, day_col):
        shifted = date(int(y) + YEAR_SHIFT, int(m), int(d))
        dow_set.add(shifted.weekday())  # 0=Mon … 6=Sun
    return ",".join(DOW_NAMES[i] for i in sorted(dow_set))


# ──────────────────────────────────────────────
# ETL phases
# ──────────────────────────────────────────────

def phase_a_airlines(df: pd.DataFrame, supabase: Client) -> dict[str, str]:
    """Insert CSV carriers into AIRLINE. Returns iata_code → airline_id map."""
    print("\n[A] Airlines...")
    rows = []
    for carrier in df["carrier"].dropna().unique():
        name, country = CARRIER_INFO.get(carrier, (f"{carrier} Airlines", "United States"))
        rows.append({"iata_code": carrier, "name": name, "country": country})
    batch_upsert(supabase, "AIRLINE", rows, conflict_col="iata_code")
    result = supabase.table("AIRLINE").select("airline_id,iata_code").execute()
    mapping = {r["iata_code"]: r["airline_id"] for r in result.data}
    print(f"  → {len(mapping)} airlines in DB")
    return mapping


def phase_b_airports(df: pd.DataFrame, supabase: Client) -> None:
    """Insert all origin + destination airports into AIRPORT."""
    print("\n[B] Airports...")
    codes: set[str] = set(df["origin"].dropna().unique()) | set(df["dest"].dropna().unique())
    rows = []
    for code in codes:
        if code in AIRPORT_INFO:
            name, city, country = AIRPORT_INFO[code]
        else:
            name, city, country = f"{code} Airport", code, "United States"
        rows.append({"iata_code": code, "name": name, "city": city, "country": country})
    batch_upsert(supabase, "AIRPORT", rows, conflict_col="iata_code")
    result = supabase.table("AIRPORT").select("iata_code", count="exact").execute()
    print(f"  → {result.count} airports in DB")


def phase_c_aircraft(df: pd.DataFrame, supabase: Client,
                     airline_ids: dict[str, str]) -> dict[tuple, str]:
    """
    Create distance-tiered aircraft per carrier (≤3 per carrier).
    Returns (carrier_iata, tier) → aircraft_id map.
    """
    print("\n[C] Aircraft...")
    # Determine which tiers each carrier actually uses
    carrier_tiers: dict[str, set[str]] = {}
    for (carrier, origin, dest), grp in df.groupby(["carrier", "origin", "dest"]):
        dist = grp["distance"].median()
        tier = distance_tier(dist)
        carrier_tiers.setdefault(carrier, set()).add(tier)

    # Fetch existing aircraft to avoid duplicates
    existing = supabase.table("AIRCRAFT").select("aircraft_id,airline_id,model").execute()
    existing_set: set[tuple] = {(r["airline_id"], r["model"]) for r in existing.data}

    to_insert: list[dict] = []
    for carrier, tiers in carrier_tiers.items():
        airline_id = airline_ids.get(carrier)
        if not airline_id:
            continue
        carrier_type = "regional" if carrier in REGIONAL_CARRIERS else "mainline"
        for tier in tiers:
            model = TIER_MODELS[carrier_type][tier]
            if (airline_id, model) not in existing_set:
                to_insert.append({"airline_id": airline_id, "model": model})
                existing_set.add((airline_id, model))

    if to_insert:
        batch_insert(supabase, "AIRCRAFT", to_insert)

    # Build (carrier, tier) → aircraft_id map
    all_ac = supabase.table("AIRCRAFT").select("aircraft_id,airline_id,model").execute()
    # airline_id → carrier reverse map
    id_to_carrier = {v: k for k, v in airline_ids.items()}
    ac_map: dict[tuple, str] = {}
    for r in all_ac.data:
        carrier = id_to_carrier.get(r["airline_id"])
        if not carrier:
            continue
        carrier_type = "regional" if carrier in REGIONAL_CARRIERS else "mainline"
        for tier, model in TIER_MODELS[carrier_type].items():
            if r["model"] == model:
                ac_map[(carrier, tier)] = r["aircraft_id"]

    print(f"  → {len(ac_map)} (carrier, tier) aircraft mappings")
    return ac_map


def phase_d_seat_classes(supabase: Client, ac_map: dict[tuple, str]) -> None:
    """Insert SEAT_CLASS rows. Trigger auto-generates SEAT_INVENTORY."""
    print("\n[D] Seat classes (trigger will auto-generate SEAT_INVENTORY)...")
    # Fetch existing to avoid re-triggering
    existing = supabase.table("SEAT_CLASS").select("class_id,aircraft_id,class_name").execute()
    existing_set: set[tuple] = {(r["aircraft_id"], r["class_name"]) for r in existing.data}

    rows: list[dict] = []
    seen_aircraft: set[str] = set()
    for (carrier, tier), ac_id in ac_map.items():
        if ac_id in seen_aircraft:
            continue
        seen_aircraft.add(ac_id)
        for class_name in ["First", "Business", "Economy"]:
            if (ac_id, class_name) in existing_set:
                continue
            rows.append({
                "aircraft_id": ac_id,
                "class_name":  class_name,
                "seat_count":  TIER_SEATS[tier][class_name],
                "price":       TIER_PRICES[tier][class_name],
            })

    # Insert one row at a time so the trigger fires reliably for each
    inserted = 0
    for row in rows:
        supabase.table("SEAT_CLASS").insert(row).execute()
        inserted += 1
        if inserted % 10 == 0:
            print(f"    SEAT_CLASS: {inserted}/{len(rows)}", end="\r")
    print()
    total = supabase.table("SEAT_CLASS").select("class_id", count="exact").execute().count
    inv   = supabase.table("SEAT_INVENTORY").select("seat_id", count="exact").execute().count
    print(f"  → {total} seat classes, {inv} seat inventory rows in DB")


def phase_e_schedules(df: pd.DataFrame, supabase: Client,
                      airline_ids: dict[str, str],
                      ac_map: dict[tuple, str]) -> dict[tuple, dict]:
    """
    Build one FLIGHT_SCHEDULE per distinct (carrier, flight#, origin, dest).
    Returns (flight_number, origin, dest) → {schedule_id, aircraft_id} map.
    """
    print("\n[E] Flight schedules...")
    df_clean = df.dropna(subset=["sched_dep_time", "sched_arr_time"]).copy()
    df_clean["flight_number"] = df_clean["carrier"] + df_clean["flight"].astype(int).astype(str)

    rows: list[dict] = []
    for (fn, origin, dest), grp in df_clean.groupby(["flight_number", "origin", "dest"]):
        carrier = grp["carrier"].iloc[0]
        airline_id = airline_ids.get(carrier)
        if not airline_id:
            continue

        dep_t = parse_hhmm(grp["sched_dep_time"].mode()[0])
        arr_t = parse_hhmm(grp["sched_arr_time"].mode()[0])
        if dep_t is None or arr_t is None:
            continue

        avg_dist = grp["distance"].median()
        tier = distance_tier(avg_dist)
        ac_id = ac_map.get((carrier, tier))
        if not ac_id:
            for fallback in ["medium", "short", "long"]:
                ac_id = ac_map.get((carrier, fallback))
                if ac_id:
                    break
        if not ac_id:
            continue

        dow = days_of_week_str(grp["year"], grp["month"], grp["day"])
        shifted_dates = [date(int(y) + YEAR_SHIFT, int(m), int(d))
                         for y, m, d in zip(grp["year"], grp["month"], grp["day"])]
        valid_from  = min(shifted_dates).isoformat()
        valid_until = max(shifted_dates).isoformat()

        rows.append({
            "aircraft_id":         ac_id,
            "depart_airport_iata": origin,
            "dest_airport_iata":   dest,
            "flight_number":       fn,
            "depart_time":         dep_t.strftime("%H:%M:%S"),
            "arrival_time":        arr_t.strftime("%H:%M:%S"),
            "days_of_week":        dow,
            "valid_from":          valid_from,
            "valid_until":         valid_until,
        })

    # FLIGHT_SCHEDULE has a composite unique on all meaningful fields.
    # Use individual inserts with ignore to avoid the long conflict-col string.
    # Batch them with try/except per chunk.
    inserted = 0
    skipped  = 0
    BATCH = 200
    for i in range(0, len(rows), BATCH):
        chunk = rows[i: i + BATCH]
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
    print(f"  → {inserted} schedules inserted, {skipped} skipped (duplicates)")

    # Fetch all schedules and build lookup map
    all_sched = supabase.table("FLIGHT_SCHEDULE").select(
        "schedule_id,flight_number,depart_airport_iata,dest_airport_iata,aircraft_id"
    ).execute()
    sched_map: dict[tuple, dict] = {}
    for s in all_sched.data:
        key = (s["flight_number"], s["depart_airport_iata"], s["dest_airport_iata"])
        sched_map[key] = {
            "schedule_id": s["schedule_id"],
            "aircraft_id": s["aircraft_id"],
        }
    print(f"  → {len(sched_map)} schedule entries in lookup map")
    return sched_map


def phase_f_flights(df: pd.DataFrame, supabase: Client,
                    sched_map: dict[tuple, dict],
                    limit: int | None, batch_size: int) -> list[str]:
    """
    Insert one FLIGHT row per (schedule, shifted date).
    Returns list of past flight_ids (for use in Phase G).
    """
    print("\n[F] Flights...")
    df_clean = df.dropna(subset=["sched_dep_time", "sched_arr_time"]).copy()
    df_clean["flight_number"] = df_clean["carrier"] + df_clean["flight"].astype(int).astype(str)

    rows: list[dict] = []
    seen: set[tuple] = set()  # (schedule_id, flight_date) dedup

    for _, row in df_clean.iterrows():
        fn     = row["flight_number"]
        origin = row["origin"]
        dest   = row["dest"]
        key    = (fn, origin, dest)
        sched  = sched_map.get(key)
        if not sched:
            continue

        schedule_id = sched["schedule_id"]
        aircraft_id = sched["aircraft_id"]

        shifted = date(int(row["year"]) + YEAR_SHIFT, int(row["month"]), int(row["day"]))
        dedup_key = (schedule_id, shifted.isoformat())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        dep_t = parse_hhmm(row["sched_dep_time"])
        arr_t = parse_hhmm(row["sched_arr_time"])
        if dep_t is None or arr_t is None:
            continue

        dep_dt = datetime.combine(shifted, dep_t)
        arr_dt = datetime.combine(shifted, arr_t)
        if arr_dt <= dep_dt:
            arr_dt += timedelta(days=1)

        rows.append({
            "schedule_id": schedule_id,
            "aircraft_id": aircraft_id,
            "flight_date": shifted.isoformat(),
            "depart_time": dep_dt.isoformat() + "+00:00",
            "arrival_time": arr_dt.isoformat() + "+00:00",
            "status": "scheduled",
        })

        if limit and len(rows) >= limit:
            break

    # Insert in batches (upsert on schedule_id,flight_date to handle reruns)
    total = 0
    BATCH = batch_size
    for i in range(0, len(rows), BATCH):
        chunk = rows[i: i + BATCH]
        try:
            supabase.table("FLIGHT").upsert(
                chunk, on_conflict="schedule_id,flight_date", ignore_duplicates=True
            ).execute()
        except Exception:
            supabase.table("FLIGHT").insert(chunk).execute()
        total += len(chunk)
        print(f"    FLIGHT: {total}/{len(rows)}", end="\r")
    print()
    print(f"  → {total} flights inserted")

    # Return past flight_ids for Phase G
    past_result = (
        supabase.table("FLIGHT")
        .select("flight_id,aircraft_id")
        .lt("flight_date", TODAY.isoformat())
        .eq("status", "scheduled")
        .execute()
    )
    return past_result.data


def phase_g_history(supabase: Client, past_flights: list[dict],
                    n_bookings: int, batch_size: int) -> None:
    """Create historical BOOKING + PAYMENT + TICKET on past-dated flights."""
    print(f"\n[G] Historical bookings (target: {n_bookings})...")
    if not past_flights:
        print("  No past flights found — skipping")
        return

    customers = supabase.table("CUSTOMER").select("customer_id").execute().data
    if not customers:
        print("  No customers found — skipping")
        return
    customer_ids = [c["customer_id"] for c in customers]

    # Build aircraft → list of (seat_id, class_id) map
    aircraft_ids = list({f["aircraft_id"] for f in past_flights})
    seats_by_ac: dict[str, list[dict]] = {}
    for ac_id in aircraft_ids:
        seats = (
            supabase.table("SEAT_INVENTORY")
            .select("seat_id,class_id")
            .eq("aircraft_id", ac_id)
            .execute()
            .data
        )
        seats_by_ac[ac_id] = seats

    # class_id → price
    seat_classes = supabase.table("SEAT_CLASS").select("class_id,price").execute().data
    class_price: dict[str, float] = {sc["class_id"]: float(sc["price"]) for sc in seat_classes}

    booked: set[tuple] = set()  # (flight_id, seat_id)
    booking_rows: list[dict] = []
    payment_rows: list[dict] = []
    ticket_rows:  list[dict] = []

    random.seed(42)
    attempts = 0
    created  = 0

    while created < n_bookings and attempts < n_bookings * 4:
        attempts += 1
        flight = random.choice(past_flights)
        flight_id  = flight["flight_id"]
        aircraft_id = flight["aircraft_id"]

        seats = seats_by_ac.get(aircraft_id, [])
        if not seats:
            continue
        available = [s for s in seats if (flight_id, s["seat_id"]) not in booked]
        if not available:
            continue

        seat     = random.choice(available)
        seat_id  = seat["seat_id"]
        class_id = seat["class_id"]
        price    = class_price.get(class_id, 150.0)

        booking_id = str(uuid.uuid4())
        payment_id = str(uuid.uuid4())
        ticket_id  = str(uuid.uuid4())
        now_str    = datetime.utcnow().isoformat() + "+00:00"

        booked.add((flight_id, seat_id))

        booking_rows.append({
            "booking_id":  booking_id,
            "flight_id":   flight_id,
            "customer_id": random.choice(customer_ids),
            "seat_id":     seat_id,
            "status":      "confirmed",
            "price":       price,
            "booked_at":   now_str,
        })
        payment_rows.append({
            "payment_id": payment_id,
            "booking_id": booking_id,
            "amount":     price,
            "method":     "credit_card",
            "status":     "completed",
            "paid_at":    now_str,
        })
        ticket_rows.append({
            "ticket_id":  ticket_id,
            "booking_id": booking_id,
            "issued_at":  now_str,
        })
        created += 1

    print(f"    Prepared {created} bookings ({attempts} attempts)")
    batch_insert(supabase, "BOOKING", booking_rows, batch_size)
    batch_insert(supabase, "PAYMENT", payment_rows, batch_size)
    batch_insert(supabase, "TICKET",  ticket_rows,  batch_size)
    print(f"  → {created} historical bookings created")


def phase_h_flip_status(supabase: Client, past_flights: list[dict],
                        batch_size: int) -> None:
    """Flip past flights (flight_date < TODAY) from scheduled → arrived."""
    print("\n[H] Flipping past flights to arrived...")
    past_ids = [f["flight_id"] for f in past_flights]
    if not past_ids:
        print("  Nothing to flip")
        return

    flipped = 0
    for i in range(0, len(past_ids), batch_size):
        chunk = past_ids[i: i + batch_size]
        supabase.table("FLIGHT").update({"status": "arrived"}).in_(
            "flight_id", chunk
        ).execute()
        flipped += len(chunk)
        print(f"    Flipped: {flipped}/{len(past_ids)}", end="\r")
    print()
    print(f"  → {flipped} flights marked as arrived")


# ──────────────────────────────────────────────
# Truncate helper
# ──────────────────────────────────────────────

def truncate_flight_data(supabase: Client) -> None:
    """Delete all bookings and flights (keeps accounts, schedules, aircraft, airports)."""
    print("Truncating BOOKING and FLIGHT data...")
    # Delete bookings first (FK chain: TICKET, PAYMENT, REFUND cascade)
    try:
        supabase.table("TICKET").delete().gt("issued_at", "1970-01-01T00:00:00+00:00").execute()
        supabase.table("REFUND").delete().gt("refunded_at", "1970-01-01T00:00:00+00:00").execute()
        supabase.table("PAYMENT").delete().gt("paid_at", "1970-01-01T00:00:00+00:00").execute()
        supabase.table("BOOKING").delete().gt("booked_at", "1970-01-01T00:00:00+00:00").execute()
    except Exception as e:
        print(f"  Note during booking clear: {e}")
    try:
        supabase.table("FLIGHT").delete().gt("flight_date", "1900-01-01").execute()
    except Exception as e:
        print(f"  Note during flight clear: {e}")
    print("  Done.")


# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

def print_summary(supabase: Client) -> None:
    tables = [
        "AIRLINE", "AIRPORT", "AIRCRAFT", "SEAT_CLASS", "SEAT_INVENTORY",
        "FLIGHT_SCHEDULE", "FLIGHT", "BOOKING", "PAYMENT", "TICKET",
    ]
    print("\n──────────────────────────────────────")
    print("Final row counts:")
    for t in tables:
        try:
            r = supabase.table(t).select("*", count="exact", head=True).execute()
            print(f"  {t:<20} {r.count:>8}")
        except Exception as e:
            print(f"  {t:<20}   (error: {e})")
    print("──────────────────────────────────────")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed AirBooking Supabase from nycflights13 flights.csv"
    )
    parser.add_argument("--with-flights",  action="store_true",
                        help="Also run phases E–H (schedules, flights, history, status flip). "
                             "Default: only phases A–D (master data)")
    parser.add_argument("--limit",        type=int, default=None,
                        help="Cap total FLIGHT rows (useful for smoke tests; requires --with-flights)")
    parser.add_argument("--with-history", type=int, default=0, metavar="N",
                        help="Create N historical bookings on past-dated flights (requires --with-flights)")
    parser.add_argument("--batch",        type=int, default=500,
                        help="Insert batch size (default 500)")
    parser.add_argument("--truncate",     action="store_true",
                        help="Clear FLIGHT+BOOKING data before loading (requires --with-flights)")
    args = parser.parse_args()

    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    supabase: Client = create_client(url, key)

    print(f"Loading {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    print(f"  {len(df):,} rows loaded")

    if args.truncate and args.with_flights:
        truncate_flight_data(supabase)
    elif args.truncate:
        print("Note: --truncate has no effect without --with-flights (no flights to truncate).")

    # Phases A–D: master data (always run)
    airline_ids = phase_a_airlines(df, supabase)
    phase_b_airports(df, supabase)
    ac_map       = phase_c_aircraft(df, supabase, airline_ids)
    phase_d_seat_classes(supabase, ac_map)

    if args.with_flights:
        # Phases E–H: schedules and flights (opt-in)
        sched_map    = phase_e_schedules(df, supabase, airline_ids, ac_map)
        past_flights = phase_f_flights(df, supabase, sched_map, args.limit, args.batch)

        if args.with_history > 0:
            phase_g_history(supabase, past_flights, args.with_history, args.batch)

        phase_h_flip_status(supabase, past_flights, args.batch)
    else:
        print("\n[E–H skipped] Master data only. Use --with-flights to also load schedules & flights.")
        print("  Demo schedules and flights are seeded by 03_seed_sample_data.sql.")

    print_summary(supabase)
    print("\nDone. Run `streamlit run app.py` to launch the app.")


if __name__ == "__main__":
    main()
