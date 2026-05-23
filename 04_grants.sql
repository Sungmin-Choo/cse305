-- ============================================================
-- Airline Reservation System (AirBooking)
-- CSE 305 Term Project — Data API Access Grants + RLS Setup
-- ============================================================
-- Execution order: 01_schema.sql → 02_functions.sql → 03_seed_sample_data.sql → 04_grants.sql
-- ============================================================
-- Two things must be in place for the anon key (used by the
-- Streamlit app) to read/write the schema:
--   (1) GRANTs on every table / view / function.
--   (2) Row Level Security DISABLED on every table — Supabase
--       enables RLS by default whenever a table is created, so
--       running 01_schema.sql (which drops and recreates every
--       table) silently re-arms RLS and the anon role gets back
--       zero rows. The DISABLE statements at the bottom of this
--       file undo that.
--
-- Supabase policy change (effective 2026-05-30):
--   Tables in the "public" schema of new projects will no longer
--   be exposed to the Data API (supabase-js, PostgREST, GraphQL)
--   without explicit GRANTs.
--   Existing projects will follow the same policy from 2026-10-30.
-- ============================================================


-- ============================================================
-- STEP 1. TABLE GRANTS — anon / authenticated / service_role
-- ============================================================
-- The app uses supabase-py with the anon key (Data API),
-- so the anon role needs CRUD privileges on all tables.
-- Since this is a university course project, identical
-- privileges are granted to all three roles for simplicity.

grant select, insert, update, delete
  on public."AIRLINE"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."AIRPORT"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."AIRCRAFT"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."CUSTOMER"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."STAFF"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."SEAT_CLASS"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."SEAT_INVENTORY"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."FLIGHT_SCHEDULE"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."STOPOVER"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."FLIGHT"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."BOOKING"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."PAYMENT"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."REFUND"
  to anon, authenticated, service_role;

grant select, insert, update, delete
  on public."TICKET"
  to anon, authenticated, service_role;


-- ============================================================
-- STEP 2. VIEW GRANTS — read-only (SELECT)
-- ============================================================

grant select
  on public."AIRCRAFT_SUMMARY_VIEW"
  to anon, authenticated, service_role;

grant select
  on public."BOOKING_VIEW"
  to anon, authenticated, service_role;

grant select
  on public."REVENUE_STATS_VIEW"
  to anon, authenticated, service_role;

grant select
  on public."FLIGHT_AVAILABILITY_VIEW"
  to anon, authenticated, service_role;


-- ============================================================
-- STEP 3. FUNCTION GRANTS — EXECUTE on stored procedures
-- ============================================================
-- PostgREST exposes any function in the "public" schema as an
-- RPC endpoint, but only if the calling role has EXECUTE.
-- Listed explicitly so a re-grant after schema changes is
-- self-contained.

grant execute on function public.generate_flights(uuid, date, date)
  to anon, authenticated, service_role;

grant execute on function public.search_flights(varchar, varchar, date, varchar)
  to anon, authenticated, service_role;

grant execute on function public.create_booking(uuid, uuid, uuid, numeric)
  to anon, authenticated, service_role;

grant execute on function public.cancel_booking(uuid)
  to anon, authenticated, service_role;

grant execute on function public.get_revenue_report()
  to anon, authenticated, service_role;

grant execute on function public.bulk_generate_test_bookings(int, int)
  to anon, authenticated, service_role;

grant execute on function public.explain_search_flights(varchar, varchar, date, varchar)
  to anon, authenticated, service_role;

grant execute on function public.explain_revenue_report()
  to anon, authenticated, service_role;


-- ============================================================
-- STEP 4. DISABLE ROW LEVEL SECURITY
-- ============================================================
-- 01_schema.sql drops and recreates every table — Supabase
-- arms RLS on each new table, so the anon role gets back zero
-- rows on SELECT even though GRANTs are in place.
-- Symptom: login returns "Invalid email or password" because the
-- SELECT against CUSTOMER / STAFF silently returns 0 rows.

ALTER TABLE public."AIRLINE"         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."AIRPORT"         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."AIRCRAFT"        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."CUSTOMER"        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."STAFF"           DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."SEAT_CLASS"      DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."SEAT_INVENTORY"  DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."FLIGHT_SCHEDULE" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."STOPOVER"        DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."FLIGHT"          DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."BOOKING"         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."PAYMENT"         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."REFUND"          DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."TICKET"          DISABLE ROW LEVEL SECURITY;


-- ============================================================
-- Done! This script is idempotent — safe to run multiple times.
-- ============================================================
