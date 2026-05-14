-- ============================================================
-- Airline Reservation System (AirBooking)
-- CSE 305 Term Project — Data API Access Grants
-- ============================================================
-- Execution order: 01_schema.sql → 02_functions.sql → 03_seed_sample_data.sql → 04_grants.sql
-- ============================================================
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
-- Done! This script is idempotent — safe to run multiple times.
-- ============================================================
