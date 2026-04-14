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

st.set_page_config(page_title="CSE 305: FRS Project", layout="wide")
st.title("Airline Reservation System")
st.info("CSE 305 Term Project - Core Operations Dashboard")


def rpc_error_message(data):
    if isinstance(data, str):
        lowered = data.lower()
        if "error" in lowered or "exception" in lowered or "failed" in lowered:
            return data
    return None


with st.expander("0. [STAFF] Create Flight Schedule", expanded=False):
    st.write("Define a recurring flight schedule with aircraft assignment.")

    try:
        airlines = supabase.table("AIRLINE").select("airline_id, name").execute().data
        aircrafts = supabase.table("AIRCRAFT").select("aircraft_id, model").execute().data
        airports = supabase.table("AIRPORT").select("iata_code, city").execute().data
    except Exception as e:
        st.error(f"Error loading master data: {str(e)}")
        airlines, aircrafts, airports = [], [], []

    airline_options = {a["name"]: a["airline_id"] for a in airlines}
    aircraft_options = {a["model"]: a["aircraft_id"] for a in aircrafts}
    airport_options = {f"{a['iata_code']} - {a['city']}": a["iata_code"] for a in airports}

    if not airline_options or not aircraft_options or not airport_options:
        st.warning("Missing airline/aircraft/airport master data. Please seed required data first.")
    else:
        selected_airline = st.selectbox("Airline", list(airline_options.keys()), key="sch_airline")
        selected_aircraft = st.selectbox("Aircraft", list(aircraft_options.keys()), key="sch_aircraft")

        col1, col2 = st.columns(2)
        with col1:
            dep_label = st.selectbox("Departure Airport", list(airport_options.keys()), key="sch_dep")
        with col2:
            arr_label = st.selectbox("Arrival Airport", list(airport_options.keys()), key="sch_arr")

        flight_number = st.text_input("Flight Number (e.g. KE001)", key="sch_fn")

        col3, col4 = st.columns(2)
        with col3:
            depart_time = st.time_input("Departure Time", key="sch_dep_time")
        with col4:
            arrival_time = st.time_input("Arrival Time", key="sch_arr_time")

        days_of_week = st.multiselect(
            "Days of Week",
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            key="sch_days",
        )

        col5, col6 = st.columns(2)
        with col5:
            valid_from = st.date_input("Valid From", key="sch_vfrom")
        with col6:
            valid_until = st.date_input("Valid Until", key="sch_vuntil")

        if st.button("Create Schedule", key="btn_create_schedule"):
            dep_iata = airport_options[dep_label]
            arr_iata = airport_options[arr_label]
            if dep_iata == arr_iata:
                st.error("Departure and arrival airports must be different.")
            elif not days_of_week:
                st.error("Select at least one day of week.")
            elif not flight_number.strip():
                st.error("Flight number is required.")
            elif valid_from > valid_until:
                st.error("Valid From must be earlier than or equal to Valid Until.")
            else:
                try:
                    supabase.table("FLIGHT_SCHEDULE").insert(
                        {
                            "airline_id": airline_options[selected_airline],
                            "aircraft_id": aircraft_options[selected_aircraft],
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
                    st.success("Schedule created successfully.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


with st.expander("1. [STAFF] Generate Flights from Schedule", expanded=False):
    st.write("Generate individual flight records based on recurring schedules.")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today(), key="gen_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="gen_end")

    if st.button("Execute Generation", key="btn_generate"):
        try:
            response = supabase.rpc(
                "generate_flights",
                {"p_start_date": str(start_date), "p_end_date": str(end_date)},
            ).execute()
            error_msg = rpc_error_message(response.data)
            if error_msg:
                st.error(error_msg)
            else:
                st.success(str(response.data))
        except Exception as e:
            st.error(f"Error: {str(e)}")


with st.expander("2. [CUSTOMER] Flight Search", expanded=False):
    st.write("Search for available flights by route, date, and optional seat class.")

    col1, col2 = st.columns(2)
    with col1:
        dep_iata = st.text_input("Departure Airport (IATA)", placeholder="e.g. ICN", key="srch_dep").upper()
    with col2:
        arr_iata = st.text_input("Arrival Airport (IATA)", placeholder="e.g. NRT", key="srch_arr").upper()

    col3, col4 = st.columns(2)
    with col3:
        travel_date = st.date_input("Travel Date", value=date.today(), key="srch_date")
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
                        st.info("No available flights found for the selected criteria.")
                    else:
                        df = pd.DataFrame(results).rename(
                            columns={
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
                                    "Flight",
                                    "Airline",
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


with st.expander("3. [CUSTOMER] Create Booking", expanded=False):
    st.write("Select a flight and seat to create a booking.")

    flight_id_input = st.text_input("Flight ID (UUID)", key="bk_flight_id").strip()
    class_choice = st.selectbox("Seat Class", ["Economy", "Business", "First"], key="bk_class")
    default_customer_id = st.session_state.get("customer_id", "")
    customer_id_input = st.text_input(
        "Customer ID (UUID)", value=default_customer_id, key="bk_customer_id"
    ).strip()

    available_seats = []
    base_price = None

    if flight_id_input:
        try:
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
                    seat_data = (
                        supabase.table("SEAT_INVENTORY")
                        .select("seat_id, seat_number")
                        .eq("class_id", class_id)
                        .execute()
                        .data
                    )
                    booked_data = (
                        supabase.table("BOOKING")
                        .select("seat_id")
                        .eq("flight_id", flight_id_input)
                        .eq("status", "confirmed")
                        .execute()
                        .data
                    )
                    booked_ids = {b["seat_id"] for b in booked_data}
                    available_seats = [s for s in seat_data if s["seat_id"] not in booked_ids]
        except Exception as e:
            st.warning(f"Could not load seats: {str(e)}")

    if available_seats and base_price is not None:
        seat_options = {s["seat_number"]: s["seat_id"] for s in available_seats}
        selected_seat_num = st.selectbox("Select Seat", list(seat_options.keys()), key="bk_seat")
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


with st.expander("4. [CUSTOMER] Cancel Booking and Refund", expanded=False):
    st.write("View your active bookings and cancel one.")

    cancel_default_customer_id = st.session_state.get("customer_id", "")
    customer_id_cancel = st.text_input(
        "Customer ID (UUID)", value=cancel_default_customer_id, key="cancel_customer_id"
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
        preferred_cols = [
            "booking_id",
            "flight_number",
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
        selected_booking = st.selectbox("Select Booking to Cancel", booking_ids, key="cancel_select")

        if st.button("Cancel Booking", key="btn_cancel"):
            try:
                response = supabase.rpc("cancel_booking", {"p_booking_id": selected_booking}).execute()
                error_msg = rpc_error_message(response.data)
                if error_msg:
                    st.error(error_msg)
                else:
                    st.success(str(response.data))
                    st.session_state.pop("active_bookings", None)
            except Exception as e:
                st.error(f"Error: {str(e)}")


with st.expander("5. [STAFF] Revenue Statistics", expanded=False):
    st.write("View revenue breakdown by route, class, and time period.")

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
                    df["revenue_month"] = pd.to_datetime(df["revenue_month"]).dt.strftime("%Y-%m")
                    df["revenue_quarter"] = (
                        pd.to_datetime(df["revenue_quarter"]).dt.to_period("Q").astype(str)
                    )

                    st.subheader("Revenue by Flight and Class")
                    st.dataframe(
                        df[
                            [
                                "flight_number",
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
                    monthly = df.groupby("revenue_month")["total_revenue"].sum().reset_index()
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
