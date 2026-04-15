-- ============================================================
-- University Airline Reservation System
-- CSE 305 Term Project - Optimized PostgreSQL Schema
-- ============================================================

-- ============================================================
-- STEP 1. CREATE TABLES
-- ============================================================

-- AIRLINE
CREATE TABLE public."AIRLINE" (
  airline_id  uuid       NOT NULL DEFAULT gen_random_uuid(),
  iata_code   varchar(3) NOT NULL,
  name        varchar    NOT NULL,
  country     varchar    NULL,
  CONSTRAINT AIRLINE_pkey          PRIMARY KEY (airline_id),
  CONSTRAINT AIRLINE_iata_code_key UNIQUE (iata_code)
);

-- AIRPORT
CREATE TABLE public."AIRPORT" (
  airport_id  uuid       NOT NULL DEFAULT gen_random_uuid(),
  iata_code   varchar(3) NOT NULL,
  name        varchar    NOT NULL,
  country     varchar    NOT NULL,
  city        varchar    NOT NULL,
  CONSTRAINT AIRPORT_pkey          PRIMARY KEY (airport_id),
  CONSTRAINT AIRPORT_iata_code_key UNIQUE (iata_code),
  CONSTRAINT AIRPORT_name_key      UNIQUE (name)
);

-- AIRCRAFT
CREATE TABLE public."AIRCRAFT" (
  aircraft_id  uuid     NOT NULL DEFAULT gen_random_uuid(),
  airline_id   uuid     NOT NULL,
  model        varchar  NOT NULL,
  CONSTRAINT AIRCRAFT_pkey PRIMARY KEY (aircraft_id)
  CONSTRAINT AIRCRAFT_airline_fkey FOREIGN KEY (airline_id)
    REFERENCES public."AIRLINE" (airline_id)
);

-- CUSTOMER
CREATE TABLE public."CUSTOMER" (
  customer_id  uuid    NOT NULL DEFAULT gen_random_uuid(),
  email        varchar NOT NULL,
  password     varchar NOT NULL,
  name         varchar NOT NULL,
  passport     varchar NULL,
  CONSTRAINT CUSTOMER_pkey      PRIMARY KEY (customer_id),
  CONSTRAINT CUSTOMER_email_key UNIQUE (email)
);

-- STAFF
CREATE TABLE public."STAFF" (
  staff_id  uuid    NOT NULL DEFAULT gen_random_uuid(),
  email     varchar NOT NULL,
  password  varchar NOT NULL,
  name      varchar NOT NULL,
  role      varchar NOT NULL DEFAULT 'agent',
  CONSTRAINT STAFF_pkey       PRIMARY KEY (staff_id),
  CONSTRAINT STAFF_email_key  UNIQUE (email),
  CONSTRAINT STAFF_role_check CHECK (role IN ('admin', 'agent', 'manager'))
);

-- Seat Class
CREATE TABLE public."SEAT_CLASS" (
  class_id    uuid     NOT NULL DEFAULT gen_random_uuid(),
  class_name  varchar  NOT NULL,            -- Seat class name
  aircraft_id uuid     NOT NULL,            -- Associated aircraft
  seat_count  smallint NOT NULL,            -- Number of seats for this class
  price       numeric  NOT NULL,            -- Base price (NULL → NOT NULL enforcement)
  CONSTRAINT SEAT_CLASS_pkey              PRIMARY KEY (class_id),
  -- Only 3 seat classes allowed
  CONSTRAINT SEAT_CLASS_class_name_check  CHECK (class_name IN ('First', 'Business', 'Economy')),
  -- Seat count must be positive
  CONSTRAINT SEAT_CLASS_seat_count_check  CHECK (seat_count > 0),
  -- Price must be >= 0
  CONSTRAINT SEAT_CLASS_price_check       CHECK (price >= 0),
  -- Same class should not be duplicated on same aircraft
  CONSTRAINT SEAT_CLASS_unique            UNIQUE (aircraft_id, class_name),
  CONSTRAINT SEAT_CLASS_aircraft_fkey     FOREIGN KEY (aircraft_id)
    REFERENCES public."AIRCRAFT" (aircraft_id) ON DELETE CASCADE
);

-- Seat Inventory Table (Individual seats by aircraft)
CREATE TABLE public."SEAT_INVENTORY" (
  seat_id     uuid    NOT NULL DEFAULT gen_random_uuid(),
  class_id    uuid    NOT NULL,             -- Associated seat class
  aircraft_id uuid    NOT NULL,             -- Associated aircraft
  seat_number varchar NOT NULL,             -- Seat number (e.g. 1A, 12C)
  CONSTRAINT SEAT_INVENTORY_pkey          PRIMARY KEY (seat_id),
  CONSTRAINT SEAT_INVENTORY_class_fkey    FOREIGN KEY (class_id)
    REFERENCES public."SEAT_CLASS" (class_id) ON DELETE CASCADE,
  CONSTRAINT SEAT_INVENTORY_aircraft_fkey FOREIGN KEY (aircraft_id)
    REFERENCES public."AIRCRAFT" (aircraft_id) ON DELETE CASCADE,
  -- Same seat number should not be duplicated on same aircraft
  CONSTRAINT SEAT_INVENTORY_unique        UNIQUE (aircraft_id, seat_number)
);

-- Regular Flight Schedule Table
CREATE TABLE public."FLIGHT_SCHEDULE" (
  schedule_id         uuid       NOT NULL DEFAULT gen_random_uuid(),
  aircraft_id         uuid       NULL,      -- Default assigned aircraft (schedule level)
  depart_airport_iata varchar(3) NOT NULL,  -- Departure airport (NULL → NOT NULL)
  dest_airport_iata   varchar(3) NOT NULL,  -- Destination airport (NULL → NOT NULL)
  flight_number       varchar    NOT NULL,  -- Flight number (e.g. KE001) (NULL → NOT NULL)
  depart_time         time       NOT NULL,  -- Departure time
  arrival_time        time       NOT NULL,  -- Arrival time
  days_of_week        varchar    NOT NULL,  -- Operating days (e.g. 'Mon,Wed,Fri')
  valid_from          date       NOT NULL,  -- Schedule validity start date
  valid_until         date       NOT NULL,  -- Schedule validity end date
  CONSTRAINT FLIGHT_SCHEDULE_pkey          PRIMARY KEY (schedule_id),
  -- Valid start date must be earlier than or equal to end date
  CONSTRAINT FLIGHT_SCHEDULE_date_check    CHECK (valid_from <= valid_until),
  -- Departure and destination airports must not be the same
  CONSTRAINT FLIGHT_SCHEDULE_route_check   CHECK (depart_airport_iata != dest_airport_iata),
  CONSTRAINT FLIGHT_SCHEDULE_aircraft_fkey FOREIGN KEY (aircraft_id)
    REFERENCES public."AIRCRAFT" (aircraft_id),
  CONSTRAINT FLIGHT_SCHEDULE_depart_fkey   FOREIGN KEY (depart_airport_iata)
    REFERENCES public."AIRPORT" (iata_code),
  CONSTRAINT FLIGHT_SCHEDULE_dest_fkey     FOREIGN KEY (dest_airport_iata)
    REFERENCES public."AIRPORT" (iata_code)
);

-- Individual Flight Table (Created from schedule)
CREATE TABLE public."FLIGHT" (
  flight_id    uuid        NOT NULL DEFAULT gen_random_uuid(),
  schedule_id  uuid        NOT NULL,        -- Source schedule
  aircraft_id  uuid        NOT NULL,        -- Assigned aircraft
  flight_date  date        NOT NULL,        -- Flight date
  depart_time  timestamptz NOT NULL,        -- Departure datetime
  arrival_time timestamptz NOT NULL,        -- Arrival datetime
  status       varchar     NOT NULL DEFAULT 'scheduled',
  CONSTRAINT FLIGHT_pkey           PRIMARY KEY (flight_id),
  -- Flight status must be a predefined value
  CONSTRAINT FLIGHT_status_check   CHECK (status IN ('scheduled', 'departed', 'arrived', 'cancelled')),
  -- Departure time must be earlier than arrival time
  CONSTRAINT FLIGHT_time_check     CHECK (depart_time < arrival_time),
  CONSTRAINT FLIGHT_schedule_fkey  FOREIGN KEY (schedule_id)
    REFERENCES public."FLIGHT_SCHEDULE" (schedule_id),
  CONSTRAINT FLIGHT_aircraft_fkey  FOREIGN KEY (aircraft_id)
    REFERENCES public."AIRCRAFT" (aircraft_id),
  -- Only one flight per schedule on the same date
  CONSTRAINT FLIGHT_unique         UNIQUE (schedule_id, flight_date)
);

-- Booking Table
CREATE TABLE public."BOOKING" (
  booking_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
  flight_id   uuid        NOT NULL,         -- Booked flight
  customer_id uuid        NOT NULL,         -- Booking customer
  seat_id     uuid        NOT NULL,         -- Selected seat
  booked_at   timestamptz NOT NULL DEFAULT now(),
  status      varchar     NOT NULL DEFAULT 'confirmed',
  price       numeric     NOT NULL,         -- Booking amount
  CONSTRAINT BOOKING_pkey           PRIMARY KEY (booking_id),
  -- Booking status must be a predefined value
  CONSTRAINT BOOKING_status_check   CHECK (status IN ('confirmed', 'cancelled')),
  -- Price must be >= 0
  CONSTRAINT BOOKING_price_check    CHECK (price >= 0),
  CONSTRAINT BOOKING_flight_fkey    FOREIGN KEY (flight_id)
    REFERENCES public."FLIGHT" (flight_id),
  CONSTRAINT BOOKING_customer_fkey  FOREIGN KEY (customer_id)
    REFERENCES public."CUSTOMER" (customer_id),
  CONSTRAINT BOOKING_seat_fkey      FOREIGN KEY (seat_id)
    REFERENCES public."SEAT_INVENTORY" (seat_id)
);

-- Prevent duplicate seats for active bookings (excluding cancelled bookings)
CREATE UNIQUE INDEX booking_active_seat_unique
  ON public."BOOKING" (flight_id, seat_id)
  WHERE status != 'cancelled';

-- Payment Table
CREATE TABLE public."PAYMENT" (
  payment_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
  booking_id  uuid        NOT NULL,         -- Associated booking
  amount      numeric     NOT NULL,         -- Payment amount
  method      varchar     NOT NULL DEFAULT 'credit_card', -- Payment method
  status      varchar     NOT NULL DEFAULT 'completed',
  paid_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT PAYMENT_pkey          PRIMARY KEY (payment_id),
  -- Payment status must be a predefined value
  CONSTRAINT PAYMENT_status_check  CHECK (status IN ('completed', 'refunded', 'failed')),
  -- Payment method must be a predefined value
  CONSTRAINT PAYMENT_method_check  CHECK (method IN ('credit_card', 'debit_card', 'bank_transfer', 'cash')),
  -- Payment amount must be positive
  CONSTRAINT PAYMENT_amount_check  CHECK (amount > 0),
  CONSTRAINT PAYMENT_booking_key   UNIQUE (booking_id),
  CONSTRAINT PAYMENT_booking_fkey  FOREIGN KEY (booking_id)
    REFERENCES public."BOOKING" (booking_id)
);

-- Refund Table
CREATE TABLE public."REFUND" (
  refund_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
  payment_id  uuid        NOT NULL,         -- Source payment
  amount      numeric     NOT NULL,         -- Refund amount
  status      varchar     NOT NULL DEFAULT 'pending',
  refunded_at timestamptz NULL,             -- Refund processed datetime
  CONSTRAINT REFUND_pkey          PRIMARY KEY (refund_id),
  -- Refund status must be a predefined value
  CONSTRAINT REFUND_status_check  CHECK (status IN ('pending', 'completed', 'rejected')),
  -- Refund amount must be positive
  CONSTRAINT REFUND_amount_check  CHECK (amount > 0),
  CONSTRAINT REFUND_payment_key   UNIQUE (payment_id),
  CONSTRAINT REFUND_payment_fkey  FOREIGN KEY (payment_id)
    REFERENCES public."PAYMENT" (payment_id)
);

-- Ticket Table
CREATE TABLE public."TICKET" (
  ticket_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
  booking_id  uuid        NOT NULL,         -- Associated booking
  ticket_no   varchar     NOT NULL,         -- Ticket number
  issued_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT TICKET_pkey          PRIMARY KEY (ticket_id),
  CONSTRAINT TICKET_no_key        UNIQUE (ticket_no),   -- Ensure ticket number uniqueness
  CONSTRAINT TICKET_booking_key   UNIQUE (booking_id),
  CONSTRAINT TICKET_booking_fkey  FOREIGN KEY (booking_id)
    REFERENCES public."BOOKING" (booking_id)
);


-- ============================================================
-- STEP 2. INDEXES (Search performance optimization)
-- ============================================================

-- Flight search: fast navigation by date + schedule
CREATE INDEX idx_flight_date ON public."FLIGHT" (flight_date);
CREATE INDEX idx_flight_status ON public."FLIGHT" (status);

-- Schedule search: fast navigation by departure/destination airports
CREATE INDEX idx_schedule_route ON public."FLIGHT_SCHEDULE" (depart_airport_iata, dest_airport_iata);
CREATE INDEX idx_schedule_valid ON public."FLIGHT_SCHEDULE" (valid_from, valid_until);

-- Booking search: query bookings by customer and flight
CREATE INDEX idx_booking_customer ON public."BOOKING" (customer_id);
CREATE INDEX idx_booking_flight ON public."BOOKING" (flight_id);
CREATE INDEX idx_booking_status ON public."BOOKING" (status);

-- Seat inventory: query seats by aircraft
CREATE INDEX idx_seat_aircraft ON public."SEAT_INVENTORY" (aircraft_id);


-- ============================================================
-- STEP 3. VIEWS
-- ============================================================

-- ▼ VIEW to replace AIRCRAFT's total_seats
-- Dynamically calculate total seats by aircraft from SEAT_INVENTORY
CREATE OR REPLACE VIEW public."AIRCRAFT_SUMMARY_VIEW" AS
SELECT
  a.aircraft_id,
  a.model,
  COUNT(si.seat_id)::smallint AS total_seats
FROM      public."AIRCRAFT"       a
LEFT JOIN public."SEAT_INVENTORY" si ON si.aircraft_id = a.aircraft_id
GROUP BY  a.aircraft_id, a.model;

-- ▼ Booking Details VIEW (for customers)
CREATE OR REPLACE VIEW public."BOOKING_VIEW" AS
SELECT
  b.booking_id,
  b.flight_id,
  b.customer_id,
  c.name                  AS customer_name,
  c.email                 AS customer_email,
  f.flight_date,
  f.depart_time,
  f.arrival_time,
  fs.flight_number,
  fs.depart_airport_iata,
  fs.dest_airport_iata,
  si.seat_number,
  sc.class_name,
  b.status,
  b.price,
  b.booked_at,
  t.ticket_no
FROM       public."BOOKING"         b
JOIN       public."CUSTOMER"        c  ON c.customer_id  = b.customer_id
JOIN       public."FLIGHT"          f  ON f.flight_id    = b.flight_id
JOIN       public."FLIGHT_SCHEDULE" fs ON fs.schedule_id = f.schedule_id
JOIN       public."SEAT_INVENTORY"  si ON si.seat_id     = b.seat_id
JOIN       public."SEAT_CLASS"      sc ON sc.class_id    = si.class_id
LEFT JOIN  public."TICKET"          t  ON t.booking_id   = b.booking_id;

-- ▼ Revenue Statistics VIEW (for staff)
CREATE OR REPLACE VIEW public."REVENUE_STATS_VIEW" AS
SELECT
  f.flight_id,
  fs.flight_number,
  fs.depart_airport_iata,
  fs.dest_airport_iata,
  f.flight_date,
  DATE_TRUNC('month',   f.flight_date) AS revenue_month,
  DATE_TRUNC('quarter', f.flight_date) AS revenue_quarter,
  sc.class_name,
  COUNT(b.booking_id)                  AS booking_count,
  COALESCE(SUM(p.amount), 0)          AS revenue,
  ROUND(
    COUNT(b.booking_id)::numeric / NULLIF(sc.seat_count, 0) * 100, 2
  )                                    AS load_factor_pct
FROM       public."FLIGHT"          f
JOIN       public."FLIGHT_SCHEDULE" fs ON fs.schedule_id = f.schedule_id
JOIN       public."BOOKING"         b  ON b.flight_id    = f.flight_id
                                      AND b.status = 'confirmed'
JOIN       public."PAYMENT"         p  ON p.booking_id   = b.booking_id
                                      AND p.status = 'completed'
JOIN       public."SEAT_INVENTORY"  si ON si.seat_id     = b.seat_id
JOIN       public."SEAT_CLASS"      sc ON sc.class_id    = si.class_id
GROUP BY
  f.flight_id, fs.flight_number,
  fs.depart_airport_iata, fs.dest_airport_iata,
  f.flight_date, sc.class_name, sc.seat_count;

-- ▼ Flight Availability VIEW (for search)
CREATE OR REPLACE VIEW public."FLIGHT_AVAILABILITY_VIEW" AS
SELECT
  f.flight_id,
  fs.flight_number,
  fs.depart_airport_iata,
  fs.dest_airport_iata,
  f.flight_date,
  f.depart_time,
  f.arrival_time,
  f.status        AS flight_status,
  al.name         AS airline_name,
  sc.class_name,
  sc.price,
  sc.seat_count   AS total_seats_in_class,
  sc.seat_count - COALESCE(booked.cnt, 0) AS available_seats
FROM       public."FLIGHT"          f
JOIN       public."FLIGHT_SCHEDULE" fs ON fs.schedule_id = f.schedule_id
JOIN       public."AIRLINE"         al ON al.airline_id  = fs.airline_id
JOIN       public."SEAT_CLASS"      sc ON sc.aircraft_id = f.aircraft_id
LEFT JOIN (
  SELECT
    b.flight_id,
    si.class_id,
    COUNT(*) AS cnt
  FROM       public."BOOKING"        b
  JOIN       public."SEAT_INVENTORY" si ON si.seat_id = b.seat_id
  WHERE b.status = 'confirmed'
  GROUP BY b.flight_id, si.class_id
) booked ON booked.flight_id = f.flight_id
        AND booked.class_id  = sc.class_id
WHERE f.status != 'cancelled'
;
