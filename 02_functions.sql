
-- 1) Generate Flights
CREATE OR REPLACE FUNCTION public.generate_flights(p_start_date date, p_end_date date)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_count int := 0;
BEGIN
    IF p_start_date > p_end_date THEN
        RAISE EXCEPTION 'Invalid date range: start_date (%) > end_date (%)', p_start_date, p_end_date;
    END IF;

    INSERT INTO public."FLIGHT"(schedule_id, aircraft_id, flight_date, depart_time, arrival_time, status)
    SELECT
        fs.schedule_id,
        fs.aircraft_id,
        d.d_date::date,
        (d.d_date::timestamp + fs.depart_time)::timestamptz,
        (
        CASE
            WHEN fs.arrival_time <= fs.depart_time
            THEN (d.d_date::timestamp + fs.arrival_time + interval '1 day')
            ELSE (d.d_date::timestamp + fs.arrival_time)
        END
        )::timestamptz,
        'scheduled'
    FROM public."FLIGHT_SCHEDULE" fs
    CROSS JOIN generate_series(p_start_date, p_end_date, interval '1 day') AS d(d_date)
    WHERE fs.aircraft_id IS NOT NULL
        AND d.d_date::date BETWEEN fs.valid_from AND fs.valid_until
        AND EXISTS (
        SELECT 1
        FROM unnest(string_to_array(replace(lower(fs.days_of_week), ' ', ''), ',')) AS t(tok)
        WHERE t.tok = lower(to_char(d.d_date::date, 'Dy'))   -- mon,tue,...
            OR t.tok = extract(isodow FROM d.d_date)::int::text -- 1..7
        )
        AND NOT EXISTS (
        SELECT 1
        FROM public."FLIGHT" f
        WHERE f.schedule_id = fs.schedule_id
            AND f.flight_date = d.d_date::date
        );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count || ' individual flights have been generated from the recurring schedules.';
END;
$$;

-- 2) Search Flights (adds optional class filter)
CREATE OR REPLACE FUNCTION public.search_flights(
    p_dep_iata varchar,
    p_arr_iata varchar,
    p_travel_date date,
    p_class_name varchar DEFAULT NULL
)
RETURNS TABLE(
    flight_id uuid,
    flight_number varchar,
    airline_name varchar,
    depart_time timestamptz,
    arrival_time timestamptz,
    class_name varchar,
    price numeric,
    available_seats bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT v.flight_id, v.flight_number, v.airline_name, v.depart_time, v.arrival_time,
            v.class_name, v.price, v.available_seats
    FROM public."FLIGHT_AVAILABILITY_VIEW" v
    WHERE v.depart_airport_iata = p_dep_iata
        AND v.dest_airport_iata = p_arr_iata
        AND v.flight_date = p_travel_date
        AND (p_class_name IS NULL OR v.class_name = p_class_name)
        AND v.available_seats > 0
    ORDER BY v.depart_time;
END;
$$;

-- 3) Create Booking (schema-correct + concurrency-safe)
CREATE OR REPLACE FUNCTION public.create_booking(
    p_customer_id uuid,
    p_flight_id uuid,
    p_seat_id uuid,
    p_amount numeric
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    v_booking_id uuid;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Payment amount must be > 0';
    END IF;

    -- seat must belong to the flight's aircraft and flight must be schedulable
    IF NOT EXISTS (
        SELECT 1
        FROM public."FLIGHT" f
        JOIN public."SEAT_INVENTORY" si
        ON si.seat_id = p_seat_id
        AND si.aircraft_id = f.aircraft_id
        WHERE f.flight_id = p_flight_id
        AND f.status = 'scheduled'
    ) THEN
        RAISE EXCEPTION 'Invalid seat/flight combination or flight not available';
    END IF;

    BEGIN
        INSERT INTO public."BOOKING"(flight_id, customer_id, seat_id, status, price)
        VALUES (p_flight_id, p_customer_id, p_seat_id, 'confirmed', p_amount)
        RETURNING booking_id INTO v_booking_id;
    EXCEPTION WHEN unique_violation THEN
        RAISE EXCEPTION 'The selected seat is already occupied for this flight.';
    END;

    INSERT INTO public."PAYMENT"(booking_id, amount, method, status)
    VALUES (v_booking_id, p_amount, 'credit_card', 'completed');

    INSERT INTO public."TICKET"(booking_id, ticket_no)
    VALUES (v_booking_id, 'TK-' || replace(v_booking_id::text, '-', ''));

    RETURN v_booking_id;
END;
$$;

-- 4) Cancel Booking + Refund (schema-correct and linked to original payment)
CREATE OR REPLACE FUNCTION public.cancel_booking(p_booking_id uuid)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_payment_id uuid;
    v_amount numeric;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public."BOOKING"
        WHERE booking_id = p_booking_id AND status = 'confirmed'
    ) THEN
        RAISE EXCEPTION 'Booking not found or already cancelled.';
    END IF;

    SELECT p.payment_id, p.amount
        INTO v_payment_id, v_amount
    FROM public."PAYMENT" p
    WHERE p.booking_id = p_booking_id
        AND p.status = 'completed'
    FOR UPDATE;

    IF v_payment_id IS NULL THEN
        RAISE EXCEPTION 'No completed payment found for booking %', p_booking_id;
    END IF;

    -- Delete TICKET first (FK references BOOKING)
    DELETE FROM public."TICKET"
    WHERE booking_id = p_booking_id;

    UPDATE public."BOOKING"
    SET status = 'cancelled'
    WHERE booking_id = p_booking_id;

    UPDATE public."PAYMENT"
    SET status = 'refunded'
    WHERE payment_id = v_payment_id;

    INSERT INTO public."REFUND"(payment_id, amount, status, refunded_at)
    VALUES (v_payment_id, v_amount, 'completed', now());

    RETURN 'Booking ' || p_booking_id || ' has been successfully cancelled and refunded.';
END;
$$;

-- 5) Revenue report (aligned with REVENUE_STATS_VIEW)
CREATE OR REPLACE FUNCTION public.get_revenue_report()
RETURNS TABLE (
    flight_id uuid,
    flight_number varchar,
    route text,
    flight_date date,
    revenue_month timestamptz,
    revenue_quarter timestamptz,
    class_name varchar,
    total_revenue numeric,
    class_revenue_pct numeric,
    load_factor_percentage numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.flight_id,
        v.flight_number,
        v.depart_airport_iata || ' -> ' || v.dest_airport_iata AS route,
        v.flight_date,
        v.revenue_month,
        v.revenue_quarter,
        v.class_name,
        v.revenue AS total_revenue,
        ROUND(
        100 * v.revenue / NULLIF(SUM(v.revenue) OVER (PARTITION BY v.flight_id, v.flight_date), 0), 2
        ) AS class_revenue_pct,
        v.load_factor_pct AS load_factor_percentage
    FROM public."REVENUE_STATS_VIEW" v
    ORDER BY v.flight_date DESC, v.revenue DESC;
END;
$$;
