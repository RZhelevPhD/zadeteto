-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0006
-- 1. Add is_superadmin column to business_owners
-- 2. Auto-grant superadmin to rusi.zhelev@gmail.com on signup
-- 3. Insert sample audit submissions for testing
--
-- Superadmin can: view/edit all partner profiles, switch between them,
-- manage all audit submissions, change scores, approve/reject.
--
-- Idempotent — safe to re-run.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────────────────────── SUPERADMIN COLUMN ────────────────────────
ALTER TABLE public.business_owners
  ADD COLUMN IF NOT EXISTS is_superadmin boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN public.business_owners.is_superadmin IS
  'TRUE for platform-level superadmins who can view/edit ALL profiles, audit submissions, and scores. Separate from is_admin which grants admin-level access. Superadmin includes all admin powers plus cross-profile management.';

-- ─────────────────────────── is_superadmin() helper ───────────────────
CREATE OR REPLACE FUNCTION public.is_superadmin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.business_owners
    WHERE id = auth.uid() AND is_superadmin = true
  );
$$;

-- ─────────────────────────── AUTO-GRANT SUPERADMIN ────────────────────
-- When rusi.zhelev@gmail.com signs up, auto-create business_owners row
-- with is_admin=true AND is_superadmin=true.
-- This runs AFTER the existing handle_new_user() trigger.
CREATE OR REPLACE FUNCTION public.handle_superadmin_signup()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Only act on specific superadmin emails
  IF NEW.email = 'rusi.zhelev@gmail.com' THEN
    INSERT INTO public.business_owners (id, display_name, is_admin, is_superadmin)
    VALUES (
      NEW.id,
      COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
      true,
      true
    )
    ON CONFLICT (id) DO UPDATE SET
      is_admin = true,
      is_superadmin = true;
  END IF;
  RETURN NEW;
END;
$$;

-- Drop and recreate to ensure idempotency
DROP TRIGGER IF EXISTS on_superadmin_signup ON auth.users;
CREATE TRIGGER on_superadmin_signup
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_superadmin_signup();

-- ─────────────────────────── GRANT EXISTING USER ─────────────────────
-- If rusi.zhelev@gmail.com already exists, grant superadmin now
DO $$
DECLARE
  _uid uuid;
BEGIN
  SELECT id INTO _uid FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1;
  IF _uid IS NOT NULL THEN
    INSERT INTO public.business_owners (id, display_name, is_admin, is_superadmin)
    VALUES (_uid, 'Руси Желев', true, true)
    ON CONFLICT (id) DO UPDATE SET
      is_admin = true,
      is_superadmin = true;
  END IF;
END $$;

-- ─────────────────────────── UPDATE RLS POLICIES ─────────────────────
-- Superadmin can SELECT all businesses (even unpublished)
DROP POLICY IF EXISTS businesses_select ON public.businesses;
CREATE POLICY businesses_select ON public.businesses
  FOR SELECT USING (
    published = true
    OR owner_id = auth.uid()
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can UPDATE any business
DROP POLICY IF EXISTS businesses_update ON public.businesses;
CREATE POLICY businesses_update ON public.businesses
  FOR UPDATE TO authenticated
  USING (
    owner_id = auth.uid()
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can see all audit submissions (including drafts)
DROP POLICY IF EXISTS audit_submissions_select ON public.audit_submissions;
CREATE POLICY audit_submissions_select ON public.audit_submissions
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.businesses b
      WHERE b.id = audit_submissions.business_id
        AND b.owner_id = auth.uid()
    )
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can update any audit submission
DROP POLICY IF EXISTS audit_submissions_update ON public.audit_submissions;
CREATE POLICY audit_submissions_update ON public.audit_submissions
  FOR UPDATE TO authenticated
  USING (
    (
      EXISTS (
        SELECT 1 FROM public.businesses b
        WHERE b.id = audit_submissions.business_id
          AND b.owner_id = auth.uid()
      )
      AND status = 'draft'
    )
    OR public.is_admin()
    OR public.is_superadmin()
  )
  WITH CHECK (
    public.is_admin() OR public.is_superadmin()
    OR (
      EXISTS (
        SELECT 1 FROM public.businesses b
        WHERE b.id = audit_submissions.business_id
          AND b.owner_id = auth.uid()
      )
      AND status IN ('draft', 'submitted')
    )
  );

-- Superadmin can see/manage all answers
DROP POLICY IF EXISTS audit_answers_select ON public.audit_answers;
CREATE POLICY audit_answers_select ON public.audit_answers
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_answers.submission_id
        AND b.owner_id = auth.uid()
    )
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can see/manage all scores
DROP POLICY IF EXISTS audit_scores_select ON public.audit_scores;
CREATE POLICY audit_scores_select ON public.audit_scores
  FOR SELECT TO authenticated
  USING (public.is_admin() OR public.is_superadmin());

DROP POLICY IF EXISTS audit_scores_insert ON public.audit_scores;
CREATE POLICY audit_scores_insert ON public.audit_scores
  FOR INSERT TO authenticated
  WITH CHECK (public.is_admin() OR public.is_superadmin());

DROP POLICY IF EXISTS audit_scores_update ON public.audit_scores;
CREATE POLICY audit_scores_update ON public.audit_scores
  FOR UPDATE TO authenticated
  USING (public.is_admin() OR public.is_superadmin());

DROP POLICY IF EXISTS audit_scores_delete ON public.audit_scores;
CREATE POLICY audit_scores_delete ON public.audit_scores
  FOR DELETE TO authenticated
  USING (public.is_admin() OR public.is_superadmin());

-- Superadmin can see all files
DROP POLICY IF EXISTS audit_files_select ON public.audit_files;
CREATE POLICY audit_files_select ON public.audit_files
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_files.submission_id
        AND b.owner_id = auth.uid()
    )
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can see all business_owners
DROP POLICY IF EXISTS business_owners_select ON public.business_owners;
CREATE POLICY business_owners_select ON public.business_owners
  FOR SELECT TO authenticated
  USING (
    id = auth.uid()
    OR public.is_admin()
    OR public.is_superadmin()
  );

-- Superadmin can update any business_owner
DROP POLICY IF EXISTS business_owners_update ON public.business_owners;
CREATE POLICY business_owners_update ON public.business_owners
  FOR UPDATE TO authenticated
  USING (
    id = auth.uid()
    OR public.is_superadmin()
  );

-- ─────────────────────────── SAMPLE AUDIT DATA ───────────────────────
-- Insert audit submissions for existing sample businesses
-- These reference legacy_id sample-001..006 from sample-businesses.sql

DO $$
DECLARE
  _biz1 uuid; _biz2 uuid; _biz3 uuid; _biz4 uuid;
  _sub1 uuid; _sub2 uuid; _sub3 uuid; _sub4 uuid;
BEGIN
  -- Find sample businesses
  SELECT id INTO _biz1 FROM public.businesses WHERE legacy_id = 'sample-001';
  SELECT id INTO _biz2 FROM public.businesses WHERE legacy_id = 'sample-002';
  SELECT id INTO _biz3 FROM public.businesses WHERE legacy_id = 'sample-003';
  SELECT id INTO _biz4 FROM public.businesses WHERE legacy_id = 'sample-004';

  IF _biz1 IS NULL OR _biz2 IS NULL THEN
    RAISE NOTICE 'Sample businesses not found — run sample-businesses.sql first. Skipping audit seed.';
    RETURN;
  END IF;

  -- ── Submission 1: Little Engineers (sample-001) — submitted, waiting review ──
  INSERT INTO public.audit_submissions (id, business_id, tier, status, submitted_at, created_at)
  VALUES (gen_random_uuid(), _biz1, 'Безплатен', 'submitted', now() - interval '2 days', now() - interval '3 days')
  ON CONFLICT (business_id, tier) DO UPDATE SET status = 'submitted', submitted_at = now() - interval '2 days'
  RETURNING id INTO _sub1;

  INSERT INTO public.audit_answers (submission_id, question_key, answer_value) VALUES
    (_sub1, 'L1_Q01', '{"text": "Литъл Инджиниърс ЕООД"}'::jsonb),
    (_sub1, 'L1_Q02', '{"text": "205987654"}'::jsonb),
    (_sub1, 'L1_Q03', '{"name": "Иван Петров", "role": "Управител", "phone": "+359 88 888 8888", "email": "ivan@littleengineers.bg"}'::jsonb),
    (_sub1, 'L1_Q05', '{"items": [{"rank": 1, "value": "София"}, {"rank": 2, "value": "Пловдив"}]}'::jsonb),
    (_sub1, 'L1_Q06', '{"items": [{"rank": 1, "value": "Образователен център"}, {"rank": 2, "value": "Школа / курс"}]}'::jsonb),
    (_sub1, 'L1_Q07', '{"text": "Вдъхновяваме следващото поколение инженери чрез практическо обучение по STEM, роботика и креативно мислене. Малки групи, индивидуален подход."}'::jsonb),
    (_sub1, 'L1_Q09', '{"items": [{"type": "website", "url": "https://littleengineers.bg"}, {"type": "facebook", "url": "https://facebook.com/littleengineers"}, {"type": "instagram", "url": "https://instagram.com/littleengineers"}]}'::jsonb),
    (_sub1, 'L1_Q10', '{"from": 6, "to": 14}'::jsonb)
  ON CONFLICT (submission_id, question_key) DO UPDATE SET answer_value = EXCLUDED.answer_value;

  -- ── Submission 2: STEM Lab София (sample-002) — submitted, waiting review ──
  INSERT INTO public.audit_submissions (id, business_id, tier, status, submitted_at, created_at)
  VALUES (gen_random_uuid(), _biz2, 'Безплатен', 'submitted', now() - interval '1 day', now() - interval '2 days')
  ON CONFLICT (business_id, tier) DO UPDATE SET status = 'submitted', submitted_at = now() - interval '1 day'
  RETURNING id INTO _sub2;

  INSERT INTO public.audit_answers (submission_id, question_key, answer_value) VALUES
    (_sub2, 'L1_Q01', '{"text": "СТЕМ Лаб ООД"}'::jsonb),
    (_sub2, 'L1_Q02', '{"text": "207123456"}'::jsonb),
    (_sub2, 'L1_Q03', '{"name": "Мария Георгиева", "role": "Съдружник", "phone": "+359 89 999 1234", "email": "maria@stemlab.bg"}'::jsonb),
    (_sub2, 'L1_Q05', '{"items": [{"rank": 1, "value": "София"}]}'::jsonb),
    (_sub2, 'L1_Q06', '{"items": [{"rank": 1, "value": "Образователен център"}]}'::jsonb),
    (_sub2, 'L1_Q07', '{"text": "Правим науката достъпна и забавна за деца от 4 до 12 години. Експерименти, LEGO роботика и програмиране."}'::jsonb),
    (_sub2, 'L1_Q09', '{"items": [{"type": "website", "url": "https://stemlab.bg"}, {"type": "instagram", "url": "https://instagram.com/stemlabsofia"}]}'::jsonb),
    (_sub2, 'L1_Q10', '{"from": 4, "to": 12}'::jsonb)
  ON CONFLICT (submission_id, question_key) DO UPDATE SET answer_value = EXCLUDED.answer_value;

  -- ── Submission 3: sample-003 — under_review (auditor has opened it) ──
  IF _biz3 IS NOT NULL THEN
    INSERT INTO public.audit_submissions (id, business_id, tier, status, submitted_at, created_at)
    VALUES (gen_random_uuid(), _biz3, 'Безплатен', 'under_review', now() - interval '5 days', now() - interval '6 days')
    ON CONFLICT (business_id, tier) DO UPDATE SET status = 'under_review', submitted_at = now() - interval '5 days'
    RETURNING id INTO _sub3;

    INSERT INTO public.audit_answers (submission_id, question_key, answer_value) VALUES
      (_sub3, 'L1_Q01', '{"text": "Детска градина Слънчице ЕООД"}'::jsonb),
      (_sub3, 'L1_Q02', '{"text": "204567890"}'::jsonb),
      (_sub3, 'L1_Q03', '{"name": "Елена Тодорова", "role": "Директор", "phone": "+359 87 777 5555", "email": "elena@slanchitse.bg"}'::jsonb),
      (_sub3, 'L1_Q05', '{"items": [{"rank": 1, "value": "Варна"}, {"rank": 2, "value": "Бургас"}]}'::jsonb),
      (_sub3, 'L1_Q06', '{"items": [{"rank": 1, "value": "Детска градина"}, {"rank": 2, "value": "Образователен център"}]}'::jsonb),
      (_sub3, 'L1_Q07', '{"text": "Създаваме топла и сигурна среда, в която децата учат чрез игра. Монтесори подход, двуезична програма БГ/EN."}'::jsonb),
      (_sub3, 'L1_Q09', '{"items": [{"type": "website", "url": "https://slanchitse.bg"}, {"type": "facebook", "url": "https://facebook.com/slanchitse"}]}'::jsonb),
      (_sub3, 'L1_Q10', '{"from": 1, "to": 7}'::jsonb)
    ON CONFLICT (submission_id, question_key) DO UPDATE SET answer_value = EXCLUDED.answer_value;
  END IF;

  -- ── Submission 4: sample-004 — scored (has scores, awaiting final approval) ──
  IF _biz4 IS NOT NULL THEN
    INSERT INTO public.audit_submissions (id, business_id, tier, status, submitted_at, created_at)
    VALUES (gen_random_uuid(), _biz4, 'Безплатен', 'scored', now() - interval '7 days', now() - interval '8 days')
    ON CONFLICT (business_id, tier) DO UPDATE SET status = 'scored', submitted_at = now() - interval '7 days'
    RETURNING id INTO _sub4;

    INSERT INTO public.audit_answers (submission_id, question_key, answer_value) VALUES
      (_sub4, 'L1_Q01', '{"text": "Логопедичен център Говори ООД"}'::jsonb),
      (_sub4, 'L1_Q02', '{"text": "203456789"}'::jsonb),
      (_sub4, 'L1_Q03', '{"name": "Десислава Николова", "role": "МОЛ", "phone": "+359 88 111 2233", "email": "desi@govori.bg"}'::jsonb),
      (_sub4, 'L1_Q05', '{"items": [{"rank": 1, "value": "Пловдив"}]}'::jsonb),
      (_sub4, 'L1_Q06', '{"items": [{"rank": 1, "value": "Логопед"}, {"rank": 2, "value": "Терапевт"}]}'::jsonb),
      (_sub4, 'L1_Q07', '{"text": "Помагаме на деца с говорни и комуникативни затруднения да открият гласа си. 15 години опит, съвременни методики."}'::jsonb),
      (_sub4, 'L1_Q09', '{"items": [{"type": "website", "url": "https://govori.bg"}]}'::jsonb),
      (_sub4, 'L1_Q10', '{"from": 2, "to": 16}'::jsonb)
    ON CONFLICT (submission_id, question_key) DO UPDATE SET answer_value = EXCLUDED.answer_value;

    -- Add some scores for this submission (from a mock auditor)
    -- We use a DO block so we can reference _sub4
    INSERT INTO public.audit_scores (submission_id, question_key, score, auditor_note, scored_by, scored_at) VALUES
      (_sub4, 'L1_Q01', 10, 'Коректно съвпада с ТР', (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q02', 8, 'ЕИК валиден', (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q03', 8, NULL, (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q05', 6, 'Само един град — минимално покритие', (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q06', 8, NULL, (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q07', 10, 'Отлична мисия, ясна и конкретна', (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q09', 4, 'Само уебсайт, липсват соцмрежи', (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days'),
      (_sub4, 'L1_Q10', 8, NULL, (SELECT id FROM auth.users WHERE email = 'rusi.zhelev@gmail.com' LIMIT 1), now() - interval '3 days')
    ON CONFLICT (submission_id, question_key) DO UPDATE SET
      score = EXCLUDED.score,
      auditor_note = EXCLUDED.auditor_note;
  END IF;

  RAISE NOTICE 'Sample audit data inserted: 4 submissions (2 submitted, 1 under_review, 1 scored)';
END $$;

-- ════════════════════════════════════════════════════════════════════════
-- DONE.
--
-- Summary:
--   - business_owners.is_superadmin column added
--   - is_superadmin() helper function created
--   - Auto-grant trigger for rusi.zhelev@gmail.com
--   - RLS policies updated to include is_superadmin()
--   - 4 sample audit submissions with answers inserted
--
-- Verification:
--   SELECT * FROM public.business_owners WHERE is_superadmin = true;
--   SELECT s.id, b.name, s.tier, s.status, s.submitted_at
--   FROM public.audit_submissions s
--   JOIN public.businesses b ON b.id = s.business_id
--   ORDER BY s.submitted_at DESC;
-- ════════════════════════════════════════════════════════════════════════
