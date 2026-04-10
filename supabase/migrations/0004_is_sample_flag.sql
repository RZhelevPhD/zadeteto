-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0004
-- Add is_sample boolean to businesses for safe mockup tracking
--
-- WHY: Mock data needs to be cleanly separable from real partner data so
-- we never accidentally delete real businesses when cleaning up demos.
-- A dedicated boolean column is the safest pattern:
--   - DEFAULT false → real businesses are NEVER tagged as samples
--   - The ONLY code path that sets it true is the explicit seed SQL files
--     (sample-businesses.sql and sample-100-mockup-partners.sql)
--   - No form, no API endpoint, no admin UI ever sets this flag
--   - Cleanup is one query: DELETE FROM businesses WHERE is_sample = true
--
-- This migration is idempotent — re-running is a no-op.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS is_sample boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN public.businesses.is_sample IS
  'TRUE for businesses inserted via seed SQL files (sample-businesses.sql, sample-100-mockup-partners.sql). FALSE for all real partner data. Used for safe cleanup. Real businesses must NEVER have this flag set to true.';

-- Index for fast cleanup queries (small partial index, only on TRUE rows)
CREATE INDEX IF NOT EXISTS businesses_is_sample_idx
  ON public.businesses (is_sample)
  WHERE is_sample = true;

-- Backfill: mark the 6 sample businesses from sample-businesses.sql as samples
-- (their legacy_id starts with 'sample-')
UPDATE public.businesses
  SET is_sample = true
  WHERE legacy_id LIKE 'sample-%' AND is_sample = false;

-- ════════════════════════════════════════════════════════════════════════
-- DONE.
--
-- Verification queries:
--   SELECT count(*) FROM public.businesses WHERE is_sample = true;   -- mockups
--   SELECT count(*) FROM public.businesses WHERE is_sample = false;  -- real
--   SELECT count(*) FROM public.businesses;                          -- total
--
-- Cleanup (deletes ALL mockups, NEVER touches real data):
--   DELETE FROM public.businesses WHERE is_sample = true;
-- ════════════════════════════════════════════════════════════════════════
