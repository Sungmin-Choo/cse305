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
-- AIRPORTS — those needed for demo schedules
-- (CSV airports added later by seed_from_csv.py via ON CONFLICT DO NOTHING)
-- ============================================================
INSERT INTO public."AIRPORT" (iata_code, name, country, city)
VALUES
  ('ICN', 'Incheon International Airport',        'South Korea',          'Seoul'),
  ('DXB', 'Dubai International Airport',          'United Arab Emirates', 'Dubai'),
  ('LHR', 'London Heathrow Airport',              'United Kingdom',       'London'),
  ('SFO', 'San Francisco International Airport',  'United States',        'San Francisco'),
  ('SEA', 'Seattle-Tacoma International Airport', 'United States',        'Seattle'),
  ('YVR', 'Vancouver International Airport',      'Canada',               'Vancouver'),
  ('NRT', 'Narita International Airport',         'Japan',                'Tokyo'),
  ('LAX', 'Los Angeles International Airport',    'United States',        'Los Angeles')
ON CONFLICT (iata_code) DO NOTHING;


-- ============================================================
-- AIRLINES — those used by the demo schedules
-- (CSV carriers added later by seed_from_csv.py)
-- ============================================================
INSERT INTO public."AIRLINE" (iata_code, name, country)
VALUES
  ('EK', 'Emirates',        'United Arab Emirates'),
  ('BA', 'British Airways', 'United Kingdom'),
  ('KE', 'Korean Air',      'South Korea')
ON CONFLICT (iata_code) DO NOTHING;


-- ============================================================
-- AIRCRAFT
-- EK 777-300ER   : medium-haul legs for dynamic connections (Economy $450)
-- EK A380-800    : premium direct long-haul (Economy $1000)
-- BA 777-300ER   : BA demo routes (Economy $450)
-- KE 787-9       : medium-haul legs for ICN→NRT / NRT→LAX (Economy $380)
-- KE A380-800    : premium direct ICN→LAX (Economy $950)
-- ============================================================
INSERT INTO public."AIRCRAFT" (airline_id, model)
SELECT al.airline_id, v.model
FROM (VALUES
  ('EK', 'Boeing 777-300ER'),
  ('EK', 'Airbus A380-800'),
  ('BA', 'Boeing 777-300ER'),
  ('KE', 'Boeing 787-9 Dreamliner'),
  ('KE', 'Airbus A380-800')
) AS v(iata, model)
JOIN public."AIRLINE" al ON al.iata_code = v.iata
ON CONFLICT DO NOTHING;


-- ============================================================
-- SEAT_CLASS — 3 classes per demo aircraft
-- Trigger trg_auto_generate_seats auto-populates SEAT_INVENTORY.
--
-- Pricing intent:
--   EK / BA B777-300ER: Economy $450  → connection ICN→LHR via DXB = $765
--   EK A380-800:        Economy $1000 → direct ICN→LHR (premium)
--   KE B787-9:          Economy $380  → connection ICN→LAX via NRT = $646
--   KE A380-800:        Economy $950  → direct ICN→LAX (premium)
-- Both connections are cheaper than their direct counterparts.
-- ============================================================

-- EK Boeing 777-300ER (connection legs)
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT cls, ac.aircraft_id, cnt, price
FROM (VALUES ('First', 2, 1800.00), ('Business', 6, 1000.00), ('Economy', 24, 450.00)) AS t(cls, cnt, price)
JOIN public."AIRCRAFT" ac ON ac.model = 'Boeing 777-300ER'
JOIN public."AIRLINE"  al ON al.airline_id = ac.airline_id AND al.iata_code = 'EK'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

-- EK Airbus A380-800 (premium direct)
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT cls, ac.aircraft_id, cnt, price
FROM (VALUES ('First', 4, 3500.00), ('Business', 8, 2000.00), ('Economy', 30, 1000.00)) AS t(cls, cnt, price)
JOIN public."AIRCRAFT" ac ON ac.model = 'Airbus A380-800'
JOIN public."AIRLINE"  al ON al.airline_id = ac.airline_id AND al.iata_code = 'EK'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

-- BA Boeing 777-300ER (stopover demo)
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT cls, ac.aircraft_id, cnt, price
FROM (VALUES ('First', 2, 1800.00), ('Business', 6, 1000.00), ('Economy', 24, 450.00)) AS t(cls, cnt, price)
JOIN public."AIRCRAFT" ac ON ac.model = 'Boeing 777-300ER'
JOIN public."AIRLINE"  al ON al.airline_id = ac.airline_id AND al.iata_code = 'BA'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

-- KE Boeing 787-9 Dreamliner (connection legs)
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT cls, ac.aircraft_id, cnt, price
FROM (VALUES ('First', 2, 1500.00), ('Business', 4, 800.00), ('Economy', 18, 380.00)) AS t(cls, cnt, price)
JOIN public."AIRCRAFT" ac ON ac.model = 'Boeing 787-9 Dreamliner'
JOIN public."AIRLINE"  al ON al.airline_id = ac.airline_id AND al.iata_code = 'KE'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;

-- KE Airbus A380-800 (premium direct)
INSERT INTO public."SEAT_CLASS" (class_name, aircraft_id, seat_count, price)
SELECT cls, ac.aircraft_id, cnt, price
FROM (VALUES ('First', 4, 3200.00), ('Business', 8, 1800.00), ('Economy', 30, 950.00)) AS t(cls, cnt, price)
JOIN public."AIRCRAFT" ac ON ac.model = 'Airbus A380-800'
JOIN public."AIRLINE"  al ON al.airline_id = ac.airline_id AND al.iata_code = 'KE'
ON CONFLICT (aircraft_id, class_name) DO NOTHING;


-- ============================================================
-- FLIGHT_SCHEDULE
-- ── Stopover demo (schema completeness, pre-defined multi-leg)
-- ── Single-leg pairs for dynamic connection demo
-- ── Premium direct routes (so connections are demonstrably cheaper)
-- ============================================================

-- EK350 — Emirates ICN → DXB → LHR (1-stop pre-defined stopover; 15% discount)
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

-- BA284 — British Airways LHR → SFO → SEA → YVR (2-stop pre-defined stopover; 30% discount)
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

-- ── Dynamic connection demo set 1: ICN → LHR via DXB ──────────────────────
-- Leg 1: EK101 ICN→DXB (depart 10:00, arrive 17:00)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'ICN', 'DXB', 'EK101',
  '10:00', '17:00', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'EK' AND ac.model = 'Boeing 777-300ER'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Leg 2: EK201 DXB→LHR (depart 19:30, arrive 22:30) — 2.5 h layover after EK101
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'DXB', 'LHR', 'EK201',
  '19:30', '22:30', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'EK' AND ac.model = 'Boeing 777-300ER'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Premium direct: EK601 ICN→LHR (on A380-800, Economy $1000 — more expensive than connection $765)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'ICN', 'LHR', 'EK601',
  '14:00', '20:00', 'Mon,Wed,Fri', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'EK' AND ac.model = 'Airbus A380-800'
LIMIT 1
ON CONFLICT DO NOTHING;

-- ── Dynamic connection demo set 2: ICN → LAX via NRT ──────────────────────
-- Leg 1: KE101 ICN→NRT (depart 09:00, arrive 11:30)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'ICN', 'NRT', 'KE101',
  '09:00', '11:30', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'KE' AND ac.model = 'Boeing 787-9 Dreamliner'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Leg 2: KE202 NRT→LAX (depart 14:00, arrive 08:00+1 → stored as 08:00, overnight) — 2.5 h layover
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'NRT', 'LAX', 'KE202',
  '14:00', '08:00', 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'KE' AND ac.model = 'Boeing 787-9 Dreamliner'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Premium direct: KE017 ICN→LAX (on A380-800, Economy $950 — more expensive than connection $646)
INSERT INTO public."FLIGHT_SCHEDULE"
  (aircraft_id, depart_airport_iata, dest_airport_iata,
   flight_number, depart_time, arrival_time, days_of_week, valid_from, valid_until)
SELECT ac.aircraft_id, 'ICN', 'LAX', 'KE017',
  '11:00', '07:00', 'Mon,Wed,Fri', '2026-06-01', '2026-12-31'
FROM public."AIRCRAFT" ac
JOIN public."AIRLINE" al ON al.airline_id = ac.airline_id
WHERE al.iata_code = 'KE' AND ac.model = 'Airbus A380-800'
LIMIT 1
ON CONFLICT DO NOTHING;


-- ============================================================
-- STOPOVER — EK350 and BA284 stopover entries (schema demo)
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
-- CUSTOMERS (3 demo + 1 bulk-data sink)
-- ============================================================
INSERT INTO public."CUSTOMER" (email, password, name, passport)
VALUES
  ('alice@example.com',   '1234', 'Alice Kim',      'M12345678'),
  ('bob@example.com',     '1234', 'Bob Johnson',    'N98765432'),
  ('charlie@example.com', '1234', 'Charlie Lee',    'P55512345'),
  ('bulk_test@demo.com',  '1234', 'Bulk Test User', 'X00000000')
ON CONFLICT (email) DO NOTHING;


-- ============================================================
-- STAFF (1)
-- ============================================================
INSERT INTO public."STAFF" (email, password, name, role)
VALUES
  ('admin@airbooking.local', '1234', 'System Admin', 'admin')
ON CONFLICT (email) DO NOTHING;


-- ============================================================
-- GENERATE DEMO FLIGHTS for the next 60 days
-- Calls generate_flights() for every demo schedule so bookings
-- can be made immediately after seeding (no manual staff step).
-- ============================================================
DO $$
DECLARE
  v_sched_id uuid;
  v_fn       varchar;
BEGIN
  FOR v_sched_id, v_fn IN
    SELECT schedule_id, flight_number
    FROM public."FLIGHT_SCHEDULE"
    WHERE flight_number IN ('EK350','BA284','EK101','EK201','EK601','KE101','KE202','KE017')
  LOOP
    BEGIN
      PERFORM generate_flights(v_sched_id, CURRENT_DATE, CURRENT_DATE + interval '60 days');
    EXCEPTION WHEN OTHERS THEN
      -- Non-fatal: schedule may already have flights
      RAISE NOTICE 'generate_flights skipped for %: %', v_fn, SQLERRM;
    END;
  END LOOP;
END;
$$;


-- ============================================================
-- VERIFICATION QUERIES (run manually to confirm)
-- ============================================================
-- SELECT iata_code FROM public."AIRPORT";          -- 8 rows (more after ETL)
-- SELECT iata_code FROM public."AIRLINE";          -- 3 rows (more after ETL)
-- SELECT COUNT(*) FROM public."AIRCRAFT";          -- 5 rows (more after ETL)
-- SELECT COUNT(*) FROM public."SEAT_CLASS";        -- 15 rows (trigger-generated seats follow)
-- SELECT COUNT(*) FROM public."SEAT_INVENTORY";    -- (2+6+24)*2 + (2+4+18)*1 + (4+8+30)*2 = 252 seats
-- SELECT flight_number FROM public."FLIGHT_SCHEDULE"; -- EK350, BA284, EK101, EK201, EK601, KE101, KE202, KE017
-- SELECT airport_iata, stop_order FROM public."STOPOVER"; -- 3 rows
-- SELECT COUNT(*) FROM public."FLIGHT";            -- demo flights for next 60 days
-- SELECT email, name FROM public."CUSTOMER";       -- 4 rows (3 demo + bulk_test)
-- SELECT email, name, role FROM public."STAFF";    -- 1 row
