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
                st.caption(
                    "Demo accounts (password: **1234**)  \n"
                    "alice@example.com  \nbob@example.com  \ncharlie@example.com  \n"
                    "admin@airbooking.local"
                )

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
        "- Customer: `charlie@example.com`\n"
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


def _format_plan(data):
    """Convert PostgREST SETOF text response into one newline-joined block.
    PostgREST may return either a list[str] or list[{<func_name>: str}]."""
    rows = data or []
    if rows and isinstance(rows[0], dict):
        rows = [next(iter(r.values()), "") for r in rows]
    return "\n".join(str(x) for x in rows)


def fmt_cols(df, rename_map, keep):
    df = df.rename(columns=rename_map)
    return df[[c for c in keep if c in df.columns]]


def _render_explain_comparison(data):
    """Split the EXPLAIN output on the '=== Without Indexes ===' marker and render two code boxes."""
    rows = data or []
    if rows and isinstance(rows[0], dict):
        rows = [next(iter(r.values()), "") for r in rows]
    full = "\n".join(str(x) for x in rows)

    marker = "=== Without Indexes (simulated: index scans disabled) ==="
    if marker in full:
        parts = full.split(marker, 1)
        with_part    = parts[0].replace("=== With Indexes ===", "").strip()
        without_part = parts[1].strip()
        st.markdown("**With Indexes** (current schema)")
        st.code(with_part or "(no plan)", language="text")
        st.markdown("**Without Indexes** (index scans disabled — simulated)")
        st.code(without_part or "(no plan)", language="text")
    else:
        st.code(full or "(no plan returned)", language="text")


def _load_seats(flight_id: str, class_name: str) -> list:
    """Return available [{seat_id, seat_number}] for a flight+class."""
    try:
        fd = supabase.table("FLIGHT").select("aircraft_id") \
            .eq("flight_id", flight_id).limit(1).execute().data
        if not fd:
            return []
        ac_id = fd[0]["aircraft_id"]
        cd = supabase.table("SEAT_CLASS").select("class_id") \
            .eq("aircraft_id", ac_id).eq("class_name", class_name) \
            .limit(1).execute().data
        if not cd:
            return []
        class_id = cd[0]["class_id"]
        all_seats = supabase.table("SEAT_INVENTORY") \
            .select("seat_id, seat_number").eq("class_id", class_id).execute().data
        booked = {
            b["seat_id"] for b in
            supabase.table("BOOKING").select("seat_id")
            .eq("flight_id", flight_id).eq("status", "confirmed").execute().data
        }
        return [s for s in all_seats if s["seat_id"] not in booked]
    except Exception:
        return []


def _render_direct_card(idx, row, dep_iata, arr_iata, user, active_idx):
    dep_t = pd.to_datetime(row["depart_time"]).strftime("%H:%M")
    arr_t = pd.to_datetime(row["arrival_time"]).strftime("%H:%M")
    stops = int(row.get("stop_count", 0))
    eff   = float(row["effective_price"])
    base  = float(row["price"])
    route = build_route(dep_iata, arr_iata, row.get("stopover_list"))
    avail = int(row.get("available_seats", 0))

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        st.markdown(f"**{row['flight_number']}** — {row['airline_name']}")
        stop_label = ("Direct" if stops == 0
                      else f"{stops} stop{'s' if stops > 1 else ''} (multi-leg route)")
        st.caption(f"{route}  •  {stop_label}")
    with c2:
        st.markdown(f"🛫 **{dep_t}** → 🛬 **{arr_t}**")
        st.caption(row.get("class_name", ""))
    with c3:
        st.markdown(f"**${eff:.2f}**")
        if stops > 0 and base > eff:
            st.caption(f"Base ${base:.2f}  |  {avail} seat(s)")
        else:
            st.caption(f"{avail} seat(s) available")
    with c4:
        if active_idx == idx:
            if st.button("✕", key=f"cclose_{idx}"):
                st.session_state["booking_card_idx"] = None
                st.rerun()
        else:
            if st.button("Book →", key=f"cbook_{idx}", type="primary"):
                st.session_state["booking_card_idx"] = idx
                st.rerun()

    if active_idx == idx:
        st.divider()
        avail_seats = _load_seats(row["flight_id"], row["class_name"])
        if not avail_seats:
            st.warning("No seats available in this class.")
        else:
            seat_opts  = {s["seat_number"]: s["seat_id"] for s in avail_seats}
            chosen_num = st.selectbox("Select Seat", list(seat_opts.keys()), key=f"dseat_{idx}")
            chosen_id  = seat_opts[chosen_num]
            st.info(f"**{row['flight_number']}** · Seat **{chosen_num}** · **${eff:.2f}**")
            if st.button("Confirm Booking", key=f"dconfirm_{idx}", type="primary"):
                try:
                    supabase.rpc("create_booking", {
                        "p_customer_id": user["id"],
                        "p_flight_id":   row["flight_id"],
                        "p_seat_id":     chosen_id,
                        "p_amount":      eff,
                    }).execute()
                    st.success(f"Booked: {row['flight_number']} seat {chosen_num} — ${eff:.2f}")
                    st.session_state["booking_card_idx"] = None
                    st.session_state.pop("my_bookings", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Booking failed: {e}")


def _render_connection_card(idx, row, dep_iata, arr_iata, user, active_idx):
    f1d  = pd.to_datetime(row["flight1_depart"]).strftime("%H:%M")
    f1a  = pd.to_datetime(row["flight1_arrival"]).strftime("%H:%M")
    f2d  = pd.to_datetime(row["flight2_depart"]).strftime("%H:%M")
    f2a  = pd.to_datetime(row["flight2_arrival"]).strftime("%H:%M")
    hub  = row["hub_iata"]
    cpr  = float(row["connection_price"])
    lp1  = float(row["leg1_price"])
    lp2  = float(row["leg2_price"])
    lmin = int(row["layover_minutes"])
    lh, lm = divmod(lmin, 60)

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        st.markdown(f"**{row['flight1_number']} + {row['flight2_number']}** — {row['flight1_airline']}")
        st.caption(f"{dep_iata} → **{hub}** → {arr_iata}  •  Connection")
    with c2:
        st.markdown(f"🛫 **{f1d}**→{f1a} | {f2d}→**{f2a}** 🛬")
        st.caption(f"Layover {lh}h {lm}m  |  {row.get('class_name', '')}")
    with c3:
        st.markdown(f"**${cpr:.2f}** total")
        saving = (lp1 + lp2) - cpr
        if saving > 0:
            st.caption(f"Save **${saving:.2f}**  |  {row['leg1_available']}/{row['leg2_available']} seats/leg")
        else:
            st.caption(f"{row['leg1_available']}/{row['leg2_available']} seats per leg")
    with c4:
        if active_idx == idx:
            if st.button("✕", key=f"cclose_{idx}"):
                st.session_state["booking_card_idx"] = None
                st.rerun()
        else:
            if st.button("Book →", key=f"cbook_{idx}", type="primary"):
                st.session_state["booking_card_idx"] = idx
                st.rerun()

    if active_idx == idx:
        st.divider()
        cl1, cl2 = st.columns(2)
        with cl1:
            st.markdown(f"**Leg 1:** {row['flight1_number']} — {dep_iata}→{hub}")
            seats1 = _load_seats(row["flight1_id"], row["class_name"])
            if seats1:
                opts1 = {s["seat_number"]: s["seat_id"] for s in seats1}
                sn1   = st.selectbox("Seat (Leg 1)", list(opts1.keys()), key=f"cs1_{idx}")
                sid1  = opts1[sn1]
            else:
                st.warning("No seats available for Leg 1.")
                sn1, sid1 = None, None
        with cl2:
            st.markdown(f"**Leg 2:** {row['flight2_number']} — {hub}→{arr_iata}")
            seats2 = _load_seats(row["flight2_id"], row["class_name"])
            if seats2:
                opts2 = {s["seat_number"]: s["seat_id"] for s in seats2}
                sn2   = st.selectbox("Seat (Leg 2)", list(opts2.keys()), key=f"cs2_{idx}")
                sid2  = opts2[sn2]
            else:
                st.warning("No seats available for Leg 2.")
                sn2, sid2 = None, None

        total_base = lp1 + lp2
        amt1 = round(cpr * (lp1 / total_base), 2) if total_base > 0 else round(cpr / 2, 2)
        amt2 = round(cpr - amt1, 2)

        if sn1 and sn2:
            st.info(
                f"**{row['flight1_number']}** seat {sn1} + "
                f"**{row['flight2_number']}** seat {sn2} — Total **${cpr:.2f}**"
            )
        if sid1 and sid2:
            if st.button("Confirm Itinerary", key=f"cconfirm_{idx}", type="primary"):
                try:
                    supabase.rpc("create_itinerary_booking", {
                        "p_customer_id": user["id"],
                        "p_flight1_id":  row["flight1_id"],
                        "p_seat1_id":    sid1,
                        "p_amount1":     amt1,
                        "p_flight2_id":  row["flight2_id"],
                        "p_seat2_id":    sid2,
                        "p_amount2":     amt2,
                    }).execute()
                    st.success(f"Itinerary booked: {dep_iata}→{hub}→{arr_iata} — Total ${cpr:.2f}")
                    st.session_state["booking_card_idx"] = None
                    st.session_state.pop("my_bookings", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Itinerary booking failed: {e}")


# ─────────────────────────────────────────────
# CUSTOMER PORTAL
# ─────────────────────────────────────────────

def customer_portal():
    user = st.session_state["user"]
    st.title(f"Customer Portal — {user['name']}")

    tab_search, tab_mybookings = st.tabs(["Search & Book Flights", "My Bookings"])

    # ── Tab 1: Search & Book Flights ──────────────────
    with tab_search:
        with st.expander("Search Flights", expanded=True):
            try:
                airports = supabase.table("AIRPORT").select("iata_code, city").execute().data
            except Exception as e:
                st.error(f"Failed to load airports: {e}")
                airports = []
            ap_opts = {f"{a['iata_code']} - {a['city']}": a["iata_code"] for a in airports}

            if not ap_opts:
                st.warning("No airports found — run the seed script first.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    dep_lbl = st.selectbox("Departure Airport", list(ap_opts.keys()), key="cust_dep")
                with c2:
                    arr_lbl = st.selectbox("Arrival Airport", list(ap_opts.keys()), key="cust_arr")
                c3, c4 = st.columns(2)
                with c3:
                    travel_date = st.date_input("Travel Date", value=date.today(), key="s_date")
                with c4:
                    cls_filter = st.selectbox("Seat Class", ["All", "First", "Business", "Economy"], key="s_class")
                c5, c6 = st.columns([1, 1])
                with c5:
                    search_clicked = st.button("Search Flights", key="btn_search", type="primary")
                with c6:
                    inc_conn = st.checkbox("Include dynamic connections", value=True, key="s_connections")

                if search_clicked:
                    dep = ap_opts[dep_lbl]
                    arr = ap_opts[arr_lbl]
                    if dep == arr:
                        st.error("Departure and arrival airports must differ.")
                    else:
                        direct_rows, conn_rows = [], []
                        try:
                            res = supabase.rpc("search_flights", {
                                "p_dep_iata":    dep,
                                "p_arr_iata":    arr,
                                "p_travel_date": str(travel_date),
                                "p_class_name":  None if cls_filter == "All" else cls_filter,
                            }).execute()
                            direct_rows = res.data or []
                            for r in direct_rows:
                                r["_type"] = "direct"
                        except Exception as e:
                            st.error(f"Search error: {e}")

                        if inc_conn:
                            try:
                                cres = supabase.rpc("search_connections", {
                                    "p_dep_iata":    dep,
                                    "p_arr_iata":    arr,
                                    "p_travel_date": str(travel_date),
                                    "p_class_name":  None if cls_filter == "All" else cls_filter,
                                }).execute()
                                conn_rows = cres.data or []
                                for r in conn_rows:
                                    r["_type"] = "connection"
                            except Exception:
                                pass

                        st.session_state.update({
                            "sr_direct": direct_rows,
                            "sr_conn":   conn_rows,
                            "sr_dep":    dep,
                            "sr_arr":    arr,
                            "booking_card_idx": None,
                        })

        # ── Results + filter/sort controls ───────────
        direct_rows = st.session_state.get("sr_direct")
        conn_rows   = st.session_state.get("sr_conn", [])
        dep = st.session_state.get("sr_dep", "")
        arr = st.session_state.get("sr_arr", "")

        if direct_rows is None:
            st.caption("Enter your route and date above, then click **Search Flights**.")
        else:
            all_results = (direct_rows or []) + (conn_rows or [])
            if not all_results:
                st.info("No flights found for this route and date. Try a different date or class.")
            else:
                fc1, fc2, fc3 = st.columns([2, 2, 2])
                with fc1:
                    sort_by = st.selectbox("Sort by",
                        ["Price ↑", "Price ↓", "Departure time", "Arrival time"],
                        key="res_sort")
                with fc2:
                    type_filter = st.radio("Show",
                        ["All", "Direct only", "Connections only"],
                        horizontal=True, key="res_type")
                with fc3:
                    airlines = sorted({
                        r.get("airline_name") or r.get("flight1_airline", "")
                        for r in all_results
                    } - {""})
                    airline_sel = st.multiselect("Airline", airlines, default=airlines, key="res_airline")

                filtered = list(all_results)
                if type_filter == "Direct only":
                    filtered = [r for r in filtered if r["_type"] == "direct"]
                elif type_filter == "Connections only":
                    filtered = [r for r in filtered if r["_type"] == "connection"]
                if airline_sel:
                    filtered = [r for r in filtered
                                if (r.get("airline_name") or r.get("flight1_airline", ""))
                                in airline_sel]

                def _price(r):
                    return float(r["effective_price"] if r["_type"] == "direct" else r["connection_price"])
                def _dep_t(r):
                    return str(r.get("depart_time") or r.get("flight1_depart", ""))
                def _arr_t(r):
                    return str(r.get("arrival_time") or r.get("flight2_arrival", ""))

                if sort_by == "Price ↑":
                    filtered.sort(key=_price)
                elif sort_by == "Price ↓":
                    filtered.sort(key=lambda r: -_price(r))
                elif sort_by == "Departure time":
                    filtered.sort(key=_dep_t)
                elif sort_by == "Arrival time":
                    filtered.sort(key=_arr_t)

                d_cnt = sum(1 for r in filtered if r["_type"] == "direct")
                c_cnt = len(filtered) - d_cnt
                st.caption(
                    f"**{len(filtered)} result(s)** — {d_cnt} direct, {c_cnt} connection(s).  "
                    "Connection prices include a **15% group discount** (capped 10% below direct)."
                )

                if not filtered:
                    st.info("No results match the current filters.")
                else:
                    active = st.session_state.get("booking_card_idx")
                    for i, row in enumerate(filtered):
                        if row["_type"] == "direct":
                            with st.container(border=True):
                                _render_direct_card(i, row, dep, arr, user, active)
                        else:
                            with st.container(border=True):
                                _render_connection_card(i, row, dep, arr, user, active)

    # ── Tab 2: My Bookings ─────────────────────
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

        bks = st.session_state.get("my_bookings")
        if bks is None:
            st.caption("Click 'Load My Bookings' to see your confirmed bookings.")
        elif not bks:
            st.info("No active bookings found.")
        else:
            from collections import defaultdict
            groups: dict = defaultdict(list)
            for b in bks:
                key = b.get("itinerary_id") or b["booking_id"]
                groups[key].append(b)

            for gkey, legs in groups.items():
                with st.container(border=True):
                    if len(legs) == 1:
                        b = legs[0]
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                        with c1:
                            st.markdown(f"**{b['flight_number']}** — {b['airline_name']}")
                            st.markdown(f"{b['depart_airport_iata']} → {b['dest_airport_iata']}")
                        with c2:
                            st.caption(str(b['flight_date']))
                            st.markdown(f"Seat **{b['seat_number']}** — {b['class_name']}")
                        with c3:
                            st.markdown(f"**${float(b['price']):.2f}**")
                            st.caption((b.get('ticket_no') or '')[:18])
                        with c4:
                            if st.button("Cancel", key=f"cancel_{b['booking_id']}", type="secondary"):
                                try:
                                    res = supabase.rpc("cancel_booking",
                                                       {"p_booking_id": b["booking_id"]}).execute()
                                    st.success(str(res.data))
                                    st.session_state.pop("my_bookings", None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Cancellation failed: {e}")
                    else:
                        legs_s = sorted(legs, key=lambda l: str(l.get("depart_time", "")))
                        total  = sum(float(l["price"]) for l in legs_s)
                        itin_id = legs_s[0].get("itinerary_id")
                        route_s = " → ".join(
                            [legs_s[0]["depart_airport_iata"]]
                            + [l["dest_airport_iata"] for l in legs_s]
                        )
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                        with c1:
                            st.markdown("**Connection Itinerary**")
                            st.markdown(route_s)
                        with c2:
                            st.caption(str(legs_s[0]['flight_date']))
                            st.markdown("  ".join(f"Seat **{l['seat_number']}**" for l in legs_s))
                        with c3:
                            st.markdown(f"**${total:.2f}** total")
                            st.caption(" + ".join(l["flight_number"] for l in legs_s))
                        with c4:
                            if st.button("Cancel All", key=f"cancel_itin_{itin_id}", type="secondary"):
                                try:
                                    res = supabase.rpc("cancel_itinerary",
                                                       {"p_itinerary_id": itin_id}).execute()
                                    st.success(str(res.data))
                                    st.session_state.pop("my_bookings", None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Cancellation failed: {e}")

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

    tab_master, tab_flights, tab_revenue, tab_adv = st.tabs([
        "Master Data", "Flights", "Revenue Statistics", "Advanced Features"
    ])

    # ═══════════════════════════════════════════
    # TAB 1: Flights
    # ═══════════════════════════════════════════
    with tab_flights:

        # ── Create Schedules ─────────────────────
        with st.expander("Create Schedule"):
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

                if st.button("Create Schedule", key="btn_create"):
                    dep_iata = ap_opts[dep_lbl]
                    arr_iata = ap_opts[arr_lbl]

                    days_str = ",".join(days)
                    dept_str = str(dep_t)
                    arrt_str = str(arr_t)
                    vf_str = str(vf)
                    vu_str = str(vu)

                    existing_fn = supabase.table("FLIGHT_SCHEDULE") \
                        .select("flight_number") \
                        .eq("flight_number", fn.strip()) \
                        .limit(1) \
                        .execute().data

                    if dep_iata == arr_iata:
                        st.error("Departure and arrival must differ.")
                    elif existing_fn:
                        st.error(f"The flight number '{fn}' already exists.")
                    elif not days:
                        st.error("Select at least one operating day.")
                    elif not fn.strip():
                        st.error("Flight number is required.")
                    elif vf > vu:
                        st.error("Valid From must be ≤ Valid Until.")
                    else:
                        try:
                            supabase.table("FLIGHT_SCHEDULE").insert({
                                "aircraft_id":        ac_opts[sel_ac],
                                "depart_airport_iata": dep_iata,
                                "dest_airport_iata":   arr_iata,
                                "flight_number":       fn.strip(),
                                "depart_time":         dept_str,
                                "arrival_time":        arrt_str,
                                "days_of_week":        days_str,
                                "valid_from":          vf_str,
                                "valid_until":         vu_str,
                            }).execute()
                            st.success("Schedule created.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── View Existing Schedules ──────────────
        with st.expander("View Existing Schedules"):
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

            if not ac_opts and ap_opts:
                st.warning("Add aircraft and airports in Master Data first.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    dep_lbl = st.selectbox("Departure Airport", list(ap_opts.keys()), key="s_dep")
                with c2:
                    arr_lbl = st.selectbox("Arrival Airport",   list(ap_opts.keys()), key="s_arr")
                if st.button("Load Schedules", key="btn_vs"):
                    try:
                        rows = supabase.table("FLIGHT_SCHEDULE").select("*") \
                            .eq("depart_airport_iata", ap_opts[dep_lbl]) \
                            .eq("dest_airport_iata", ap_opts[arr_lbl]) \
                            .execute().data
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True)
                        else:
                            st.info("No schedules matches with the given parameter.")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ── Create Flights ───────────────────────
        with st.expander("Generate Flights"):
            try:
                all_schedules = supabase.table("FLIGHT_SCHEDULE") \
                    .select("schedule_id, flight_number, depart_airport_iata, "
                            "dest_airport_iata, depart_time, days_of_week, valid_from, valid_until") \
                    .execute().data
            except Exception as e:
                st.error(f"Failed to load schedules: {e}")
                all_schedules = []

            if not all_schedules:
                st.info("No schedules exist yet. Create one above first.")
            else:
                sched_opts = {
                    (f"{s['flight_number']} — {s['depart_airport_iata']}→{s['dest_airport_iata']}"
                     f" — {str(s['depart_time'])[:5]} — {s['days_of_week']}"): s["schedule_id"]
                    for s in all_schedules
                }
                sched_lbl = st.selectbox("Schedule", list(sched_opts.keys()), key="g_sched")
                schedule_id = sched_opts[sched_lbl]

                c1, c2 = st.columns(2)
                with c1:
                    gs = st.date_input("Generate Start", value=date.today(), key="f_gs")
                with c2:
                    ge = st.date_input("Generate End",   value=date.today(), key="f_ge")

                if st.button("Generate Flights", key="btn_gen"):
                    if gs > ge:
                        st.error("Generate Start must be ≤ Generate End.")
                    else:
                        try:
                            res = supabase.rpc("generate_flights", {
                                "p_sched_id":   schedule_id,
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
                        .select("schedule_id, flight_id,flight_number,airline_name,depart_airport_iata,dest_airport_iata,flight_date,depart_time,arrival_time,flight_status,class_name,available_seats") \
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
                st.session_state["revenue_rows"] = rows
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state["revenue_rows"] = []

        rows = st.session_state.get("revenue_rows")
        if rows is None:
            st.caption("Click the button to load the latest revenue report.")
        elif not rows:
            st.info("No revenue data available. Create some bookings first.")
        else:
            df = pd.DataFrame(rows)
            df["revenue_month"]   = pd.to_datetime(df["revenue_month"]).dt.strftime("%Y-%m")
            # Q labels like "2026-Q2" derived directly from month number — robust across pandas versions
            df["revenue_quarter"] = pd.to_datetime(df["revenue_quarter"]).apply(
                lambda d: f"{d.year}-Q{((d.month - 1) // 3) + 1}"
            )

            # ── Totals strip ────────────────────────────
            total_revenue  = float(df["total_revenue"].sum())
            unique_flights = int(df["flight_id"].nunique())
            unique_routes  = int(df["route"].nunique())
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Revenue (USD)", f"${total_revenue:,.2f}")
            m2.metric("Flights with Bookings", f"{unique_flights}")
            m3.metric("Routes Sold",            f"{unique_routes}")

            # ── Per-flight per-class breakdown ──────────
            st.write("**Revenue by Flight and Class**")
            disp_cols = [
                "flight_number", "airline_name", "route", "flight_date",
                "class_name", "total_revenue", "class_revenue_pct",
                "class_load_factor_pct", "flight_load_factor_pct",
            ]
            st.dataframe(
                df[[c for c in disp_cols if c in df.columns]],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "`class_revenue_pct` is the share of a flight's revenue from this class. "
                "`class_load_factor_pct` = bookings in this class / seats in this class. "
                "`flight_load_factor_pct` = bookings on this flight / total seats on the aircraft."
            )

            # ── Time-period roll-ups ────────────────────
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Revenue by Month**")
                monthly = df.groupby("revenue_month")["total_revenue"].sum().reset_index()
                st.bar_chart(monthly.set_index("revenue_month"))
            with c2:
                st.write("**Revenue by Quarter**")
                quarterly = df.groupby("revenue_quarter")["total_revenue"].sum().reset_index()
                st.bar_chart(quarterly.set_index("revenue_quarter"))

            # ── Route ranking & class breakdown ─────────
            st.write("**Revenue ranked by Route**")
            route_rev = (
                df.groupby("route")["total_revenue"].sum()
                  .sort_values(ascending=False).reset_index()
            )
            st.bar_chart(route_rev.set_index("route"))

            st.write("**Revenue by Seat Class**")
            class_rev = df.groupby("class_name")["total_revenue"].sum().reset_index()
            class_rev["share_pct"] = (class_rev["total_revenue"] /
                                     class_rev["total_revenue"].sum() * 100).round(2)
            st.dataframe(class_rev, use_container_width=True, hide_index=True)
            st.bar_chart(class_rev.set_index("class_name")["total_revenue"])

    # ═══════════════════════════════════════════
    # TAB 4: Advanced Features
    # ═══════════════════════════════════════════
    with tab_adv:
        st.subheader("Advanced Features")
        st.write(
            "This project incorporates **both** advanced features from the project brief:\n\n"
            "1. **Triggers & Stored Procedures** — 3 PL/pgSQL triggers and 5+ stored procedures.\n"
            "2. **Indexing & Query Optimization** — bulk data generator + EXPLAIN ANALYZE plans."
        )

        st.markdown("### Triggers & Stored Procedures")

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

            st.markdown("**Live Demo:** Set a flight to `'departed'` status, then attempt a booking — the trigger blocks it.")
            try:
                # Query ALL flights (not filtered by status) so the selected flight
                # stays in the dropdown after its status is changed to 'departed'.
                flights = supabase.table("FLIGHT") \
                    .select("flight_id, flight_date, status, FLIGHT_SCHEDULE(flight_number)") \
                    .in_("status", ["scheduled", "departed", "cancelled"]) \
                    .order("flight_date", desc=True).limit(30).execute().data
                flight_opts = {
                    f"{r.get('FLIGHT_SCHEDULE',{}).get('flight_number','?')} on {r['flight_date']} [{r['status']}]": r["flight_id"]
                    for r in flights
                }
            except Exception:
                flight_opts = {}

            if flight_opts:
                sel_f = st.selectbox("Select a flight for demo", list(flight_opts.keys()), key="d2_flt")
                # Pin the selected flight_id in session_state so status changes
                # on re-render don't silently swap it to a different flight.
                flt_id = flight_opts[sel_f]
                st.session_state["d2_locked_flt_id"] = flt_id

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Set to 'departed' (makes booking invalid)", key="btn_d2_set"):
                        try:
                            supabase.table("FLIGHT").update({"status": "departed"}) \
                                .eq("flight_id", flt_id).execute()
                            st.warning("Flight set to 'departed'. Now try booking below.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with c2:
                    if st.button("Reset to 'scheduled'", key="btn_d2_reset"):
                        try:
                            supabase.table("FLIGHT").update({"status": "scheduled"}) \
                                .eq("flight_id", flt_id).execute()
                            st.success("Flight reset to 'scheduled'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                locked_flt_id = st.session_state.get("d2_locked_flt_id", flt_id)
                if st.button("Attempt Booking (should be blocked by trigger)", key="btn_d2_book"):
                    try:
                        cust = supabase.table("CUSTOMER").select("customer_id") \
                            .eq("email", "bulk_test@demo.com").limit(1).execute().data
                        flt_ac = supabase.table("FLIGHT").select("aircraft_id, status") \
                            .eq("flight_id", locked_flt_id).limit(1).execute().data
                        seat = []
                        if flt_ac:
                            all_seats = supabase.table("SEAT_INVENTORY").select("seat_id") \
                                .eq("aircraft_id", flt_ac[0]["aircraft_id"]).execute().data
                            taken = {
                                r["seat_id"]
                                for r in supabase.table("BOOKING")
                                    .select("seat_id")
                                    .eq("flight_id", locked_flt_id)
                                    .neq("status", "cancelled")
                                    .execute().data
                            }
                            seat = [s for s in all_seats if s["seat_id"] not in taken][:1]
                        if cust and seat:
                            supabase.rpc("create_booking", {
                                "p_customer_id": cust[0]["customer_id"],
                                "p_flight_id":   locked_flt_id,
                                "p_seat_id":     seat[0]["seat_id"],
                                "p_amount":      100.0,
                            }).execute()
                            st.warning("Booking succeeded (flight was still 'scheduled').")
                    except Exception as e:
                        st.error(f"Trigger blocked the booking: {e}")
            else:
                st.info("No flights available for demo.")

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
| `generate_flights(sched_id, start, end)` | Generates individual `FLIGHT` rows from a `FLIGHT_SCHEDULE` for the given date range. Skips already-generated dates. |
| `search_flights(dep, arr, date, class)` | Returns available direct/pre-defined-stopover flights with seat counts and `effective_price` (15%/stop discount). |
| `search_connections(dep, arr, date, class)` | Finds dynamic A→hub→B itineraries by self-joining flights; prices = (leg1+leg2)×0.85, capped 10% below direct. |
| `create_booking(customer, flight, seat, amount)` | **Atomic**: INSERT BOOKING → INSERT PAYMENT → INSERT TICKET. Rolls back on any failure. |
| `create_itinerary_booking(customer, f1, seat1, amt1, f2, seat2, amt2)` | **Atomic two-leg**: books both legs under a shared `itinerary_id`; rolls back if either seat is taken. |
| `cancel_booking(booking_id)` | **Atomic**: DELETE TICKET → UPDATE BOOKING='cancelled' → UPDATE PAYMENT='refunded' → INSERT REFUND. |
| `cancel_itinerary(itinerary_id)` | **Atomic multi-leg**: cancels and refunds all legs sharing the itinerary_id. |
| `get_revenue_report()` | Aggregates revenue, class breakdown %, and dual load factors from `REVENUE_STATS_VIEW`. |
| `bulk_generate_test_bookings(N, seed)` | Loads N random confirmed bookings (with payment + ticket) for query-optimization testing. |
""")

        # ───────────────────────────────────────────
        # Indexing & Query Optimization
        # ───────────────────────────────────────────
        st.divider()
        st.markdown("### Indexing & Query Optimization")
        st.write(
            "PostgreSQL's planner exposes `EXPLAIN (ANALYZE, BUFFERS)` to "
            "inspect execution plans and timings. Below: scale the dataset "
            "with the bulk generator, then run each core query through "
            "EXPLAIN ANALYZE to verify index usage."
        )

        # ── Indexes catalog ────────────────────────
        with st.expander("Indexes defined in 01_schema.sql"):
            st.markdown("""
| Index | Table | Columns | Optimizes |
|---|---|---|---|
| `idx_flight_date` | `FLIGHT` | `flight_date` | Date-based flight search |
| `idx_flight_status` | `FLIGHT` | `status` | Filter active/cancelled flights |
| `idx_schedule_route` | `FLIGHT_SCHEDULE` | `(depart_airport_iata, dest_airport_iata)` | Route lookup |
| `idx_schedule_valid` | `FLIGHT_SCHEDULE` | `(valid_from, valid_until)` | Validity filter |
| `idx_booking_customer` | `BOOKING` | `customer_id` | My-Bookings page |
| `idx_booking_flight` | `BOOKING` | `flight_id` | Seat availability count |
| `idx_booking_status` | `BOOKING` | `status` | Confirmed/cancelled filter |
| `idx_seat_aircraft` | `SEAT_INVENTORY` | `aircraft_id` | Seat lookup per aircraft |
| `idx_seat_class` | `SEAT_INVENTORY` | `class_id` | Seat lookup per class |
| `idx_stopover_schedule` | `STOPOVER` | `schedule_id` | Stopover list lookup |
| `booking_active_seat_unique` | `BOOKING` | `(flight_id, seat_id) WHERE status != 'cancelled'` | Double-booking guard + lookup |
""")

        # ── Bulk Data Generator ────────────────────
        with st.expander("Bulk Generate Test Bookings (scale the dataset)"):
            st.markdown(
                "Calls `bulk_generate_test_bookings(N, seed)` which atomically "
                "inserts N random confirmed bookings (each with PAYMENT and TICKET). "
                "Generate flights first via the Flights tab so there are seats to book."
            )
            c1, c2 = st.columns(2)
            with c1:
                bulk_n = st.number_input("Number of bookings to create",
                                         min_value=1, max_value=50000, value=2000, key="bulk_n")
            with c2:
                bulk_seed = st.number_input("Random seed (reproducible)",
                                            min_value=0, max_value=999999, value=42, key="bulk_seed")
            if st.button("Run Bulk Generator", key="btn_bulk"):
                try:
                    res = supabase.rpc("bulk_generate_test_bookings", {
                        "p_count": int(bulk_n),
                        "p_seed":  int(bulk_seed),
                    }).execute()
                    st.success(str(res.data))
                    # Fetch the most recently inserted bookings to display
                    recent = supabase.table("BOOKING_VIEW") \
                        .select("flight_number,airline_name,depart_airport_iata,dest_airport_iata,flight_date,seat_number,class_name,price,booked_at") \
                        .eq("status", "confirmed") \
                        .order("booked_at", desc=True) \
                        .limit(int(bulk_n)) \
                        .execute().data
                    st.session_state["bulk_generated_rows"] = recent
                except Exception as e:
                    st.error(f"Bulk generator error: {e}")

            if st.session_state.get("bulk_generated_rows"):
                rows_df = pd.DataFrame(st.session_state["bulk_generated_rows"])
                rows_df = rows_df.rename(columns={
                    "flight_number": "Flight",
                    "airline_name": "Airline",
                    "depart_airport_iata": "From",
                    "dest_airport_iata": "To",
                    "flight_date": "Date",
                    "seat_number": "Seat",
                    "class_name": "Class",
                    "price": "Price (USD)",
                    "booked_at": "Booked At",
                })
                st.write(f"**{len(rows_df)} booking(s) shown (most recent first):**")
                st.dataframe(rows_df, use_container_width=True, height=300)

            st.divider()
            st.warning("**Clear All Bookings** — deletes every BOOKING, PAYMENT, TICKET, and REFUND row. Use only in demo/test environments.")
            if st.button("Clear All Bookings", key="btn_clear_bookings"):
                try:
                    supabase.table("TICKET").delete().neq("ticket_id", "00000000-0000-0000-0000-000000000000").execute()
                    supabase.table("REFUND").delete().neq("refund_id", "00000000-0000-0000-0000-000000000000").execute()
                    supabase.table("PAYMENT").delete().neq("payment_id", "00000000-0000-0000-0000-000000000000").execute()
                    supabase.table("BOOKING").delete().neq("booking_id", "00000000-0000-0000-0000-000000000000").execute()
                    st.success("All bookings, payments, tickets, and refunds have been cleared.")
                except Exception as e:
                    st.error(f"Clear failed: {e}")

            # Show current scale
            try:
                f_cnt = supabase.table("FLIGHT").select("flight_id", count="exact").execute()
                b_cnt = supabase.table("BOOKING").select("booking_id", count="exact").execute()
                si_cnt = supabase.table("SEAT_INVENTORY").select("seat_id", count="exact").execute()
                m1, m2, m3 = st.columns(3)
                m1.metric("FLIGHT rows", f"{getattr(f_cnt, 'count', 0):,}")
                m2.metric("BOOKING rows", f"{getattr(b_cnt, 'count', 0):,}")
                m3.metric("SEAT_INVENTORY rows", f"{getattr(si_cnt, 'count', 0):,}")
            except Exception:
                pass

        # ── EXPLAIN ANALYZE — search_flights ──────
        with st.expander("EXPLAIN ANALYZE — search_flights"):
            st.markdown(
                "Inspect the executor plan and per-node timings for the customer "
                "Flight Search query path."
            )
            try:
                airports = supabase.table("AIRPORT").select("iata_code, city").execute().data
            except Exception:
                airports = []
            ap_opts2 = {f"{a['iata_code']} - {a['city']}": a["iata_code"] for a in airports}

            if ap_opts2:
                c1, c2 = st.columns(2)
                with c1:
                    e_dep = st.selectbox("Departure", list(ap_opts2.keys()), key="e_dep")
                with c2:
                    e_arr = st.selectbox("Arrival",   list(ap_opts2.keys()), key="e_arr")
                c3, c4 = st.columns(2)
                with c3:
                    e_date = st.date_input("Travel Date", value=date.today(), key="e_date")
                with c4:
                    e_cls = st.selectbox("Seat Class",
                                          ["All", "First", "Business", "Economy"], key="e_cls")
                if st.button("Run EXPLAIN ANALYZE", key="btn_e_sf"):
                    try:
                        res = supabase.rpc("explain_search_flights", {
                            "p_dep_iata":    ap_opts2[e_dep],
                            "p_arr_iata":    ap_opts2[e_arr],
                            "p_travel_date": str(e_date),
                            "p_class_name":  None if e_cls == "All" else e_cls,
                        }).execute()
                        _render_explain_comparison(res.data)
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ── EXPLAIN ANALYZE — get_revenue_report ──
        with st.expander("EXPLAIN ANALYZE — get_revenue_report"):
            st.markdown(
                "Inspect the executor plan and per-node timings for the Revenue Statistics "
                "aggregation. After bulk-generating a few thousand bookings, look for "
                "sequential scans on `BOOKING` / `PAYMENT` that benefit from existing indexes."
            )
            if st.button("Run EXPLAIN ANALYZE", key="btn_e_rev"):
                try:
                    res = supabase.rpc("explain_revenue_report", {}).execute()
                    _render_explain_comparison(res.data)
                except Exception as e:
                    st.error(f"Error: {e}")


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
