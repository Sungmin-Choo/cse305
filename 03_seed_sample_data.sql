-- ============================================================
-- Airline Reservation System (AirBooking)
-- CSE 305 Term Project — Seed Data (Accounts + Stopover Demo)
-- ============================================================
-- Execute AFTER: 01_schema.sql → 02_functions.sql → this file → 04_grants.sql
-- Then run:      python seed_from_csv.py   (loads nycflights13 CSV data)
--
-- This file seeds ONLY:
--   1. Demo user accounts (CUSTOMER × 3, STAFF × 1)
--   2. Two stopover demo schedules (EK350 1-stop, BA284 2-stop) + their
--      airports, airlines, aircraft, and seat classes — so the stopover
--      discount feature remains demonstrable even though the CSV dataset
--      contains no stopover routes.
--
-- Demo credentials:
--   Customer : alice@example.com    / 1234
--   Customer : bob@example.com      / 1234
--   Customer : charlie@example.com  / 1234
--   Staff    : admin@airbooking.local / 1234
-- ============================================================


-- ============================================================
-- AIRPORTS — only those needed for the stopover demo schedules
-- (CSV airports such as JFK, ATL, SFO, SEA are added by seed_from_csv.py)
-- ============================================================
INSERT INTO public."AIRPORT" (iata_code, name, country, city)
VALUES
  ('ICN', 'Incheon International Airport',       'South Korea',          'Seoul'),
  ('DXB', 'Dubai International Airport',         'United Arab Emirates', 'Dubai'),
  ('LHR', 'London Heathrow Airport',             'United Kingdom',       'London'),
  ('SFO', 'San Francisco International Airport', 'United States',        'San Francisco'),
  ('SEA', 'Seattle-Tacoma International Airport','United States',        'Seattle'),
  ('YVR', 'Vancouver International Airport',     'Canada',               'Vancouver')
ON CONFLICT (iata_code) DO NOTHING;


-- ============================================================
-- AIRLINES — only those used by the demo stopover schedules
-- (CSV carriers such as AA, DL, UA, B6, WN, etc. are added by seed_from_csv.py)
-- ============================================================
INSERT INTO public."AIRLINE" (iata_code, name, country)
VALUES
  ('EK', 'Emirates',         'United Arab Emirates'),
  ('BA', 'British Airways',  'United Kingdom')
ON CONFLICT (iata_code) DO NOTHING;


-- ============================================================
-- AIRCRAFT — one per airline for the demo schedules
-- ============================================================
INSERT INTO public."AIRCRAFT" (airline_id, model)
SELECT al.airline_id, v.model
FROM (VALUES
  ('EK', 'Boeing 777-300ER'),
  ('BA', 'Boeing 777-300ER')
) AS v(iata, model)
JOIN public."AIRLINE" al ON al.iata_code = v.iata
ON CONFLICT DO NOTHING;


-- ============================================================
-- SEAT_CLASS — 3 classes for each demo aircraft
-- The trigger trg_auto_generate_seats auto-populates SEAT_INVENTORY.
-- ============================================================
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT 'First',    ac.aircraft_id, 2, 1800.00
FROM public."AIRCRAFT" ac
WHERE ac.model = 'Boeing 777-300ER'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT 'Business', ac.aircraft_id, 6, 1000.00
FROM public."AIRCRAFT" ac
WHERE ac.model = 'Boeing 777-300ER'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT 'Economy',  ac.aircraft_id, 24, 450.00
FROM public."AIRCRAFT" ac
WHERE ac.model = 'Boeing 777-300ER'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;


-- ============================================================
-- FLIGHT_SCHEDULE — two demo stopover routes
-- These are kept here (not in the CSV ETL) because the CSV dataset
-- contains only US-domestic direct flights.
-- ============================================================

-- EK350 — Emirates ICN → DXB → LHR (1 stop: 15% discount demo)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'ICN', 'LHR', 'EK350',
  '23:55', '17:00', 'Mon,Wed,Fri,Sun', '2026-05-30', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'EK' AND ac.model = 'Boeing 777-300ER'
LIMIT 1
ON CONFLICT DO NOTHING;

-- BA284 — British Airways LHR → SFO → SEA → YVR (2 stops: 30% discount demo)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'LHR', 'YVR', 'BA284',
  '15:00', '11:30', 'Tue,Thu,Sat', '2026-05-30', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'BA' AND ac.model = 'Boeing 777-300ER'
LIMIT 1
ON CONFLICT DO NOTHING;


-- ============================================================
-- STOPOVER — EK350 and BA284 stopover entries
-- ============================================================

-- EK350: stop at DXB (+10h arrive, +12h depart)
INSERT INTO public."STOPOVER" (schedule_id, airport_iata, arrival_time_offset, departure_time_offset, stop_order)
SELECT schedule_id, 'DXB', interval '10 hours', interval '12 hours', 1
FROM public."FLIGHT_SCHEDULE" WHERE flight_number = 'EK350'
ON CONFLICT (schedule_id, stop_order) DO NOTHING;

-- BA284: stop 1 at SFO, stop 2 at SEA
INSERT INTO public."STOPOVER" (schedule_id, airport_iata, arrival_time_offset, departure_time_offset, stop_order)
SELECT schedule_id, 'SFO', interval '10 hours', interval '12 hours', 1
FROM public."FLIGHT_SCHEDULE" WHERE flight_number = 'BA284'
ON CONFLICT (schedule_id, stop_order) DO NOTHING;

INSERT INTO public."STOPOVER" (schedule_id, airport_iata, arrival_time_offset, departure_time_offset, stop_order)
SELECT schedule_id, 'SEA', interval '14 hours', interval '16 hours', 2
FROM public."FLIGHT_SCHEDULE" WHERE flight_number = 'BA284'
ON CONFLICT (schedule_id, stop_order) DO NOTHING;


-- ============================================================
-- CUSTOMERS (3)
-- ============================================================
INSERT INTO public."CUSTOMER" (email, password, name, passport)
VALUES
  ('alice@example.com',   '1234', 'Alice Kim',   'M12345678'),
  ('bob@example.com',     '1234', 'Bob Johnson', 'N98765432'),
  ('charlie@example.com', '1234', 'Charlie Lee', 'P55512345')
ON CONFLICT (email) DO NOTHING;


-- ============================================================
-- STAFF (1)
-- ============================================================
INSERT INTO public."STAFF" (email, password, name, role)
VALUES
  ('admin@airbooking.local', '1234', 'System Admin', 'admin')
ON CONFLICT (email) DO NOTHING;


-- ============================================================
-- VERIFICATION QUERIES (run manually to confirm)
-- ============================================================
-- SELECT iata_code FROM public."AIRPORT";          -- 6 rows (more after ETL)
-- SELECT iata_code FROM public."AIRLINE";          -- 2 rows (more after ETL)
-- SELECT COUNT(*) FROM public."AIRCRAFT";          -- 2 rows (more after ETL)
-- SELECT COUNT(*) FROM public."SEAT_CLASS";        -- 6 rows (trigger-generated seats follow)
-- SELECT COUNT(*) FROM public."SEAT_INVENTORY";    -- 64 rows (2×32 seats per B777)
-- SELECT flight_number FROM public."FLIGHT_SCHEDULE"; -- EK350, BA284
-- SELECT airport_iata, stop_order FROM public."STOPOVER"; -- 3 rows
-- SELECT email, name FROM public."CUSTOMER";       -- 3 rows
-- SELECT email, name, role FROM public."STAFF";    -- 1 row
