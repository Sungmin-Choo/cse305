import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

st.set_page_config(page_title="AirBooking — CSE 305", layout="wide")


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────

def try_login(email: str, password: str):
    """Return user dict {id, name, email, role} or None."""
    # Check CUSTOMER table first
    res = (
        supabase.table("CUSTOMER")
        .select("customer_id, name, email")
        .eq("email", email)
        .eq("password", password)
        .limit(1)
        .execute()
    )
    if res.data:
        row = res.data[0]
        return {"id": row["customer_id"], "name": row["name"],
                "email": row["email"], "role": "customer"}
    # Check STAFF table
    res = (
        supabase.table("STAFF")
        .select("staff_id, name, email, role")
        .eq("email", email)
        .eq("password", password)
        .limit(1)
        .execute()
    )
    if res.data:
        row = res.data[0]
        return {"id": row["staff_id"], "name": row["name"],
                "email": row["email"], "role": row["role"]}
    return None


def register_customer(email, password, name, passport):
    supabase.table("CUSTOMER").insert({
        "email": email, "password": password,
        "name": name, "passport": passport or None,
    }).execute()


# ─────────────────────────────────────────────
# Sidebar — Auth
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("AirBooking")
        st.caption("CSE 305 Term Project")
        st.divider()

        if "user" not in st.session_state:
            tab_login, tab_reg = st.tabs(["Login", "Register"])

            with tab_login:
                email = st.text_input("Email", key="login_email")
                pwd   = st.text_input("Password", type="password", key="login_pwd")
                if st.button("Login", key="btn_login"):
                    user = try_login(email.strip(), pwd.strip())
                    if user:
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                st.caption("Demo accounts (password: **1234**)  \nalice@example.com  \nbob@example.com  \nadmin@airbooking.local")

            with tab_reg:
                r_name     = st.text_input("Full Name",  key="reg_name")
                r_email    = st.text_input("Email",       key="reg_email")
                r_pwd      = st.text_input("Password", type="password", key="reg_pwd")
                r_passport = st.text_input("Passport No (optional)", key="reg_passport")
                if st.button("Register", key="btn_register"):
                    if not r_name or not r_email or not r_pwd:
                        st.error("Name, email, and password are required.")
                    else:
                        try:
                            register_customer(r_email.strip(), r_pwd.strip(),
                                              r_name.strip(), r_passport.strip())
                            st.success("Account created. Please log in.")
                        except Exception as e:
                            st.error(f"Registration failed: {e}")
        else:
            user = st.session_state["user"]
            role_label = "Staff" if user["role"] != "customer" else "Customer"
            st.markdown(f"**{user['name']}**  \n`{role_label}`")
            st.caption(user["email"])
            if st.button("Logout", key="btn_logout"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()


# ─────────────────────────────────────────────
# Welcome screen
# ─────────────────────────────────────────────

def show_welcome():
    st.title("Welcome to AirBooking")
    st.write("Please log in using the sidebar.")
    st.info(
        "**Demo accounts** (password: `1234`)\n\n"
        "- Customer: `alice@example.com`\n"
        "- Customer: `bob@example.com`\n"
        "- Staff:    `admin@airbooking.local`"
    )


# ─────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────

def build_route(dep, dest, stopover_list):
    if stopover_list:
        stops = stopover_list.split(",")
        return " → ".join([dep] + stops + [dest])
    return f"{dep} → {dest}"


def fmt_cols(df, rename_map, keep):
    df = df.rename(columns=rename_map)
    return df[[c for c in keep if c in df.columns]]


# ─────────────────────────────────────────────
# CUSTOMER PORTAL
# ─────────────────────────────────────────────

def customer_portal():
    user = st.session_state["user"]
    st.title(f"Customer Portal — {user['name']}")

    tab_search, tab_book, tab_mybookings = st.tabs([
        "Search Flights", "Book Flight", "My Bookings"
    ])

    # ── Tab 1: Search Flights ──────────────────
    with tab_search:
        st.subheader("Search Available Flights")
        c1, c2 = st.columns(2)
        with c1:
            dep = st.text_input("Departure Airport (IATA)", placeholder="e.g. ICN", key="s_dep").upper()
        with c2:
            arr = st.text_input("Arrival Airport (IATA)",   placeholder="e.g. JFK", key="s_arr").upper()
        c3, c4 = st.columns(2)
        with c3:
            travel_date = st.date_input("Travel Date", value=date.today(), key="s_date")
        with c4:
            cls_filter = st.selectbox("Seat Class", ["All", "First", "Business", "Economy"], key="s_class")

        if st.button("Search", key="btn_search"):
            if not dep or not arr:
                st.error("Both airports are required.")
            else:
                try:
                    res = supabase.rpc("search_flights", {
                        "p_dep_iata":    dep,
                        "p_arr_iata":    arr,
                        "p_travel_date": str(travel_date),
                        "p_class_name":  None if cls_filter == "All" else cls_filter,
                    }).execute()
                    rows = res.data or []
                    if not rows:
                        st.info("No available flights found.")
                    else:
                        df = pd.DataFrame(rows)
                        df["Route"] = df.apply(
                            lambda r: build_route(dep, arr, r.get("stopover_list")), axis=1
                        )
                        df = df.rename(columns={
                            "flight_id": "Flight ID", "flight_number": "Flight",
                            "airline_name": "Airline", "depart_time": "Departure",
                            "arrival_time": "Arrival", "class_name": "Class",
                            "price": "Price (USD)", "available_seats": "Avail. Seats",
                        })
                        st.dataframe(
                            df[["Flight ID","Flight","Airline","Route",
                                "Departure","Arrival","Class","Price (USD)","Avail. Seats"]],
                            use_container_width=True,
                        )
                        st.caption("Copy a Flight ID from the table above to use in the Book Flight tab.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Tab 2: Book Flight ─────────────────────
    with tab_book:
        st.subheader("Create a Booking")
        flight_id = st.text_input("Flight ID (paste from search results)", key="b_fid").strip()
        cls_choice = st.selectbox("Seat Class", ["Economy", "Business", "First"], key="b_cls")

        avail_seats = []
        base_price  = None

        if flight_id:
            try:
                fd = supabase.table("FLIGHT").select("aircraft_id") \
                    .eq("flight_id", flight_id).limit(1).execute().data
                if fd:
                    ac_id = fd[0]["aircraft_id"]
                    cd = supabase.table("SEAT_CLASS") \
                        .select("class_id, price") \
                        .eq("aircraft_id", ac_id) \
                        .eq("class_name", cls_choice) \
                        .limit(1).execute().data
                    if cd:
                        class_id   = cd[0]["class_id"]
                        base_price = cd[0]["price"]
                        all_seats  = supabase.table("SEAT_INVENTORY") \
                            .select("seat_id, seat_number") \
                            .eq("class_id", class_id).execute().data
                        booked_ids = {
                            b["seat_id"] for b in
                            supabase.table("BOOKING").select("seat_id")
                            .eq("flight_id", flight_id).eq("status", "confirmed")
                            .execute().data
                        }
                        avail_seats = [s for s in all_seats if s["seat_id"] not in booked_ids]
            except Exception as e:
                st.warning(f"Could not load seats: {e}")

        if avail_seats and base_price is not None:
            opts = {s["seat_number"]: s["seat_id"] for s in avail_seats}
            chosen_num = st.selectbox("Select Seat", list(opts.keys()), key="b_seat")
            chosen_id  = opts[chosen_num]
            st.info(f"Price: USD {base_price}")

            if st.button("Confirm Booking", key="btn_book"):
                try:
                    res = supabase.rpc("create_booking", {
                        "p_customer_id": user["id"],
                        "p_flight_id":   flight_id,
                        "p_seat_id":     chosen_id,
                        "p_amount":      float(base_price),
                    }).execute()
                    st.success(f"Booking confirmed! Booking ID: `{res.data}`")
                except Exception as e:
                    st.error(f"Booking failed: {e}")
        elif flight_id:
            st.warning("No available seats for this flight and class.")

    # ── Tab 3: My Bookings ─────────────────────
    with tab_mybookings:
        st.subheader("My Bookings")
        if st.button("Load My Bookings", key="btn_load"):
            try:
                rows = supabase.table("BOOKING_VIEW") \
                    .select("*") \
                    .eq("customer_id", user["id"]) \
                    .eq("status", "confirmed") \
                    .execute().data
                st.session_state["my_bookings"] = rows
            except Exception as e:
                st.error(f"Error: {e}")

        if st.session_state.get("my_bookings"):
            bks = st.session_state["my_bookings"]
            df = pd.DataFrame(bks)
            cols = ["booking_id","flight_number","airline_name","flight_date",
                    "depart_airport_iata","dest_airport_iata","seat_number",
                    "class_name","price","ticket_no"]
            st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True)

            sel = st.selectbox("Select booking to cancel",
                               [b["booking_id"] for b in bks], key="b_cancel_sel")
            if st.button("Cancel Booking", key="btn_cancel"):
                try:
                    res = supabase.rpc("cancel_booking", {"p_booking_id": sel}).execute()
                    st.success(str(res.data))
                    st.session_state.pop("my_bookings", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Cancellation failed: {e}")
        elif "my_bookings" in st.session_state:
            st.info("No active bookings found.")

        st.divider()
        st.subheader("Refund History")
        if st.button("Load Refund History", key="btn_refunds"):
            try:
                cancelled = supabase.table("BOOKING").select("booking_id") \
                    .eq("customer_id", user["id"]).eq("status", "cancelled").execute().data
                booking_ids = [b["booking_id"] for b in cancelled]
                if booking_ids:
                    payments = supabase.table("PAYMENT").select("payment_id, booking_id") \
                        .in_("booking_id", booking_ids).execute().data
                    payment_ids = [p["payment_id"] for p in payments]
                    if payment_ids:
                        refunds = supabase.table("REFUND").select("*") \
                            .in_("payment_id", payment_ids).execute().data
                        st.session_state["my_refunds"] = refunds
                    else:
                        st.session_state["my_refunds"] = []
                else:
                    st.session_state["my_refunds"] = []
            except Exception as e:
                st.error(f"Error: {e}")

        if st.session_state.get("my_refunds"):
            df_r = pd.DataFrame(st.session_state["my_refunds"])
            if "refunded_at" in df_r.columns:
                df_r["refunded_at"] = (
                    pd.to_datetime(df_r["refunded_at"], utc=True)
                    .dt.tz_convert("Asia/Seoul")
                    .dt.strftime("%Y-%m-%d %H:%M:%S KST")
                )
            cols_r = ["refund_id", "payment_id", "amount", "status", "refunded_at"]
            st.dataframe(df_r[[c for c in cols_r if c in df_r.columns]], use_container_width=True)
        elif "my_refunds" in st.session_state:
            st.info("No refund history found.")


# ─────────────────────────────────────────────
# STAFF DASHBOARD
# ─────────────────────────────────────────────

def staff_dashboard():
    user = st.session_state["user"]
    st.title(f"Staff Dashboard — {user['name']}")

    tab_flights, tab_master, tab_revenue, tab_adv = st.tabs([
        "Flights", "Master Data", "Revenue Statistics", "Triggers Demo"
    ])

    # ═══════════════════════════════════════════
    # TAB 1: Flights
    # ═══════════════════════════════════════════
    with tab_flights:

        # ── Create Schedule + Generate Flights ──
        with st.expander("Create Schedule & Generate Flights", expanded=True):
            try:
                aircrafts = supabase.table("AIRCRAFT") \
                    .select("aircraft_id, model, AIRLINE(name)").execute().data
                airports  = supabase.table("AIRPORT").select("iata_code, city").execute().data
            except Exception as e:
                st.error(f"Failed to load master data: {e}")
                aircrafts, airports = [], []

            ac_opts = {
                f"{a.get('AIRLINE',{}).get('name','?')} — {a['model']}": a["aircraft_id"]
                for a in aircrafts
            }
            ap_opts = {f"{a['iata_code']} - {a['city']}": a["iata_code"] for a in airports}

            if not ac_opts or not ap_opts:
                st.warning("Add aircraft and airports in Master Data first.")
            else:
                sel_ac = st.selectbox("Aircraft", list(ac_opts.keys()), key="f_ac")
                c1, c2 = st.columns(2)
                with c1:
                    dep_lbl = st.selectbox("Departure Airport", list(ap_opts.keys()), key="f_dep")
                with c2:
                    arr_lbl = st.selectbox("Arrival Airport",   list(ap_opts.keys()), key="f_arr")
                fn = st.text_input("Flight Number (e.g. KE001)", key="f_fn")
                c3, c4 = st.columns(2)
                with c3:
                    dep_t = st.time_input("Departure Time", key="f_dt")
                with c4:
                    arr_t = st.time_input("Arrival Time",   key="f_at")
                days = st.multiselect("Operating Days",
                    ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], key="f_days")
                c5, c6 = st.columns(2)
                with c5:
                    vf = st.date_input("Valid From",  value=date.today(), key="f_vf")
                with c6:
                    vu = st.date_input("Valid Until", value=date.today(), key="f_vu")
                c7, c8 = st.columns(2)
                with c7:
                    gs = st.date_input("Generate Start", value=date.today(), key="f_gs")
                with c8:
                    ge = st.date_input("Generate End",   value=date.today(), key="f_ge")

                if st.button("Create Schedule & Generate Flights", key="btn_gen"):
                    dep_iata = ap_opts[dep_lbl]
                    arr_iata = ap_opts[arr_lbl]
                    if dep_iata == arr_iata:
                        st.error("Departure and arrival must differ.")
                    elif not days:
                        st.error("Select at least one operating day.")
                    elif not fn.strip():
                        st.error("Flight number is required.")
                    elif vf > vu:
                        st.error("Valid From must be ≤ Valid Until.")
                    elif gs > ge:
                        st.error("Generate Start must be ≤ Generate End.")
                    else:
                        try:
                            supabase.table("FLIGHT_SCHEDULE").insert({
                                "aircraft_id":        ac_opts[sel_ac],
                                "depart_airport_iata": dep_iata,
                                "dest_airport_iata":   arr_iata,
                                "flight_number":       fn.strip(),
                                "depart_time":         str(dep_t),
                                "arrival_time":        str(arr_t),
                                "days_of_week":        ",".join(days),
                                "valid_from":          str(vf),
                                "valid_until":         str(vu),
                            }).execute()
                            st.success("Schedule created.")
                            res = supabase.rpc("generate_flights", {
                                "p_start_date": str(gs),
                                "p_end_date":   str(ge),
                            }).execute()
                            st.success(str(res.data))
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── View Existing Flights ────────────────
        with st.expander("View Existing Flights"):
            c1, c2 = st.columns(2)
            with c1:
                vf_from = st.date_input("From", value=date.today(), key="vf_from")
            with c2:
                vf_to   = st.date_input("To",   value=date.today(), key="vf_to")
            if st.button("Load Flights", key="btn_vf"):
                try:
                    rows = supabase.table("FLIGHT_AVAILABILITY_VIEW") \
                        .select("flight_id,flight_number,airline_name,depart_airport_iata,dest_airport_iata,flight_date,depart_time,arrival_time,flight_status,class_name,available_seats") \
                        .gte("flight_date", str(vf_from)) \
                        .lte("flight_date", str(vf_to)) \
                        .execute().data
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)
                    else:
                        st.info("No flights in this date range.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # ═══════════════════════════════════════════
    # TAB 2: Master Data
    # ═══════════════════════════════════════════
    with tab_master:
        sub_al, sub_ap, sub_ac, sub_sc = st.tabs(
            ["Airlines", "Airports", "Aircraft", "Seat Classes"]
        )

        # ── Airlines ──────────────────────────────
        with sub_al:
            st.subheader("Airlines")
            try:
                al_rows = supabase.table("AIRLINE").select("*").execute().data
                if al_rows:
                    al_df = pd.DataFrame(al_rows)
                    st.dataframe(al_df[["airline_id","iata_code","name","country"]],
                                 use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
                al_rows = []

            with st.expander("Add Airline"):
                iata = st.text_input("IATA Code (2–3 chars)", key="al_iata").upper()
                name = st.text_input("Airline Name",           key="al_name")
                ctry = st.text_input("Country",                key="al_ctry")
                if st.button("Add Airline", key="btn_al_add"):
                    if not iata or not name:
                        st.error("IATA code and name are required.")
                    else:
                        try:
                            supabase.table("AIRLINE").insert(
                                {"iata_code": iata, "name": name, "country": ctry or None}
                            ).execute()
                            st.success(f"Airline '{name}' added.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            with st.expander("Delete Airline"):
                if al_rows:
                    del_opts = {f"{a['iata_code']} — {a['name']}": a["airline_id"] for a in al_rows}
                    sel_del = st.selectbox("Select airline to delete", list(del_opts.keys()), key="al_del_sel")
                    st.warning("Deleting an airline also deletes its aircraft, seat classes, and seat inventory (CASCADE).")
                    if st.button("Delete", key="btn_al_del"):
                        try:
                            supabase.table("AIRLINE").delete() \
                                .eq("airline_id", del_opts[sel_del]).execute()
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Airports ──────────────────────────────
        with sub_ap:
            st.subheader("Airports")
            try:
                ap_rows = supabase.table("AIRPORT").select("*").execute().data
                if ap_rows:
                    st.dataframe(pd.DataFrame(ap_rows)[["airport_id","iata_code","name","city","country"]],
                                 use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
                ap_rows = []

            with st.expander("Add Airport"):
                iata = st.text_input("IATA Code", key="ap_iata").upper()
                name = st.text_input("Airport Name", key="ap_name")
                city = st.text_input("City",         key="ap_city")
                ctry = st.text_input("Country",      key="ap_ctry")
                if st.button("Add Airport", key="btn_ap_add"):
                    if not iata or not name or not city or not ctry:
                        st.error("All fields are required.")
                    else:
                        try:
                            supabase.table("AIRPORT").insert(
                                {"iata_code": iata, "name": name, "city": city, "country": ctry}
                            ).execute()
                            st.success(f"Airport '{name}' added.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            with st.expander("Delete Airport"):
                if ap_rows:
                    del_opts = {f"{a['iata_code']} — {a['name']}": a["airport_id"] for a in ap_rows}
                    sel_del  = st.selectbox("Select airport", list(del_opts.keys()), key="ap_del_sel")
                    if st.button("Delete", key="btn_ap_del"):
                        try:
                            supabase.table("AIRPORT").delete() \
                                .eq("airport_id", del_opts[sel_del]).execute()
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Aircraft ──────────────────────────────
        with sub_ac:
            st.subheader("Aircraft")
            try:
                ac_rows = supabase.table("AIRCRAFT") \
                    .select("aircraft_id, model, AIRLINE(name, iata_code)").execute().data
                if ac_rows:
                    ac_df = pd.DataFrame([{
                        "aircraft_id": r["aircraft_id"],
                        "model":       r["model"],
                        "airline":     r.get("AIRLINE",{}).get("name","?"),
                        "iata":        r.get("AIRLINE",{}).get("iata_code","?"),
                    } for r in ac_rows])
                    st.dataframe(ac_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
                ac_rows = []

            with st.expander("Add Aircraft"):
                try:
                    al_list = supabase.table("AIRLINE").select("airline_id, name, iata_code").execute().data
                    al_opts = {f"{a['iata_code']} — {a['name']}": a["airline_id"] for a in al_list}
                except Exception:
                    al_opts = {}
                if al_opts:
                    sel_al = st.selectbox("Airline", list(al_opts.keys()), key="ac_al")
                    model  = st.text_input("Model (e.g. Boeing 737-800)", key="ac_model")
                    if st.button("Add Aircraft", key="btn_ac_add"):
                        if not model:
                            st.error("Model is required.")
                        else:
                            try:
                                supabase.table("AIRCRAFT").insert(
                                    {"airline_id": al_opts[sel_al], "model": model.strip()}
                                ).execute()
                                st.success("Aircraft added.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.warning("Add an airline first.")

            with st.expander("Delete Aircraft"):
                if ac_rows:
                    del_opts = {
                        f"{r.get('AIRLINE',{}).get('iata_code','?')} — {r['model']}": r["aircraft_id"]
                        for r in ac_rows
                    }
                    sel_del = st.selectbox("Select aircraft", list(del_opts.keys()), key="ac_del_sel")
                    st.warning("Deleting an aircraft also deletes its seat classes and seat inventory (CASCADE).")
                    if st.button("Delete", key="btn_ac_del"):
                        try:
                            supabase.table("AIRCRAFT").delete() \
                                .eq("aircraft_id", del_opts[sel_del]).execute()
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Seat Classes ──────────────────────────
        with sub_sc:
            st.subheader("Seat Classes")
            try:
                sc_rows = supabase.table("SEAT_CLASS") \
                    .select("class_id, class_name, seat_count, price, AIRCRAFT(model, AIRLINE(iata_code))") \
                    .execute().data
                if sc_rows:
                    sc_df = pd.DataFrame([{
                        "class_id":   r["class_id"],
                        "aircraft":   r.get("AIRCRAFT",{}).get("model","?"),
                        "airline":    (r.get("AIRCRAFT",{}).get("AIRLINE") or {}).get("iata_code","?"),
                        "class":      r["class_name"],
                        "seats":      r["seat_count"],
                        "price_usd":  r["price"],
                    } for r in sc_rows])
                    st.dataframe(sc_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
                sc_rows = []

            with st.expander("Add Seat Class  (trigger auto-generates seat inventory)"):
                try:
                    ac_list = supabase.table("AIRCRAFT") \
                        .select("aircraft_id, model, AIRLINE(iata_code)").execute().data
                    ac_opts2 = {
                        f"{r.get('AIRLINE',{}).get('iata_code','?')} — {r['model']}": r["aircraft_id"]
                        for r in ac_list
                    }
                except Exception:
                    ac_opts2 = {}
                if ac_opts2:
                    sel_ac2    = st.selectbox("Aircraft", list(ac_opts2.keys()), key="sc_ac")
                    cls_name   = st.selectbox("Class", ["First","Business","Economy"], key="sc_cls")
                    seat_cnt   = st.number_input("Seat Count", min_value=1, max_value=500, value=10, key="sc_cnt")
                    price_val  = st.number_input("Price (USD)", min_value=0.0, value=500.0, key="sc_price")
                    if st.button("Add Seat Class", key="btn_sc_add"):
                        try:
                            supabase.table("SEAT_CLASS").insert({
                                "aircraft_id": ac_opts2[sel_ac2],
                                "class_name":  cls_name,
                                "seat_count":  int(seat_cnt),
                                "price":       float(price_val),
                            }).execute()
                            st.success(f"Seat class added. Trigger auto-generated {int(seat_cnt)} seats.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Add aircraft first.")

            with st.expander("Delete Seat Class"):
                if sc_rows:
                    del_opts = {
                        f"{(r.get('AIRCRAFT',{}).get('AIRLINE') or {}).get('iata_code','?')} — {r.get('AIRCRAFT',{}).get('model','?')} — {r['class_name']}": r["class_id"]
                        for r in sc_rows
                    }
                    sel_del = st.selectbox("Select seat class", list(del_opts.keys()), key="sc_del_sel")
                    st.warning("Deleting a seat class also deletes its seat inventory (CASCADE).")
                    if st.button("Delete", key="btn_sc_del"):
                        try:
                            supabase.table("SEAT_CLASS").delete() \
                                .eq("class_id", del_opts[sel_del]).execute()
                            st.success("Deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ═══════════════════════════════════════════
    # TAB 3: Revenue Statistics
    # ═══════════════════════════════════════════
    with tab_revenue:
        st.subheader("Revenue Statistics")
        if st.button("Generate Revenue Report", key="btn_rev"):
            try:
                res  = supabase.rpc("get_revenue_report", {}).execute()
                rows = res.data or []
                if not rows:
                    st.info("No revenue data available. Create some bookings first.")
                else:
                    df = pd.DataFrame(rows)
                    df["revenue_month"]   = pd.to_datetime(df["revenue_month"]).dt.strftime("%Y-%m")
                    df["revenue_quarter"] = pd.to_datetime(df["revenue_quarter"]).dt.to_period("Q").astype(str)

                    st.write("**Revenue by Flight and Class**")
                    disp_cols = ["flight_number","airline_name","route","flight_date",
                                 "class_name","total_revenue","class_revenue_pct","load_factor_percentage"]
                    st.dataframe(df[[c for c in disp_cols if c in df.columns]], use_container_width=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Revenue by Month**")
                        monthly = df.groupby("revenue_month")["total_revenue"].sum().reset_index()
                        st.bar_chart(monthly.set_index("revenue_month"))
                    with c2:
                        st.write("**Revenue by Route**")
                        route_rev = df.groupby("route")["total_revenue"].sum() \
                            .sort_values(ascending=False).reset_index()
                        st.bar_chart(route_rev.set_index("route"))

                    st.write("**Revenue by Seat Class**")
                    class_rev = df.groupby("class_name")["total_revenue"].sum().reset_index()
                    st.bar_chart(class_rev.set_index("class_name"))
            except Exception as e:
                st.error(f"Error: {e}")

    # ═══════════════════════════════════════════
    # TAB 4: Triggers Demo
    # ═══════════════════════════════════════════
    with tab_adv:
        st.subheader("Advanced Feature: Triggers & Stored Procedures")
        st.write(
            "This project implements **3 database triggers** and **5 stored procedures** "
            "as PL/pgSQL functions in PostgreSQL. The demos below show each trigger firing live."
        )

        # ── Demo 1: Auto-generate Seat Inventory ──
        with st.expander("Demo 1 — trg_auto_generate_seats (Auto-generate Seat Inventory)", expanded=True):
            st.markdown("""
**What it does:** When a `SEAT_CLASS` row is inserted, the trigger automatically populates
`SEAT_INVENTORY` with the correct number of physical seats using a row/column numbering scheme
(First: 1A/1B, Business: 10A–10D, Economy: 20A–20F).
""")
            st.code("""-- Trigger fires AFTER INSERT ON SEAT_CLASS
CREATE OR REPLACE FUNCTION public.fn_auto_generate_seats()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_start_row INT; v_cols TEXT[]; v_cols_count INT;
    v_row INT; v_col_idx INT; v_seat_label TEXT;
BEGIN
    CASE NEW.class_name
        WHEN 'First'    THEN v_start_row := 1;  v_cols := ARRAY['A','B'];
        WHEN 'Business' THEN v_start_row := 10; v_cols := ARRAY['A','B','C','D'];
        WHEN 'Economy'  THEN v_start_row := 20; v_cols := ARRAY['A','B','C','D','E','F'];
    END CASE;
    v_cols_count := array_length(v_cols, 1);
    FOR i IN 1..NEW.seat_count LOOP
        v_row       := v_start_row + ((i - 1) / v_cols_count);
        v_col_idx   := ((i - 1) % v_cols_count) + 1;
        v_seat_label := v_row::TEXT || v_cols[v_col_idx];
        INSERT INTO public."SEAT_INVENTORY" (class_id, aircraft_id, seat_number)
        VALUES (NEW.class_id, NEW.aircraft_id, v_seat_label);
    END LOOP;
    RETURN NEW;
END; $$;""", language="sql")

            st.markdown("**Live Demo:** Create a temporary aircraft + seat class, then observe auto-generated seats.")
            demo_model = st.text_input("Test Aircraft Model", value="Demo Boeing 737-800", key="d1_model")
            demo_class = st.selectbox("Test Seat Class", ["Economy","Business","First"], key="d1_cls")
            demo_count = st.number_input("Seat Count", min_value=1, max_value=20, value=6, key="d1_cnt")
            try:
                al_list = supabase.table("AIRLINE").select("airline_id, name, iata_code").execute().data
                al_opts = {f"{a['iata_code']} — {a['name']}": a["airline_id"] for a in al_list}
            except Exception:
                al_opts = {}

            if al_opts:
                sel_demo_al = st.selectbox("Assign to Airline", list(al_opts.keys()), key="d1_al")

            c_run, c_clean = st.columns(2)
            with c_run:
                if st.button("Run Demo", key="btn_d1_run") and al_opts:
                    try:
                        # Create temp aircraft
                        ac_res = supabase.table("AIRCRAFT").insert({
                            "airline_id": al_opts[sel_demo_al],
                            "model":      demo_model.strip(),
                        }).execute()
                        demo_ac_id = ac_res.data[0]["aircraft_id"]
                        st.session_state["demo1_ac_id"] = demo_ac_id

                        # Insert seat class → trigger fires
                        supabase.table("SEAT_CLASS").insert({
                            "aircraft_id": demo_ac_id,
                            "class_name":  demo_class,
                            "seat_count":  int(demo_count),
                            "price":       999.0,
                        }).execute()

                        # Fetch auto-generated seats
                        seats = supabase.table("SEAT_INVENTORY") \
                            .select("seat_number, class_id") \
                            .eq("aircraft_id", demo_ac_id).execute().data
                        st.success(f"Trigger fired! {len(seats)} seats auto-generated:")
                        st.dataframe(pd.DataFrame(seats), use_container_width=True)
                    except Exception as e:
                        st.error(f"Demo error: {e}")

            with c_clean:
                if st.button("Clean Up", key="btn_d1_clean"):
                    ac_id = st.session_state.get("demo1_ac_id")
                    if ac_id:
                        try:
                            supabase.table("AIRCRAFT").delete().eq("aircraft_id", ac_id).execute()
                            st.session_state.pop("demo1_ac_id", None)
                            st.success("Test aircraft and its seats deleted.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.info("Nothing to clean up.")

        # ── Demo 2: Booking Validation ─────────────
        with st.expander("Demo 2 — trg_validate_booking (Booking Integrity Check)"):
            st.markdown("""
**What it does:** `BEFORE INSERT ON BOOKING`, this trigger:
1. Verifies the flight exists and has status `'scheduled'`
2. Verifies the seat belongs to the same aircraft as the flight

If either check fails, the INSERT is aborted with an exception — the booking never persists.
""")
            st.code("""CREATE OR REPLACE FUNCTION public.fn_validate_booking()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_flight_aircraft_id uuid; v_seat_aircraft_id uuid; v_flight_status varchar;
BEGIN
    SELECT f.aircraft_id, f.status INTO v_flight_aircraft_id, v_flight_status
    FROM public."FLIGHT" f WHERE f.flight_id = NEW.flight_id;

    IF v_flight_status != 'scheduled' THEN
        RAISE EXCEPTION 'Cannot book: flight status is "%" (must be "scheduled").', v_flight_status;
    END IF;

    SELECT si.aircraft_id INTO v_seat_aircraft_id
    FROM public."SEAT_INVENTORY" si WHERE si.seat_id = NEW.seat_id;

    IF v_seat_aircraft_id != v_flight_aircraft_id THEN
        RAISE EXCEPTION 'Seat does not belong to the aircraft assigned to this flight.';
    END IF;
    RETURN NEW;
END; $$;""", language="sql")

            st.markdown("**Live Demo:** Set a flight to `'cancelled'` status, then attempt a booking — the trigger blocks it.")
            try:
                flights = supabase.table("FLIGHT") \
                    .select("flight_id, flight_date, status, FLIGHT_SCHEDULE(flight_number)") \
                    .eq("status", "scheduled").limit(20).execute().data
                flight_opts = {
                    f"{r.get('FLIGHT_SCHEDULE',{}).get('flight_number','?')} on {r['flight_date']} [{r['flight_id'][:8]}...]": r["flight_id"]
                    for r in flights
                }
            except Exception:
                flight_opts = {}

            if flight_opts:
                sel_f = st.selectbox("Select a flight for demo", list(flight_opts.keys()), key="d2_flt")
                flt_id = flight_opts[sel_f]

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Set to 'departed' (makes booking invalid)", key="btn_d2_set"):
                        try:
                            supabase.table("FLIGHT").update({"status": "departed"}) \
                                .eq("flight_id", flt_id).execute()
                            st.warning("Flight set to 'departed'. Now try booking below.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                with c2:
                    if st.button("Reset to 'scheduled'", key="btn_d2_reset"):
                        try:
                            supabase.table("FLIGHT").update({"status": "scheduled"}) \
                                .eq("flight_id", flt_id).execute()
                            st.success("Flight reset to 'scheduled'.")
                        except Exception as e:
                            st.error(f"Error: {e}")

                if st.button("Attempt Booking (should be blocked by trigger)", key="btn_d2_book"):
                    try:
                        # Use a dummy customer and seat — trigger will fire before any real data matters
                        cust = supabase.table("CUSTOMER").select("customer_id").limit(1).execute().data
                        seat = supabase.table("SEAT_INVENTORY").select("seat_id").limit(1).execute().data
                        if cust and seat:
                            supabase.rpc("create_booking", {
                                "p_customer_id": cust[0]["customer_id"],
                                "p_flight_id":   flt_id,
                                "p_seat_id":     seat[0]["seat_id"],
                                "p_amount":      100.0,
                            }).execute()
                            st.warning("Booking succeeded (flight was still 'scheduled').")
                    except Exception as e:
                        st.error(f"Trigger blocked the booking: {e}")
            else:
                st.info("No scheduled flights available for demo.")

        # ── Demo 3: Guard Seat Count Update ────────
        with st.expander("Demo 3 — trg_guard_seat_class_update (Guard Seat Count Changes)"):
            st.markdown("""
**What it does:** `BEFORE UPDATE ON SEAT_CLASS` — if `seat_count` changes:
- **With active bookings:** raises an exception, blocking the update
- **Without active bookings:** deletes all existing seat rows (a second `AFTER UPDATE` trigger then regenerates them with the new count)
""")
            st.code("""CREATE OR REPLACE FUNCTION public.fn_guard_seat_class_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_booked_count INT; BEGIN
    IF NEW.seat_count = OLD.seat_count THEN RETURN NEW; END IF;

    SELECT COUNT(*) INTO v_booked_count
    FROM public."BOOKING" b
    JOIN public."SEAT_INVENTORY" si ON si.seat_id = b.seat_id
    WHERE si.class_id = OLD.class_id AND b.status = 'confirmed';

    IF v_booked_count > 0 THEN
        RAISE EXCEPTION
            'Cannot modify seat_count: % active booking(s) exist for class "%" on this aircraft.',
            v_booked_count, OLD.class_name;
    END IF;

    DELETE FROM public."SEAT_INVENTORY"
    WHERE class_id = OLD.class_id AND aircraft_id = OLD.aircraft_id;
    RETURN NEW;
END; $$;""", language="sql")

            st.markdown("**Live Demo:** Try updating seat_count on a seat class. If bookings exist it will be blocked.")
            try:
                sc_list = supabase.table("SEAT_CLASS") \
                    .select("class_id, class_name, seat_count, AIRCRAFT(model, AIRLINE(iata_code))") \
                    .execute().data
                sc_opts = {
                    f"{(r.get('AIRCRAFT',{}).get('AIRLINE') or {}).get('iata_code','?')} — {r.get('AIRCRAFT',{}).get('model','?')} — {r['class_name']} ({r['seat_count']} seats)": r["class_id"]
                    for r in sc_list
                }
            except Exception:
                sc_opts = {}

            if sc_opts:
                sel_sc   = st.selectbox("Select seat class", list(sc_opts.keys()), key="d3_sc")
                new_cnt  = st.number_input("New Seat Count", min_value=1, max_value=500, value=8, key="d3_cnt")
                if st.button("Update Seat Count", key="btn_d3_upd"):
                    try:
                        supabase.table("SEAT_CLASS").update({"seat_count": int(new_cnt)}) \
                            .eq("class_id", sc_opts[sel_sc]).execute()
                        st.success(f"Updated to {int(new_cnt)} seats. Old seats deleted and regenerated by trigger.")
                        # Show new seat inventory
                        seats = supabase.table("SEAT_INVENTORY") \
                            .select("seat_number") \
                            .eq("class_id", sc_opts[sel_sc]).execute().data
                        st.dataframe(pd.DataFrame(seats), use_container_width=True)
                    except Exception as e:
                        st.error(f"Trigger blocked the update: {e}")
            else:
                st.info("No seat classes found.")

        # ── Stored Procedures Summary ────────────
        with st.expander("Stored Procedures Summary"):
            st.markdown("""
| Procedure | Description |
|---|---|
| `generate_flights(start, end)` | Generates individual `FLIGHT` rows from all recurring `FLIGHT_SCHEDULE` records for the given date range. Skips already-generated dates. |
| `search_flights(dep, arr, date, class)` | Returns available flights with seat counts from `FLIGHT_AVAILABILITY_VIEW`. Includes stopover list via `string_agg`. |
| `create_booking(customer, flight, seat, amount)` | **Atomic**: INSERT BOOKING → INSERT PAYMENT → INSERT TICKET. Rolls back all on any failure. |
| `cancel_booking(booking_id)` | **Atomic**: DELETE TICKET → UPDATE BOOKING status='cancelled' → UPDATE PAYMENT status='refunded' → INSERT REFUND. |
| `get_revenue_report()` | Aggregates revenue, class breakdown %, and load factor % from `REVENUE_STATS_VIEW`. |
""")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

render_sidebar()

if "user" not in st.session_state:
    show_welcome()
elif st.session_state["user"]["role"] == "customer":
    customer_portal()
else:
    staff_dashboard()
