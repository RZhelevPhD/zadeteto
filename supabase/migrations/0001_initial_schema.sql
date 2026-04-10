-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Initial schema migration
-- Apply via: Supabase Dashboard → SQL Editor → paste → Run
-- Idempotent: every CREATE uses IF NOT EXISTS, every policy uses CREATE OR REPLACE
-- ════════════════════════════════════════════════════════════════════════

-- Skip eager validation of function bodies during this migration so we can
-- define helper functions (like is_admin) before the tables they reference.
-- Functions are still checked at call time — this only relaxes CREATE-time
-- validation. Scoped to this session via SET LOCAL inside an explicit txn.
SET check_function_bodies = off;

-- ─────────────────────────── EXTENSIONS ────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;       -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS postgis;        -- geography type for "near me" queries
CREATE EXTENSION IF NOT EXISTS unaccent;       -- needed for slug transliteration

-- ─────────────────────────── ENUMS ─────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE business_tier AS ENUM ('Доверен', 'Проверен', 'Стандартен', 'Безплатен');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE application_status AS ENUM ('pending', 'approved', 'rejected');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE report_status AS ENUM ('open', 'investigating', 'resolved', 'dismissed');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ─────────────────────────── HELPER FUNCTIONS ──────────────────────────

-- is_admin() — used by RLS policies to grant admin-only access
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.business_owners
    WHERE id = auth.uid() AND is_admin = true
  );
$$;

-- touch_updated_at() — generic trigger to bump updated_at on UPDATE
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- slugify() — Cyrillic → Latin transliteration + lowercase + dashes
-- Uses simple character mapping, not the full unaccent extension which doesn't handle Cyrillic.
CREATE OR REPLACE FUNCTION public.slugify(input text)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  result text;
BEGIN
  IF input IS NULL OR input = '' THEN
    RETURN NULL;
  END IF;
  result := lower(input);
  -- Cyrillic → Latin (Bulgarian-style transliteration)
  result := translate(result,
    'абвгдежзийклмнопрстуфхцчшщъьюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЬЮЯ',
    'abvgdezzijklmnoprstufhcc__ay aabvgdezzijklmnoprstufhcc__ay '
  );
  result := replace(result, 'ж', 'zh');
  result := replace(result, 'ч', 'ch');
  result := replace(result, 'ш', 'sh');
  result := replace(result, 'щ', 'sht');
  result := replace(result, 'ю', 'yu');
  result := replace(result, 'я', 'ya');
  -- Strip non-alphanumeric, collapse runs of dashes
  result := regexp_replace(result, '[^a-z0-9]+', '-', 'g');
  result := regexp_replace(result, '^-+|-+$', '', 'g');
  RETURN nullif(result, '');
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════
-- TABLES
-- ═══════════════════════════════════════════════════════════════════════

-- ─────────────────────────── businesses ────────────────────────────────
CREATE TABLE IF NOT EXISTS public.businesses (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  legacy_id     text UNIQUE,
  slug          text UNIQUE,
  name          text NOT NULL,
  tier          business_tier NOT NULL DEFAULT 'Безплатен',
  city          text,
  address       text,
  lat           double precision,
  lng           double precision,
  coords        geography(point, 4326),  -- populated by trigger from lat/lng
  description   text,
  services      text[] DEFAULT ARRAY[]::text[],
  categories    text[] DEFAULT ARRAY[]::text[],
  age_groups    text[] DEFAULT ARRAY[]::text[],
  logo          text,
  audit_score   integer,
  sop           boolean DEFAULT false,
  is_online     boolean GENERATED ALWAYS AS (city = 'Онлайн') STORED,
  -- Contact fields (all nullable, controlled by tier in app code)
  phone         text,
  email         text,
  website       text,
  facebook      text,
  instagram     text,
  tiktok        text,
  linkedin      text,
  x             text,
  youtube       text,
  maps          text,
  reviews       text,
  -- CTAs
  cta_label     text,
  cta_url       text,
  cta_label_1   text,
  cta_url_1     text,
  cta_label_2   text,
  cta_url_2     text,
  -- Ownership and workflow
  owner_id      uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  published     boolean DEFAULT false,
  created_at    timestamptz DEFAULT now() NOT NULL,
  updated_at    timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS businesses_published_tier_idx ON public.businesses (published, tier);
CREATE INDEX IF NOT EXISTS businesses_city_idx ON public.businesses (city);
CREATE INDEX IF NOT EXISTS businesses_owner_idx ON public.businesses (owner_id);
CREATE INDEX IF NOT EXISTS businesses_coords_gix ON public.businesses USING GIST (coords);
CREATE INDEX IF NOT EXISTS businesses_categories_gin ON public.businesses USING GIN (categories);
CREATE INDEX IF NOT EXISTS businesses_services_gin ON public.businesses USING GIN (services);

-- Trigger: touch updated_at on every UPDATE
DROP TRIGGER IF EXISTS businesses_touch_updated_at ON public.businesses;
CREATE TRIGGER businesses_touch_updated_at
  BEFORE UPDATE ON public.businesses
  FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- Trigger: auto-generate slug from name if null
CREATE OR REPLACE FUNCTION public.businesses_autoslug()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.slug IS NULL OR NEW.slug = '' THEN
    NEW.slug := public.slugify(NEW.name);
    -- Append random suffix if collision
    IF EXISTS (SELECT 1 FROM public.businesses WHERE slug = NEW.slug AND id <> COALESCE(NEW.id, gen_random_uuid())) THEN
      NEW.slug := NEW.slug || '-' || substring(gen_random_uuid()::text, 1, 6);
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS businesses_autoslug_trigger ON public.businesses;
CREATE TRIGGER businesses_autoslug_trigger
  BEFORE INSERT OR UPDATE OF name ON public.businesses
  FOR EACH ROW EXECUTE FUNCTION public.businesses_autoslug();

-- Trigger: populate coords from lat/lng
CREATE OR REPLACE FUNCTION public.businesses_set_coords()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.lat IS NOT NULL AND NEW.lng IS NOT NULL THEN
    NEW.coords := ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326)::geography;
  ELSE
    NEW.coords := NULL;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS businesses_set_coords_trigger ON public.businesses;
CREATE TRIGGER businesses_set_coords_trigger
  BEFORE INSERT OR UPDATE OF lat, lng ON public.businesses
  FOR EACH ROW EXECUTE FUNCTION public.businesses_set_coords();

-- ─────────────────────────── parents ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.parents (
  id            uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name  text,
  avatar_url    text,
  created_at    timestamptz DEFAULT now() NOT NULL
);

-- ─────────────────────────── business_owners ───────────────────────────
CREATE TABLE IF NOT EXISTS public.business_owners (
  id            uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name  text,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE SET NULL,
  is_admin      boolean DEFAULT false NOT NULL,
  created_at    timestamptz DEFAULT now() NOT NULL
);

-- Trigger: auto-create parents row on auth.users insert (default role)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.parents (id, display_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email))
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─────────────────────────── liked_businesses ──────────────────────────
CREATE TABLE IF NOT EXISTS public.liked_businesses (
  parent_id     uuid REFERENCES public.parents(id) ON DELETE CASCADE,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE CASCADE,
  created_at    timestamptz DEFAULT now() NOT NULL,
  PRIMARY KEY (parent_id, business_id)
);

-- ─────────────────────────── dismissed_businesses ──────────────────────
CREATE TABLE IF NOT EXISTS public.dismissed_businesses (
  parent_id     uuid REFERENCES public.parents(id) ON DELETE CASCADE,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE CASCADE,
  created_at    timestamptz DEFAULT now() NOT NULL,
  PRIMARY KEY (parent_id, business_id)
);

-- ─────────────────────────── reviews ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.reviews (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id     uuid REFERENCES public.parents(id) ON DELETE SET NULL,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE CASCADE,
  stars         smallint NOT NULL CHECK (stars BETWEEN 1 AND 5),
  text          text,
  approved      boolean DEFAULT false NOT NULL,
  created_at    timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS reviews_business_idx ON public.reviews (business_id);
CREATE INDEX IF NOT EXISTS reviews_parent_idx ON public.reviews (parent_id);
CREATE INDEX IF NOT EXISTS reviews_approved_idx ON public.reviews (approved) WHERE approved = true;

-- ─────────────────────────── feedback_log ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.feedback_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id     uuid REFERENCES public.parents(id) ON DELETE SET NULL,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE CASCADE,
  used          text,                                       -- "yes" / "no" / "unsure"
  reasons       text[] DEFAULT ARRAY[]::text[],
  other_text    text,
  stars         smallint CHECK (stars BETWEEN 0 AND 5),
  suggestion    text,
  created_at    timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS feedback_log_business_idx ON public.feedback_log (business_id);

-- ─────────────────────────── partner_applications ──────────────────────
CREATE TABLE IF NOT EXISTS public.partner_applications (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_name  text NOT NULL,
  company       text NOT NULL,
  brand         text NOT NULL,
  email         text NOT NULL,
  phone         text NOT NULL,
  city          text NOT NULL,
  category      text NOT NULL,
  website       text,
  status        application_status DEFAULT 'pending' NOT NULL,
  business_id   uuid REFERENCES public.businesses(id) ON DELETE SET NULL,
  reviewed_by   uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  reviewed_at   timestamptz,
  created_at    timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS partner_apps_status_idx ON public.partner_applications (status);
CREATE INDEX IF NOT EXISTS partner_apps_email_idx ON public.partner_applications (email);

-- ─────────────────────────── contact_messages ──────────────────────────
CREATE TABLE IF NOT EXISTS public.contact_messages (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  email         text NOT NULL,
  message       text NOT NULL,
  handled_by    uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  handled_at    timestamptz,
  created_at    timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS contact_messages_handled_idx ON public.contact_messages (handled_at) WHERE handled_at IS NULL;

-- ─────────────────────────── reports ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.reports (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type            text NOT NULL,                            -- info / service / safety / fraud / reviews / other
  partner_ref     text NOT NULL,                            -- legacy id or freeform name
  description     text NOT NULL,
  reporter_name   text,
  reporter_email  text,
  status          report_status DEFAULT 'open' NOT NULL,
  business_id     uuid REFERENCES public.businesses(id) ON DELETE SET NULL,
  resolved_by     uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  resolved_at     timestamptz,
  created_at      timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS reports_status_idx ON public.reports (status);

-- ═══════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.liked_businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dismissed_businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

-- ─────────────── businesses ───────────────
DROP POLICY IF EXISTS "businesses_select_published" ON public.businesses;
CREATE POLICY "businesses_select_published" ON public.businesses
  FOR SELECT USING (
    published = true OR owner_id = auth.uid() OR public.is_admin()
  );

DROP POLICY IF EXISTS "businesses_insert_owner" ON public.businesses;
CREATE POLICY "businesses_insert_owner" ON public.businesses
  FOR INSERT WITH CHECK (
    auth.uid() IS NOT NULL AND (owner_id = auth.uid() OR public.is_admin())
  );

DROP POLICY IF EXISTS "businesses_update_owner" ON public.businesses;
CREATE POLICY "businesses_update_owner" ON public.businesses
  FOR UPDATE USING (owner_id = auth.uid() OR public.is_admin());

-- No DELETE policy → nobody can delete (use published=false instead)

-- ─────────────── parents ───────────────
DROP POLICY IF EXISTS "parents_self_select" ON public.parents;
CREATE POLICY "parents_self_select" ON public.parents
  FOR SELECT USING (id = auth.uid() OR public.is_admin());

DROP POLICY IF EXISTS "parents_self_update" ON public.parents;
CREATE POLICY "parents_self_update" ON public.parents
  FOR UPDATE USING (id = auth.uid());

-- INSERT happens via trigger only; DELETE happens via auth.users cascade

-- ─────────────── business_owners ───────────────
DROP POLICY IF EXISTS "business_owners_self_select" ON public.business_owners;
CREATE POLICY "business_owners_self_select" ON public.business_owners
  FOR SELECT USING (id = auth.uid() OR public.is_admin());

DROP POLICY IF EXISTS "business_owners_self_update" ON public.business_owners;
CREATE POLICY "business_owners_self_update" ON public.business_owners
  FOR UPDATE USING (id = auth.uid());

-- INSERT happens by admin or via approval flow (admin uses service_role from edge function)

-- ─────────────── liked_businesses ───────────────
DROP POLICY IF EXISTS "liked_self_all" ON public.liked_businesses;
CREATE POLICY "liked_self_all" ON public.liked_businesses
  FOR ALL USING (parent_id = auth.uid()) WITH CHECK (parent_id = auth.uid());

-- ─────────────── dismissed_businesses ───────────────
DROP POLICY IF EXISTS "dismissed_self_all" ON public.dismissed_businesses;
CREATE POLICY "dismissed_self_all" ON public.dismissed_businesses
  FOR ALL USING (parent_id = auth.uid()) WITH CHECK (parent_id = auth.uid());

-- ─────────────── reviews ───────────────
DROP POLICY IF EXISTS "reviews_select_approved" ON public.reviews;
CREATE POLICY "reviews_select_approved" ON public.reviews
  FOR SELECT USING (
    approved = true OR parent_id = auth.uid() OR public.is_admin()
  );

DROP POLICY IF EXISTS "reviews_insert_anyone" ON public.reviews;
CREATE POLICY "reviews_insert_anyone" ON public.reviews
  FOR INSERT WITH CHECK (
    parent_id IS NULL OR parent_id = auth.uid()
  );

DROP POLICY IF EXISTS "reviews_update_own" ON public.reviews;
CREATE POLICY "reviews_update_own" ON public.reviews
  FOR UPDATE USING (parent_id = auth.uid() OR public.is_admin());

DROP POLICY IF EXISTS "reviews_delete_own" ON public.reviews;
CREATE POLICY "reviews_delete_own" ON public.reviews
  FOR DELETE USING (parent_id = auth.uid() OR public.is_admin());

-- ─────────────── feedback_log ───────────────
DROP POLICY IF EXISTS "feedback_select_admin" ON public.feedback_log;
CREATE POLICY "feedback_select_admin" ON public.feedback_log
  FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "feedback_insert_anyone" ON public.feedback_log;
CREATE POLICY "feedback_insert_anyone" ON public.feedback_log
  FOR INSERT WITH CHECK (true);

-- No update or delete

-- ─────────────── partner_applications ───────────────
DROP POLICY IF EXISTS "partner_apps_select_admin" ON public.partner_applications;
CREATE POLICY "partner_apps_select_admin" ON public.partner_applications
  FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "partner_apps_insert_anyone" ON public.partner_applications;
CREATE POLICY "partner_apps_insert_anyone" ON public.partner_applications
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "partner_apps_update_admin" ON public.partner_applications;
CREATE POLICY "partner_apps_update_admin" ON public.partner_applications
  FOR UPDATE USING (public.is_admin());

-- ─────────────── contact_messages ───────────────
DROP POLICY IF EXISTS "contact_select_admin" ON public.contact_messages;
CREATE POLICY "contact_select_admin" ON public.contact_messages
  FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "contact_insert_anyone" ON public.contact_messages;
CREATE POLICY "contact_insert_anyone" ON public.contact_messages
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "contact_update_admin" ON public.contact_messages;
CREATE POLICY "contact_update_admin" ON public.contact_messages
  FOR UPDATE USING (public.is_admin());

-- ─────────────── reports ───────────────
DROP POLICY IF EXISTS "reports_select_admin" ON public.reports;
CREATE POLICY "reports_select_admin" ON public.reports
  FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "reports_insert_anyone" ON public.reports;
CREATE POLICY "reports_insert_anyone" ON public.reports
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "reports_update_admin" ON public.reports;
CREATE POLICY "reports_update_admin" ON public.reports
  FOR UPDATE USING (public.is_admin());

-- ═══════════════════════════════════════════════════════════════════════
-- DONE.
-- Next steps after applying this migration:
-- 1. Sign up via the app (or Supabase Dashboard → Authentication → Users → Invite)
-- 2. Run this in SQL editor to grant yourself admin:
--      INSERT INTO public.business_owners (id, display_name, is_admin)
--      VALUES ('<your-uuid-from-auth.users>', 'Admin', true);
--    Find your uuid via: SELECT id, email FROM auth.users;
-- 3. See docs/supabase-setup.md for the complete walkthrough.
-- ═══════════════════════════════════════════════════════════════════════
