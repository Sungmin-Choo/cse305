import os
import random
import uuid
from datetime import date, datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

TODAY = date.today()
random.seed(42)

POPULAR_ROUTES = {
    ("ICN", "JFK"): 1.8,
    ("ICN", "LAX"): 1.7,
    ("JFK", "LHR"): 1.5,
    ("LAX", "NRT"): 1.4,
}

MONTH_FACTOR = {
    1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.1,
    7: 1.4, 8: 1.5, 9: 1.0, 10: 1.0, 11: 1.1, 12: 1.6
}

CLASS_BASE = {
    "Economy": 0.75,
    "Business": 0.35,
    "First": 0.12,
}

BATCH_SIZE = 500


def route_weight(dep: str, dest: str) -> float:
    return POPULAR_ROUTES.get((dep, dest), 1.0)


def date_weight(flight_date_str: str) -> float:
    d = datetime.fromisoformat(flight_date_str).date()
    w = MONTH_FACTOR.get(d.month, 1.0)
    if d.weekday() in [4, 5, 6]:  # Fri, Sat, Sun
        w *= 1.1
    return w


def batch_insert(table_name: str, rows: list[dict], batch_size: int = BATCH_SIZE) -> int:
    if not rows:
        return 0

    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        supabase.table(table_name).insert(chunk).execute()
        total += len(chunk)
        print(f"{table_name}: {total}/{len(rows)}", end="\r")
    print()
    return total


def main():
    print("Loading reference data...")

    customers = supabase.table("CUSTOMER").select("customer_id").execute().data
    customer_ids = [c["customer_id"] for c in customers]

    if not customer_ids:
        print("No customers found.")
        return

    flights = supabase.table("FLIGHT") \
        .select("flight_id, aircraft_id, flight_date, FLIGHT_SCHEDULE!inner(depart_airport_iata, dest_airport_iata)") \
        .lt("flight_date", TODAY.isoformat()) \
        .eq("status", "scheduled") \
        .execute().data

    if not flights:
        print("No past scheduled flights found.")
        return

    seat_classes = supabase.table("SEAT_CLASS") \
        .select("class_id, aircraft_id, class_name, price") \
        .execute().data

    seat_inventory = supabase.table("SEAT_INVENTORY") \
        .select("seat_id, aircraft_id, class_id") \
        .execute().data

    existing_bookings = supabase.table("BOOKING") \
        .select("flight_id, seat_id") \
        .eq("status", "confirmed") \
        .execute().data

    already_booked = {(b["flight_id"], b["seat_id"]) for b in existing_bookings}

    seats_by_aircraft_class = {}
    for s in seat_inventory:
        key = (s["aircraft_id"], s["class_id"])
        seats_by_aircraft_class.setdefault(key, []).append(s["seat_id"])

    class_meta = {}
    for sc in seat_classes:
        class_meta[(sc["aircraft_id"], sc["class_name"])] = sc

    booking_rows = []
    payment_rows = []
    ticket_rows = []

    inserted = 0

    print("Generating synthetic bookings in memory...")

    for idx, flight in enumerate(flights, start=1):
        flight_id = flight["flight_id"]
        aircraft_id = flight["aircraft_id"]
        flight_date = flight["flight_date"]
        dep = flight["FLIGHT_SCHEDULE"]["depart_airport_iata"]
        dest = flight["FLIGHT_SCHEDULE"]["dest_airport_iata"]

        rw = route_weight(dep, dest)
        dw = date_weight(flight_date)

        for class_name in ["Economy", "Business", "First"]:
            meta = class_meta.get((aircraft_id, class_name))
            if not meta:
                continue

            class_id = meta["class_id"]
            base_price = float(meta["price"])
            seat_ids = seats_by_aircraft_class.get((aircraft_id, class_id), [])

            if not seat_ids:
                continue

            available_seat_ids = [
                sid for sid in seat_ids
                if (flight_id, sid) not in already_booked
            ]

            if not available_seat_ids:
                continue

            demand = CLASS_BASE[class_name] * rw * dw
            demand = min(demand, 0.95)

            target_count = max(0, int(len(available_seat_ids) * demand))
            target_count = min(target_count, len(available_seat_ids))

            if target_count == 0:
                continue

            chosen_seats = random.sample(available_seat_ids, target_count)

            for seat_id in chosen_seats:
                booking_id = str(uuid.uuid4())
                payment_id = str(uuid.uuid4())
                ticket_id = str(uuid.uuid4())
                customer_id = random.choice(customer_ids)
                now_str = datetime.utcnow().isoformat() + "+00:00"

                booking_rows.append({
                    "booking_id": booking_id,
                    "flight_id": flight_id,
                    "customer_id": customer_id,
                    "seat_id": seat_id,
                    "status": "confirmed",
                    "price": base_price,
                    "booked_at": now_str,
                })

                payment_rows.append({
                    "payment_id": payment_id,
                    "booking_id": booking_id,
                    "amount": base_price,
                    "method": "credit_card",
                    "status": "completed",
                    "paid_at": now_str,
                })

                ticket_rows.append({
                    "ticket_id": ticket_id,
                    "booking_id": booking_id,
                    "issued_at": now_str,
                })

                already_booked.add((flight_id, seat_id))
                inserted += 1

        if idx % 50 == 0:
            print(f"Processed flights: {idx}/{len(flights)} | prepared bookings: {inserted}")

    print(f"\nPrepared {len(booking_rows)} bookings")
    print("Sending batch inserts to Supabase...")

    batch_insert("BOOKING", booking_rows)
    batch_insert("PAYMENT", payment_rows)
    batch_insert("TICKET", ticket_rows)

    print(f"\nDone. Inserted {inserted} synthetic bookings.")


if __name__ == "__main__":
    main()