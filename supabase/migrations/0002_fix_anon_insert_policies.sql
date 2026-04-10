-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0002
-- Fix: anon role couldn't insert into form tables because the policies
-- in 0001 used the default `public` role grant, which Supabase does NOT
-- automatically map to the `anon` JWT role used by the API.
--
-- This migration:
--   1. Drops the broken policies and re-creates them with explicit TO clause
--      that lists `anon` and `authenticated` as allowed roles
--   2. Grants table-level INSERT to both roles where needed
--   3. Idempotent — safe to re-run
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────── contact_messages: anyone can INSERT ───────────
DROP POLICY IF EXISTS "contact_insert_anyone" ON public.contact_messages;
CREATE POLICY "contact_insert_anyone" ON public.contact_messages
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);
GRANT INSERT ON public.contact_messages TO anon, authenticated;

-- ─────────── reports: anyone can INSERT ───────────
DROP POLICY IF EXISTS "reports_insert_anyone" ON public.reports;
CREATE POLICY "reports_insert_anyone" ON public.reports
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);
GRANT INSERT ON public.reports TO anon, authenticated;

-- ─────────── partner_applications: anyone can INSERT ───────────
DROP POLICY IF EXISTS "partner_apps_insert_anyone" ON public.partner_applications;
CREATE POLICY "partner_apps_insert_anyone" ON public.partner_applications
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);
GRANT INSERT ON public.partner_applications TO anon, authenticated;

-- ─────────── feedback_log: anyone can INSERT ───────────
DROP POLICY IF EXISTS "feedback_insert_anyone" ON public.feedback_log;
CREATE POLICY "feedback_insert_anyone" ON public.feedback_log
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);
GRANT INSERT ON public.feedback_log TO anon, authenticated;

-- ─────────── reviews: anonymous OR own ───────────
DROP POLICY IF EXISTS "reviews_insert_anyone" ON public.reviews;
CREATE POLICY "reviews_insert_anyone" ON public.reviews
  FOR INSERT TO anon, authenticated
  WITH CHECK (parent_id IS NULL OR parent_id = auth.uid());
GRANT INSERT ON public.reviews TO anon, authenticated;

-- ─────────── businesses: published rows readable by anon ───────────
-- The SELECT policy was correct, but make sure the table-level grant exists
GRANT SELECT ON public.businesses TO anon, authenticated;

-- ─────────── reviews: approved rows readable by anon ───────────
GRANT SELECT ON public.reviews TO anon, authenticated;

-- ════════════════════════════════════════════════════════════════════════
-- DONE. Re-run the smoke test to verify INSERTs now succeed.
-- ════════════════════════════════════════════════════════════════════════
