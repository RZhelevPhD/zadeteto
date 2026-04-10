-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0003
-- Listing page enrichment: working hours + (future) gallery URLs
--
-- Adds two new columns to public.businesses:
--   1. working_hours (jsonb)  — per-day open/close times
--      Shape: {"mon":"9:00-18:00", "tue":"9:00-18:00", "wed":"9:00-18:00",
--              "sat":"10:00-14:00", "sun":"closed", "note":"Затворено в празници"}
--      All keys optional. Use lowercase 3-letter day names. "closed" is a magic value.
--      Optional "note" field for free-form caveats (Bulgarian).
--
--   2. gallery_urls (text[])  — list of public image URLs to render in the gallery
--      For now: external URLs (Imgur, Cloudinary, partner's own server).
--      Future: switch to Supabase Storage URLs once that bundle ships.
--      RLS already allows SELECT on businesses where published=true,
--      so no separate policy needed for gallery_urls (it inherits row access).
--
-- Idempotent: every ALTER uses IF NOT EXISTS.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────── working_hours ───────────
ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS working_hours jsonb;

COMMENT ON COLUMN public.businesses.working_hours IS
  'Per-day open/close times. Shape: {"mon":"9:00-18:00",...,"sun":"closed","note":"..."}. All keys optional. Lowercase 3-letter day names. "closed" is a magic value.';

-- ─────────── gallery_urls ───────────
ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS gallery_urls text[] DEFAULT ARRAY[]::text[];

COMMENT ON COLUMN public.businesses.gallery_urls IS
  'Public image URLs for the gallery section on listing.html. For now: external URLs (Imgur etc). Future: Supabase Storage paths.';

-- ─────────── Sample data for testing ───────────
-- (Commented out — uncomment + run manually if you want to populate
--  one business with test working hours and gallery images.)
--
-- UPDATE public.businesses
-- SET
--   working_hours = '{
--     "mon": "9:00-18:00",
--     "tue": "9:00-18:00",
--     "wed": "9:00-18:00",
--     "thu": "9:00-18:00",
--     "fri": "9:00-18:00",
--     "sat": "10:00-14:00",
--     "sun": "closed"
--   }'::jsonb,
--   gallery_urls = ARRAY[
--     'https://placehold.co/600x400/7c4dff/white?text=Snimka+1',
--     'https://placehold.co/600x400/2e994d/white?text=Snimka+2',
--     'https://placehold.co/600x400/c89a00/white?text=Snimka+3'
--   ]
-- WHERE name = 'Test Specialist';

-- ════════════════════════════════════════════════════════════════════════
-- DONE. Listing page will pick up these columns on next page load.
-- Both columns are nullable / default-empty, so existing rows are unaffected.
-- ════════════════════════════════════════════════════════════════════════
