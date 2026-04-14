-- ============================================================
-- AirBooking Sample Seed Data
-- Safe to run multiple times (idempotent style)
-- ============================================================

-- AIRLINE
INSERT INTO public."AIRLINE" (airline_id, iata_code, name, country)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'KE', 'Korean Air', 'Korea'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRLINE" WHERE iata_code = 'KE'
);

INSERT INTO public."AIRLINE" (airline_id, iata_code, name, country)
SELECT '22222222-2222-2222-2222-222222222222'::uuid, 'JL', 'Japan Airlines', 'Japan'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRLINE" WHERE iata_code = 'JL'
);

-- AIRPORT
INSERT INTO public."AIRPORT" (airport_id, iata_code, name, country, city)
SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1'::uuid, 'ICN', 'Incheon International Airport', 'Korea', 'Incheon'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRPORT" WHERE iata_code = 'ICN'
);

INSERT INTO public."AIRPORT" (airport_id, iata_code, name, country, city)
SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2'::uuid, 'NRT', 'Narita International Airport', 'Japan', 'Tokyo'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRPORT" WHERE iata_code = 'NRT'
);

INSERT INTO public."AIRPORT" (airport_id, iata_code, name, country, city)
SELECT 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3'::uuid, 'HND', 'Haneda Airport', 'Japan', 'Tokyo'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRPORT" WHERE iata_code = 'HND'
);

-- AIRCRAFT
INSERT INTO public."AIRCRAFT" (aircraft_id, model)
SELECT '33333333-3333-3333-3333-333333333331'::uuid, 'Boeing 777-300ER'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRCRAFT" WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid
);

INSERT INTO public."AIRCRAFT" (aircraft_id, model)
SELECT '33333333-3333-3333-3333-333333333332'::uuid, 'Airbus A321neo'
WHERE NOT EXISTS (
  SELECT 1 FROM public."AIRCRAFT" WHERE aircraft_id = '33333333-3333-3333-3333-333333333332'::uuid
);

-- SEAT_CLASS (for first aircraft)
INSERT INTO public."SEAT_CLASS" (class_id, class_name, aircraft_id, seat_count, price)
SELECT '44444444-4444-4444-4444-444444444401'::uuid, 'First',    '33333333-3333-3333-3333-333333333331'::uuid, 4, 1200
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_CLASS"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid
    AND class_name = 'First'
);

INSERT INTO public."SEAT_CLASS" (class_id, class_name, aircraft_id, seat_count, price)
SELECT '44444444-4444-4444-4444-444444444402'::uuid, 'Business', '33333333-3333-3333-3333-333333333331'::uuid, 8, 700
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_CLASS"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid
    AND class_name = 'Business'
);

INSERT INTO public."SEAT_CLASS" (class_id, class_name, aircraft_id, seat_count, price)
SELECT '44444444-4444-4444-4444-444444444403'::uuid, 'Economy',  '33333333-3333-3333-3333-333333333331'::uuid, 24, 220
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_CLASS"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid
    AND class_name = 'Economy'
);

-- SEAT_INVENTORY (small sample per class, enough for booking demo)
INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555501'::uuid, '44444444-4444-4444-4444-444444444401'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '1A'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '1A'
);

INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555502'::uuid, '44444444-4444-4444-4444-444444444401'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '1B'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '1B'
);

INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555503'::uuid, '44444444-4444-4444-4444-444444444402'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '3A'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '3A'
);

INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555504'::uuid, '44444444-4444-4444-4444-444444444402'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '3B'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '3B'
);

INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555505'::uuid, '44444444-4444-4444-4444-444444444403'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '20A'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '20A'
);

INSERT INTO public."SEAT_INVENTORY" (seat_id, class_id, aircraft_id, seat_number)
SELECT '55555555-5555-5555-5555-555555555506'::uuid, '44444444-4444-4444-4444-444444444403'::uuid, '33333333-3333-3333-3333-333333333331'::uuid, '20B'
WHERE NOT EXISTS (
  SELECT 1 FROM public."SEAT_INVENTORY"
  WHERE aircraft_id = '33333333-3333-3333-3333-333333333331'::uuid AND seat_number = '20B'
);

-- CUSTOMER (bcrypt hash placeholder from sample projects)
INSERT INTO public."CUSTOMER" (customer_id, email, password, name, passport)
SELECT
  '66666666-6666-6666-6666-666666666661'::uuid,
  'alice@example.com',
  '$2b$12$9f8QJ3J6m8kV2P9s2Qb5KeU4NZGNvJ1m3NQY7rZjj7w0sW9mH5GzK',
  'Alice Kim',
  'M12345678'
WHERE NOT EXISTS (
  SELECT 1 FROM public."CUSTOMER" WHERE email = 'alice@example.com'
);

INSERT INTO public."CUSTOMER" (customer_id, email, password, name, passport)
SELECT
  '66666666-6666-6666-6666-666666666662'::uuid,
  'bob@example.com',
  '$2b$12$9f8QJ3J6m8kV2P9s2Qb5KeU4NZGNvJ1m3NQY7rZjj7w0sW9mH5GzK',
  'Bob Sato',
  'N98765432'
WHERE NOT EXISTS (
  SELECT 1 FROM public."CUSTOMER" WHERE email = 'bob@example.com'
);

-- STAFF
INSERT INTO public."STAFF" (staff_id, email, password, name, role)
SELECT
  '77777777-7777-7777-7777-777777777771'::uuid,
  'admin@airbooking.local',
  '$2b$12$9f8QJ3J6m8kV2P9s2Qb5KeU4NZGNvJ1m3NQY7rZjj7w0sW9mH5GzK',
  'System Admin',
  'admin'
WHERE NOT EXISTS (
  SELECT 1 FROM public."STAFF" WHERE email = 'admin@airbooking.local'
);
