-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0013: Partner Lifecycle Foundation
--
-- Phase 1 от партньорския lifecycle план. Слага DB основата за:
--   1. Waitlist signup flow (partners.html → auth.signUp → auto-create business)
--   2. VIP / hot-lead индикатор в админ queue-то
--   3. Change-request workflow за fiscal/safety-critical полета
--   4. AHDM marker flags за copy полета
--
-- Включва:
--   • partner_applications upgrade — добавя eik, vip_onboarding, auth_user_id,
--     signup_completed_at, password_set; маха NOT NULL от company/brand (формата
--     не ги събира, затова inserts падат досега)
--   • businesses upgrade — добавя fiscal полета: eik, company_name,
--     registered_address, mol_name, mol_phone, mol_email
--   • audit_submissions.is_hot_lead boolean (за бърз филтър)
--   • change_requests таблица + RLS
--   • ahdm_review_flags таблица + RLS
--   • RPC create_business_for_partner(p_application_id) — атомарно създава
--     businesses + business_owners + draft audit_submissions ред след email
--     confirmation, базирано на partner_applications row
--
-- Idempotent — безопасна за повтаряне.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────────────────────── partner_applications upgrade ─────────────
-- Махаме NOT NULL от company / brand (формата на partners.html не ги събира).
-- Колоните остават за обратна съвместимост с други lead източници.
ALTER TABLE public.partner_applications
  ALTER COLUMN company DROP NOT NULL,
  ALTER COLUMN brand   DROP NOT NULL;

ALTER TABLE public.partner_applications
  ADD COLUMN IF NOT EXISTS eik                   text,
  ADD COLUMN IF NOT EXISTS vip_onboarding        boolean   NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS auth_user_id          uuid      REFERENCES auth.users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS signup_completed_at   timestamptz,
  ADD COLUMN IF NOT EXISTS password_set          boolean   NOT NULL DEFAULT false;

COMMENT ON COLUMN public.partner_applications.eik IS
  'Единен идентификационен код. NULL ако lead-ът е маркирал „все още нямаме ЕИК / не сме открили дейност".';
COMMENT ON COLUMN public.partner_applications.vip_onboarding IS
  'TRUE ако lead-ът е чекнал „Искам VIP старт" в waitlist формата. Денормализира се в audit_submissions.is_hot_lead при auto-create на business.';
COMMENT ON COLUMN public.partner_applications.auth_user_id IS
  'Linkва lead към auth.users row, ако партньорът е продължил към signUp от waitlist формата. NULL за стари lead-ове или admin-вкарани.';
COMMENT ON COLUMN public.partner_applications.signup_completed_at IS
  'Timestamp когато partner-ът е потвърдил имейла си и create_business_for_partner е минала. NULL означава pending confirmation.';
COMMENT ON COLUMN public.partner_applications.password_set IS
  'TRUE ако lead-ът е продължил към signUp с парола (не е само на waitlist).';

-- Composite index за бърз филтър „горещи waiting за confirmation"
CREATE INDEX IF NOT EXISTS partner_apps_vip_status_idx
  ON public.partner_applications (vip_onboarding, status)
  WHERE vip_onboarding = true;

-- ─────────────────────────── businesses fiscal columns ────────────────
-- Safety-critical полета. Промяната им от owner-а минава през change_requests.
ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS eik                 text,
  ADD COLUMN IF NOT EXISTS company_name        text,
  ADD COLUMN IF NOT EXISTS registered_address  text,
  ADD COLUMN IF NOT EXISTS mol_name            text,
  ADD COLUMN IF NOT EXISTS mol_phone           text,
  ADD COLUMN IF NOT EXISTS mol_email           text;

COMMENT ON COLUMN public.businesses.eik IS
  'ЕИК / Булстат на регистрираното юридическо лице. Safety-critical: change-request only.';
COMMENT ON COLUMN public.businesses.company_name IS
  'Официалното фирмено наименование (юридическо лице). Различно от businesses.name (публичен бранд). Safety-critical.';
COMMENT ON COLUMN public.businesses.registered_address IS
  'Адрес по търговска регистрация. Различен от businesses.address (публичен/работен адрес). Safety-critical.';
COMMENT ON COLUMN public.businesses.mol_name IS
  'Материално-отговорно лице, име. Safety-critical.';
COMMENT ON COLUMN public.businesses.mol_phone IS
  'МОЛ телефон. Safety-critical.';
COMMENT ON COLUMN public.businesses.mol_email IS
  'МОЛ имейл. Safety-critical.';

CREATE INDEX IF NOT EXISTS businesses_eik_idx ON public.businesses (eik) WHERE eik IS NOT NULL;

-- ─────────────────────────── audit_submissions.is_hot_lead ────────────
ALTER TABLE public.audit_submissions
  ADD COLUMN IF NOT EXISTS is_hot_lead boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.audit_submissions.is_hot_lead IS
  'TRUE за submission от партньор който е чекнал „Искам VIP старт" при waitlist signup. Деноромализирано от partner_applications.vip_onboarding за бърз филтър в admin queue.';

CREATE INDEX IF NOT EXISTS audit_submissions_hot_lead_idx
  ON public.audit_submissions (is_hot_lead, status)
  WHERE is_hot_lead = true;

-- ─────────────────────────── change_requests table ────────────────────
CREATE TABLE IF NOT EXISTS public.change_requests (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id   uuid NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  requested_by  uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  field_name    text NOT NULL,           -- 'company_name'|'eik'|'registered_address'|'mol_name'|'mol_phone'|'mol_email'
  old_value     text,
  new_value     text NOT NULL,
  status        text NOT NULL DEFAULT 'pending',  -- 'pending'|'approved'|'rejected'|'cancelled'
  admin_note    text,
  reviewed_by   uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  reviewed_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT chk_change_requests_status
    CHECK (status IN ('pending','approved','rejected','cancelled')),
  CONSTRAINT chk_change_requests_field
    CHECK (field_name IN (
      'company_name','eik','registered_address',
      'mol_name','mol_phone','mol_email'
    ))
);

COMMENT ON TABLE public.change_requests IS
  'Заявки за промяна на safety-critical полета на businesses. Партньорът ги подава, админ/суперадмин ги одобрява или отхвърля. Admin direct edits също оставят audit row тук със status=approved.';

-- Само една pending заявка на (business_id, field_name) едновременно
CREATE UNIQUE INDEX IF NOT EXISTS change_requests_one_pending_per_field
  ON public.change_requests (business_id, field_name)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS change_requests_business_idx ON public.change_requests (business_id);
CREATE INDEX IF NOT EXISTS change_requests_status_idx   ON public.change_requests (status);
CREATE INDEX IF NOT EXISTS change_requests_pending_idx  ON public.change_requests (created_at DESC)
  WHERE status = 'pending';

ALTER TABLE public.change_requests ENABLE ROW LEVEL SECURITY;

-- INSERT: owner на бизнеса може да създава заявки за свои бизнеси
DROP POLICY IF EXISTS change_requests_insert ON public.change_requests;
CREATE POLICY change_requests_insert ON public.change_requests
  FOR INSERT TO authenticated
  WITH CHECK (
    requested_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.businesses b
       WHERE b.id = change_requests.business_id
         AND b.owner_id = auth.uid()
    )
  );

-- SELECT: owner вижда свои; admin/superadmin виждат всички
DROP POLICY IF EXISTS change_requests_select ON public.change_requests;
CREATE POLICY change_requests_select ON public.change_requests
  FOR SELECT TO authenticated
  USING (
    requested_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.businesses b
       WHERE b.id = change_requests.business_id
         AND b.owner_id = auth.uid()
    )
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- UPDATE: само admin/superadmin (за approve/reject + admin_note + reviewed_*)
DROP POLICY IF EXISTS change_requests_update ON public.change_requests;
CREATE POLICY change_requests_update ON public.change_requests
  FOR UPDATE TO authenticated
  USING (public.is_admin() OR public.is_superadmin())
  WITH CHECK (public.is_admin() OR public.is_superadmin());

-- DELETE: owner може да трие свои pending заявки; admin може всичко
DROP POLICY IF EXISTS change_requests_delete ON public.change_requests;
CREATE POLICY change_requests_delete ON public.change_requests
  FOR DELETE TO authenticated
  USING (
    (requested_by = auth.uid() AND status = 'pending')
    OR public.is_admin()
    OR public.is_superadmin()
  );

GRANT SELECT, INSERT, DELETE ON public.change_requests TO authenticated;
GRANT UPDATE ON public.change_requests TO authenticated;

-- ─────────────────────────── ahdm_review_flags table ──────────────────
CREATE TABLE IF NOT EXISTS public.ahdm_review_flags (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id     uuid NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  field_path      text NOT NULL,        -- 'description'|'tagline'|'audit_answer:L1_Q07' etc.
  flagged_by      uuid NOT NULL REFERENCES auth.users(id) ON DELETE SET NULL,
  flagged_at      timestamptz NOT NULL DEFAULT now(),
  processed_at    timestamptz,
  ahdm_suggestion text
);

COMMENT ON TABLE public.ahdm_review_flags IS
  'Маркери за AHDM преглед на копи полета. Админ натиска „🪄 AHDM" в редактора, ред влиза тук. CLI скрипт executions/process_ahdm_flags.py ги обработва batch и записва ahdm_suggestion обратно.';

CREATE INDEX IF NOT EXISTS ahdm_flags_business_idx  ON public.ahdm_review_flags (business_id);
CREATE INDEX IF NOT EXISTS ahdm_flags_unprocessed_idx
  ON public.ahdm_review_flags (flagged_at DESC)
  WHERE processed_at IS NULL;

ALTER TABLE public.ahdm_review_flags ENABLE ROW LEVEL SECURITY;

-- Само admin/superadmin SELECT/INSERT/UPDATE/DELETE
DROP POLICY IF EXISTS ahdm_flags_admin_all ON public.ahdm_review_flags;
CREATE POLICY ahdm_flags_admin_all ON public.ahdm_review_flags
  FOR ALL TO authenticated
  USING (public.is_admin() OR public.is_superadmin())
  WITH CHECK (public.is_admin() OR public.is_superadmin());

GRANT SELECT, INSERT, UPDATE, DELETE ON public.ahdm_review_flags TO authenticated;

-- ─────────────────────────── RPC: create_business_for_partner ─────────
--
-- Извиква се от welcome.html след auth email confirmation. Атомарно:
--   1. Намира partner_applications row по auth.uid()
--   2. Създава businesses ред (с draft / unpublished статус, populated от формата)
--   3. Създава business_owners ред
--   4. Линква partner_applications.business_id + signup_completed_at
--   5. Ако vip_onboarding=true, създава draft audit_submissions с is_hot_lead=true
--   6. Връща {business_id, slug, business_name, is_hot_lead}
--
-- SECURITY DEFINER защото RLS на businesses би блокирала insert от anon/authenticated
-- без owner_id; авторизацията тук е чрез auth.uid() match с partner_applications.auth_user_id.
--
-- Грешки (RAISE EXCEPTION ... USING ERRCODE='P0001'):
--   'not_authenticated'       — auth.uid() е NULL
--   'no_application_found'    — няма partner_applications row за този user
--   'already_completed'       — signup вече е минал, business вече съществува
--
-- При повторно извикване (idempotent на client-side — например refresh):
--   Връща {ok:true, already_completed:true, business_id, slug}
--

CREATE OR REPLACE FUNCTION public.create_business_for_partner()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _uid       uuid := auth.uid();
  _app       public.partner_applications%ROWTYPE;
  _biz_id    uuid;
  _biz_slug  text;
  _biz_name  text;
  _biz_eik   text;
  _hot       boolean;
BEGIN
  IF _uid IS NULL THEN
    RAISE EXCEPTION 'not_authenticated' USING ERRCODE = 'P0001';
  END IF;

  -- Намери partner_applications за този auth user (последната, ако има няколко)
  SELECT * INTO _app
    FROM public.partner_applications
   WHERE auth_user_id = _uid
   ORDER BY created_at DESC
   LIMIT 1
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'no_application_found' USING ERRCODE = 'P0001';
  END IF;

  -- Idempotency: ако вече е завършен signup, върни съществуващото
  IF _app.signup_completed_at IS NOT NULL AND _app.business_id IS NOT NULL THEN
    SELECT slug, name INTO _biz_slug, _biz_name
      FROM public.businesses
     WHERE id = _app.business_id;
    RETURN jsonb_build_object(
      'ok', true,
      'already_completed', true,
      'business_id', _app.business_id,
      'slug', _biz_slug,
      'business_name', _biz_name,
      'is_hot_lead', _app.vip_onboarding
    );
  END IF;

  _biz_name := _app.contact_name || ' (чернова)';
  _biz_eik  := NULLIF(_app.eik, '');
  _hot      := _app.vip_onboarding;

  -- Създай businesses ред (draft, unpublished)
  INSERT INTO public.businesses (
    name, tier, city, categories, eik,
    phone, email,
    owner_id, claimed_at, claim_method,
    is_sample, published
  )
  VALUES (
    _biz_name,
    'Безплатен'::business_tier,
    NULLIF(_app.city, ''),
    CASE WHEN _app.category IS NOT NULL AND _app.category <> ''
         THEN ARRAY[_app.category]
         ELSE ARRAY[]::text[] END,
    _biz_eik,
    NULLIF(_app.phone, ''),
    NULLIF(_app.email, ''),
    _uid,
    now(),
    'waitlist',
    false,
    false
  )
  RETURNING id, slug INTO _biz_id, _biz_slug;

  -- Създай business_owners ред (или upsert ако rusi.zhelev/superadmin вече има)
  INSERT INTO public.business_owners (id, display_name, business_id, is_admin)
  VALUES (_uid, _app.contact_name, _biz_id, false)
  ON CONFLICT (id) DO UPDATE
    SET business_id  = COALESCE(public.business_owners.business_id, EXCLUDED.business_id),
        display_name = COALESCE(public.business_owners.display_name, EXCLUDED.display_name);

  -- Свържи partner_applications с новия business + маркирай като completed
  UPDATE public.partner_applications
     SET business_id          = _biz_id,
         signup_completed_at  = now(),
         status               = 'approved'
   WHERE id = _app.id;

  -- VIP → draft audit_submission с is_hot_lead=true (за да изскочи в admin queue-то)
  IF _hot THEN
    INSERT INTO public.audit_submissions (
      business_id, tier, status, is_hot_lead
    )
    VALUES (
      _biz_id,
      'Безплатен'::business_tier,
      'draft',
      true
    )
    ON CONFLICT (business_id, tier) DO UPDATE
      SET is_hot_lead = true;
  END IF;

  RETURN jsonb_build_object(
    'ok', true,
    'already_completed', false,
    'business_id', _biz_id,
    'slug', _biz_slug,
    'business_name', _biz_name,
    'is_hot_lead', _hot
  );
END;
$$;

COMMENT ON FUNCTION public.create_business_for_partner() IS
  'Атомарно създава businesses + business_owners + (optional) draft audit_submissions ред за newly-confirmed партньор. Базира се на partner_applications row linked чрез auth_user_id. Idempotent — повторно извикване от welcome.html refresh връща existing business.';

GRANT EXECUTE ON FUNCTION public.create_business_for_partner() TO authenticated;

-- ════════════════════════════════════════════════════════════════════════
-- DONE.
--
-- Verification:
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name='partner_applications'
--      AND column_name IN ('eik','vip_onboarding','auth_user_id',
--                          'signup_completed_at','password_set');
--   -- Expect 5 rows.
--
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name='businesses'
--      AND column_name IN ('eik','company_name','registered_address',
--                          'mol_name','mol_phone','mol_email');
--   -- Expect 6 rows.
--
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name='audit_submissions' AND column_name='is_hot_lead';
--   -- Expect 1 row.
--
--   SELECT count(*) FROM public.change_requests;     -- Expect 0.
--   SELECT count(*) FROM public.ahdm_review_flags;   -- Expect 0.
--
--   SELECT proname FROM pg_proc WHERE proname='create_business_for_partner';
--   -- Expect 1 row.
-- ════════════════════════════════════════════════════════════════════════
