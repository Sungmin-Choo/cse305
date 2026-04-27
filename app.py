import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(URL, KEY)

st.set_page_config(page_title="CSE 305: ARS Project", layout="wide")
st.title("✈️ Airline Reservation System")
st.info("CSE 305 Term Project — Core Operations Dashboard (Physical Asset Model)")


def rpc_error_message(data):
    """Check if an RPC response contains an error string instead of real data."""
    if isinstance(data, str):
        lowered = data.lower()
        if "error" in lowered or "exception" in lowered or "failed" in lowered:
            return data
    return None


def build_route_display(dep, dest, stopover_list):
    """Build a human-readable route string including stopovers.
    Example: ICN → DXB → LHR
    """
    if stopover_list:
        stops = stopover_list.split(",")
        return " → ".join([dep] + stops + [dest])
    return f"{dep} → {dest}"


# =============================================================
# Section 1: [STAFF] Generate Flights from Schedule
# =============================================================
# Unified workflow: define a recurring schedule and generate
# individual flight records in one step.
# Airline is auto-derived from the selected aircraft's ownership.
# =============================================================
with st.expander("1. [STAFF] Generate Flights from Schedule", expanded=False):
    st.write(
        "Define a recurring flight schedule and generate individual flight records. "
        "Each generated flight is associated with the schedule and ready for booking."
    )

    try:
        # Load aircraft with airline info (Aircraft → Airline ownership)
        aircrafts = (
            supabase.table("AIRCRAFT")
            .select("aircraft_id, model, airline_id, AIRLINE(name)")
            .execute()
            .data
        )
        airports = supabase.table("AIRPORT").select("iata_code, city").execute().data
    except Exception as e:
        st.error(f"Error loading master data: {str(e)}")
        aircrafts, airports = [], []

    # Build aircraft options showing "Airline — Model" for clarity
    aircraft_options = {}
    for ac in aircrafts:
        airline_name = ac.get("AIRLINE", {}).get("name", "Unknown")
        label = f"{airline_name} — {ac['model']}"
        aircraft_options[label] = ac["aircraft_id"]

    airport_options = {
        f"{a['iata_code']} - {a['city']}": a["iata_code"] for a in airports
    }

    if not aircraft_options or not airport_options:
        st.warning(
            "Missing aircraft/airport master data. Please seed required data first."
        )
    else:
        # --- Aircraft & Route ---
        st.subheader("Aircraft & Route")
        selected_aircraft_label = st.selectbox(
            "Aircraft (airline auto-derived from ownership)",
            list(aircraft_options.keys()),
            key="gen_aircraft",
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            dep_label = st.selectbox(
                "Departure Airport", list(airport_options.keys()), key="gen_dep"
            )
        with col_r2:
            arr_label = st.selectbox(
                "Arrival Airport", list(airport_options.keys()), key="gen_arr"
            )

        flight_number = st.text_input("Flight Number (e.g. KE001)", key="gen_fn")

        # --- Departure / Arrival Times ---
        st.subheader("Departure & Arrival Times")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            depart_time = st.time_input("Departure Time", key="gen_dep_time")
        with col_t2:
            arrival_time = st.time_input("Arrival Time", key="gen_arr_time")

        # --- Operating Days ---
        st.subheader("Operating Days")
        days_of_week = st.multiselect(
            "Days of week this flight operates",
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            key="gen_days",
        )

        # --- Schedule Validity & Generation Range ---
        st.subheader("Schedule Validity Period")
        st.caption(
            "The schedule is valid during this date range. "
            "Individual flights will be generated for matching dates within this period."
        )
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            valid_from = st.date_input(
                "Valid From", value=date.today(), key="gen_valid_from"
            )
        with col_d2:
            valid_until = st.date_input(
                "Valid Until", value=date.today(), key="gen_valid_until"
            )

        st.subheader("Flight Generation Date Range")
        st.caption(
            "Choose the date range for which to generate individual flight records. "
            "Flights are only created for dates that fall within the validity period above."
        )
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            gen_start = st.date_input(
                "Generation Start Date", value=date.today(), key="gen_start"
            )
        with col_g2:
            gen_end = st.date_input(
                "Generation End Date", value=date.today(), key="gen_end"
            )

        st.divider()

        if st.button("Create Schedule & Generate Flights", key="btn_generate"):
            dep_iata = airport_options[dep_label]
            arr_iata = airport_options[arr_label]

            # --- Validation ---
            if dep_iata == arr_iata:
                st.error("Departure and arrival airports must be different.")
            elif not days_of_week:
                st.error("Select at least one operating day.")
            elif not flight_number.strip():
                st.error("Flight number is required.")
            elif valid_from > valid_until:
                st.error("Valid From must be earlier than or equal to Valid Until.")
            elif gen_start > gen_end:
                st.error("Generation Start must be earlier than or equal to Generation End.")
            else:
                try:
                    # Step 1: Create the recurring schedule
                    supabase.table("FLIGHT_SCHEDULE").insert(
                        {
                            "aircraft_id": aircraft_options[selected_aircraft_label],
                            "depart_airport_iata": dep_iata,
                            "dest_airport_iata": arr_iata,
                            "flight_number": flight_number.strip(),
                            "depart_time": str(depart_time),
                            "arrival_time": str(arrival_time),
                            "days_of_week": ",".join(days_of_week),
                            "valid_from": str(valid_from),
                            "valid_until": str(valid_until),
                        }
                    ).execute()
                    st.success("✅ Schedule created successfully.")

                    # Step 2: Generate individual flights for the date range
                    response = supabase.rpc(
                        "generate_flights",
                        {
                            "p_start_date": str(gen_start),
                            "p_end_date": str(gen_end),
                        },
                    ).execute()
                    error_msg = rpc_error_message(response.data)
                    if error_msg:
                        st.error(error_msg)
                    else:
                        st.success(f"✅ {response.data}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# =============================================================
# Section 2: [CUSTOMER] Flight Search
# =============================================================
# search_flights now returns stopover_list for route display.
# Route is shown as: Departure → Stopovers → Destination
# =============================================================
with st.expander("2. [CUSTOMER] Flight Search", expanded=False):
    st.write("Search for available flights by route, date, and optional seat class.")

    col1, col2 = st.columns(2)
    with col1:
        dep_iata = st.text_input(
            "Departure Airport (IATA)", placeholder="e.g. ICN", key="srch_dep"
        ).upper()
    with col2:
        arr_iata = st.text_input(
            "Arrival Airport (IATA)", placeholder="e.g. LHR", key="srch_arr"
        ).upper()

    col3, col4 = st.columns(2)
    with col3:
        travel_date = st.date_input(
            "Travel Date", value=date.today(), key="srch_date"
        )
    with col4:
        class_filter = st.selectbox(
            "Seat Class (optional)",
            ["All", "First", "Business", "Economy"],
            key="srch_class",
        )

    if st.button("Search Flights", key="btn_search"):
        if not dep_iata or not arr_iata:
            st.error("Both departure and arrival IATA codes are required.")
        else:
            try:
                params = {
                    "p_dep_iata": dep_iata,
                    "p_arr_iata": arr_iata,
                    "p_travel_date": str(travel_date),
                    "p_class_name": None if class_filter == "All" else class_filter,
                }
                response = supabase.rpc("search_flights", params).execute()
                error_msg = rpc_error_message(response.data)
                if error_msg:
                    st.error(error_msg)
                else:
                    results = response.data
                    if not results:
                        st.info(
                            "No available flights found for the selected criteria."
                        )
                    else:
                        df = pd.DataFrame(results)

                        # Build Route column: Departure → Stopovers → Destination
                        df["Route"] = df.apply(
                            lambda row: build_route_display(
                                dep_iata, arr_iata, row.get("stopover_list")
                            ),
                            axis=1,
                        )

                        df = df.rename(
                            columns={
                                "flight_id": "Flight ID",
                                "flight_number": "Flight",
                                "airline_name": "Airline",
                                "depart_time": "Departure",
                                "arrival_time": "Arrival",
                                "class_name": "Class",
                                "price": "Price (USD)",
                                "available_seats": "Available Seats",
                            }
                        )
                        st.dataframe(
                            df[
                                [
                                    "Flight ID",
                                    "Flight",
                                    "Airline",
                                    "Route",
                                    "Departure",
                                    "Arrival",
                                    "Class",
                                    "Price (USD)",
                                    "Available Seats",
                                ]
                            ],
                            use_container_width=True,
                        )
            except Exception as e:
                st.error(f"Error: {str(e)}")


# =============================================================
# Section 3: [CUSTOMER] Create Booking
# =============================================================
with st.expander("3. [CUSTOMER] Create Booking", expanded=False):
    st.write("Select a flight and seat to create a booking.")

    flight_id_input = st.text_input("Flight ID (UUID)", key="bk_flight_id").strip()
    class_choice = st.selectbox(
        "Seat Class", ["Economy", "Business", "First"], key="bk_class"
    )
    default_customer_id = st.session_state.get("customer_id", "")
    customer_id_input = st.text_input(
        "Customer ID (UUID)", value=default_customer_id, key="bk_customer_id"
    ).strip()

    available_seats = []
    base_price = None

    if flight_id_input:
        try:
            # Look up the flight's aircraft
            flight_data = (
                supabase.table("FLIGHT")
                .select("aircraft_id")
                .eq("flight_id", flight_id_input)
                .limit(1)
                .execute()
                .data
            )
            if flight_data:
                aircraft_id = flight_data[0]["aircraft_id"]
                # Look up seat class and price for this aircraft
                class_data = (
                    supabase.table("SEAT_CLASS")
                    .select("class_id, price")
                    .eq("aircraft_id", aircraft_id)
                    .eq("class_name", class_choice)
                    .limit(1)
                    .execute()
                    .data
                )
                if class_data:
                    class_id = class_data[0]["class_id"]
                    base_price = class_data[0]["price"]
                    # Get all seats in this class
                    seat_data = (
                        supabase.table("SEAT_INVENTORY")
                        .select("seat_id, seat_number")
                        .eq("class_id", class_id)
                        .execute()
                        .data
                    )
                    # Filter out already-booked seats
                    booked_data = (
                        supabase.table("BOOKING")
                        .select("seat_id")
                        .eq("flight_id", flight_id_input)
                        .eq("status", "confirmed")
                        .execute()
                        .data
                    )
                    booked_ids = {b["seat_id"] for b in booked_data}
                    available_seats = [
                        s for s in seat_data if s["seat_id"] not in booked_ids
                    ]
        except Exception as e:
            st.warning(f"Could not load seats: {str(e)}")

    if available_seats and base_price is not None:
        seat_options = {s["seat_number"]: s["seat_id"] for s in available_seats}
        selected_seat_num = st.selectbox(
            "Select Seat", list(seat_options.keys()), key="bk_seat"
        )
        selected_seat_id = seat_options[selected_seat_num]
        st.info(f"Price: USD {base_price}")

        if st.button("Confirm Booking", key="btn_book"):
            if not customer_id_input:
                st.error("Customer ID is required.")
            else:
                try:
                    response = supabase.rpc(
                        "create_booking",
                        {
                            "p_customer_id": customer_id_input,
                            "p_flight_id": flight_id_input,
                            "p_seat_id": selected_seat_id,
                            "p_amount": float(base_price),
                        },
                    ).execute()
                    error_msg = rpc_error_message(response.data)
                    if error_msg:
                        st.error(error_msg)
                    else:
                        st.success(f"Booking created. Booking ID: {response.data}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    elif flight_id_input:
        st.warning("No available seats for the selected flight and class.")


# =============================================================
# Section 4: [CUSTOMER] Cancel Booking and Refund
# =============================================================
with st.expander("4. [CUSTOMER] Cancel Booking and Refund", expanded=False):
    st.write("View your active bookings and cancel one.")

    cancel_default_customer_id = st.session_state.get("customer_id", "")
    customer_id_cancel = st.text_input(
        "Customer ID (UUID)",
        value=cancel_default_customer_id,
        key="cancel_customer_id",
    ).strip()

    if st.button("Load My Bookings", key="btn_load_bookings"):
        if not customer_id_cancel:
            st.error("Customer ID is required.")
        else:
            try:
                bookings = (
                    supabase.table("BOOKING_VIEW")
                    .select("*")
                    .eq("customer_id", customer_id_cancel)
                    .eq("status", "confirmed")
                    .execute()
                    .data
                )
                st.session_state["active_bookings"] = bookings
                if not bookings:
                    st.info("No active bookings found.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

    if "active_bookings" in st.session_state and st.session_state["active_bookings"]:
        bookings = st.session_state["active_bookings"]
        df = pd.DataFrame(bookings)
        # Display columns including airline_name from the updated BOOKING_VIEW
        preferred_cols = [
            "booking_id",
            "flight_number",
            "airline_name",
            "flight_date",
            "depart_airport_iata",
            "dest_airport_iata",
            "seat_number",
            "class_name",
            "price",
            "ticket_no",
        ]
        display_cols = [c for c in preferred_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

        booking_ids = [b["booking_id"] for b in bookings]
        selected_booking = st.selectbox(
            "Select Booking to Cancel", booking_ids, key="cancel_select"
        )

        if st.button("Cancel Booking", key="btn_cancel"):
            try:
                response = supabase.rpc(
                    "cancel_booking", {"p_booking_id": selected_booking}
                ).execute()
                error_msg = rpc_error_message(response.data)
                if error_msg:
                    st.error(error_msg)
                else:
                    st.success(str(response.data))
                    st.session_state.pop("active_bookings", None)
            except Exception as e:
                st.error(f"Error: {str(e)}")


# =============================================================
# Section 5: [STAFF] Revenue Statistics
# =============================================================
with st.expander("5. [STAFF] Revenue Statistics", expanded=False):
    st.write("View revenue breakdown by airline, route, class, and time period.")

    if st.button("Generate Revenue Report", key="btn_revenue"):
        try:
            response = supabase.rpc("get_revenue_report", {}).execute()
            error_msg = rpc_error_message(response.data)
            if error_msg:
                st.error(error_msg)
            else:
                results = response.data
                if not results:
                    st.info("No revenue data available.")
                else:
                    df = pd.DataFrame(results)
                    df["revenue_month"] = pd.to_datetime(
                        df["revenue_month"]
                    ).dt.strftime("%Y-%m")
                    df["revenue_quarter"] = (
                        pd.to_datetime(df["revenue_quarter"])
                        .dt.to_period("Q")
                        .astype(str)
                    )

                    st.subheader("Revenue by Flight and Class")
                    st.dataframe(
                        df[
                            [
                                "flight_number",
                                "airline_name",
                                "route",
                                "flight_date",
                                "class_name",
                                "total_revenue",
                                "class_revenue_pct",
                                "load_factor_percentage",
                            ]
                        ],
                        use_container_width=True,
                    )

                    st.subheader("Revenue by Month")
                    monthly = (
                        df.groupby("revenue_month")["total_revenue"]
                        .sum()
                        .reset_index()
                    )
                    st.bar_chart(monthly.set_index("revenue_month"))

                    st.subheader("Revenue by Route")
                    route_rev = (
                        df.groupby("route")["total_revenue"]
                        .sum()
                        .sort_values(ascending=False)
                        .reset_index()
                    )
                    st.bar_chart(route_rev.set_index("route"))
        except Exception as e:
            st.error(f"Error: {str(e)}")
