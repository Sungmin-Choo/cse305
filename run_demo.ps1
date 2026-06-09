python generate_airline_network_seed.py --reset --reset-schedules --one-per-month --with-bookings &&
python seed_from_csv.py --with-flights --with-history 5000 &&
streamlit run app.py
