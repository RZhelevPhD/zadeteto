-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0005
-- Audit questionnaire system: submissions, answers, files, scores
--
-- WHY: Partners fill out tier-specific questionnaires (Levels 1–5).
-- Answers are stored as flexible JSONB. Uploaded files go to Supabase
-- Storage (bucket "audit-files", max 5 MB). After a video audit, our
-- auditor manually scores each question on a 0/4/6/8/10 scale.
-- The questionnaire for each tier is only visible after the partner
-- subscribes to that tier.
--
-- This migration is idempotent — re-running is a no-op.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────────────────────── ENUM: business_tier ──────────────────────
-- Add 'Ентърпрайз' to existing business_tier enum
-- ALTER TYPE ... ADD VALUE is idempotent in PG 13+ (IF NOT EXISTS)
ALTER TYPE business_tier ADD VALUE IF NOT EXISTS 'Ентърпрайз';

-- ─────────────────────────── ENUM: audit_submission_status ────────────
DO $$ BEGIN
  CREATE TYPE audit_submission_status AS ENUM (
    'draft',         -- партньорът попълва
    'submitted',     -- изпратен за преглед
    'under_review',  -- одиторът разглежда
    'scored',        -- оценките са вписани, чака одобрение
    'approved',      -- минал одита
    'rejected'       -- не е минал, може да подаде отново
  );
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ─────────────────────────── TABLE: audit_submissions ─────────────────
-- One row = one questionnaire submission for a specific tier.
-- A business can have at most one submission per tier.
CREATE TABLE IF NOT EXISTS public.audit_submissions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  tier        business_tier NOT NULL,
  status      audit_submission_status NOT NULL DEFAULT 'draft',
  submitted_at timestamptz,
  submitted_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_audit_submission_business_tier UNIQUE (business_id, tier)
);

COMMENT ON TABLE public.audit_submissions IS
  'Each row represents a partner''s questionnaire submission for one audit tier. One business = one submission per tier.';

-- Auto-bump updated_at
CREATE OR REPLACE TRIGGER audit_submissions_touch_updated_at
  BEFORE UPDATE ON public.audit_submissions
  FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- ─────────────────────────── TABLE: audit_answers ─────────────────────
-- Individual answers stored as JSONB for flexibility across field types.
-- question_key format: "L1_Q01", "L2_Q07", "L5_Q12" etc.
CREATE TABLE IF NOT EXISTS public.audit_answers (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id  uuid NOT NULL REFERENCES public.audit_submissions(id) ON DELETE CASCADE,
  question_key   text NOT NULL,
  answer_value   jsonb NOT NULL DEFAULT '{}',
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_audit_answer_per_question UNIQUE (submission_id, question_key)
);

COMMENT ON TABLE public.audit_answers IS
  'Flexible JSONB answers to audit questionnaire questions. One row per question per submission.';

CREATE OR REPLACE TRIGGER audit_answers_touch_updated_at
  BEFORE UPDATE ON public.audit_answers
  FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- ─────────────────────────── TABLE: audit_files ───────────────────────
-- Metadata for files uploaded to Supabase Storage bucket "audit-files".
-- Actual files live at: audit-files/{business_id}/{tier}/{question_key}/{filename}
CREATE TABLE IF NOT EXISTS public.audit_files (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id  uuid NOT NULL REFERENCES public.audit_submissions(id) ON DELETE CASCADE,
  question_key   text NOT NULL,
  storage_path   text NOT NULL,
  original_name  text NOT NULL,
  mime_type      text NOT NULL,
  size_bytes     integer NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT chk_audit_file_size CHECK (size_bytes > 0 AND size_bytes <= 5242880)
);

COMMENT ON TABLE public.audit_files IS
  'Metadata for files uploaded as part of audit questionnaires. Files stored in Supabase Storage bucket "audit-files", max 5 MB each.';

-- ─────────────────────────── TABLE: audit_scores ──────────────────────
-- Auditor manually scores each question after video audit.
-- Score scale: 0 (no evidence), 4 (critical gaps), 6 (minor gaps),
--              8 (meets standard), 10 (exceeds standard).
CREATE TABLE IF NOT EXISTS public.audit_scores (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id  uuid NOT NULL REFERENCES public.audit_submissions(id) ON DELETE CASCADE,
  question_key   text NOT NULL,
  score          smallint NOT NULL,
  auditor_note   text,
  scored_by      uuid NOT NULL REFERENCES auth.users(id) ON DELETE SET NULL,
  scored_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_audit_score_per_question UNIQUE (submission_id, question_key),
  CONSTRAINT chk_audit_score_values CHECK (score IN (0, 4, 6, 8, 10))
);

COMMENT ON TABLE public.audit_scores IS
  'Manual scores assigned by auditors after video audit. Scale: 0/4/6/8/10. Admin-only access.';

-- ─────────────────────────── INDEXES ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_submissions_business
  ON public.audit_submissions(business_id);

CREATE INDEX IF NOT EXISTS idx_audit_submissions_status
  ON public.audit_submissions(status);

CREATE INDEX IF NOT EXISTS idx_audit_answers_submission
  ON public.audit_answers(submission_id);

CREATE INDEX IF NOT EXISTS idx_audit_files_submission
  ON public.audit_files(submission_id);

CREATE INDEX IF NOT EXISTS idx_audit_scores_submission
  ON public.audit_scores(submission_id);

-- ─────────────────────────── RLS ──────────────────────────────────────
ALTER TABLE public.audit_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_answers     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_files       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_scores      ENABLE ROW LEVEL SECURITY;

-- ── audit_submissions policies ──

-- SELECT: owner of the business or admin
CREATE POLICY audit_submissions_select ON public.audit_submissions
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.businesses b
      WHERE b.id = audit_submissions.business_id
        AND b.owner_id = auth.uid()
    )
    OR public.is_admin()
  );

-- INSERT: owner of the business (authenticated)
CREATE POLICY audit_submissions_insert ON public.audit_submissions
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.businesses b
      WHERE b.id = audit_submissions.business_id
        AND b.owner_id = auth.uid()
    )
  );

-- UPDATE: owner can update only while draft; admin can always update
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
  )
  WITH CHECK (
    (
      EXISTS (
        SELECT 1 FROM public.businesses b
        WHERE b.id = audit_submissions.business_id
          AND b.owner_id = auth.uid()
      )
      AND status IN ('draft', 'submitted')
    )
    OR public.is_admin()
  );

-- ── audit_answers policies ──

-- SELECT: owner or admin
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
  );

-- INSERT: owner, only if submission is draft
CREATE POLICY audit_answers_insert ON public.audit_answers
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_answers.submission_id
        AND b.owner_id = auth.uid()
        AND s.status = 'draft'
    )
  );

-- UPDATE: owner while draft
CREATE POLICY audit_answers_update ON public.audit_answers
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_answers.submission_id
        AND b.owner_id = auth.uid()
        AND s.status = 'draft'
    )
  );

-- DELETE: owner while draft, or admin
CREATE POLICY audit_answers_delete ON public.audit_answers
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_answers.submission_id
        AND (
          (b.owner_id = auth.uid() AND s.status = 'draft')
          OR public.is_admin()
        )
    )
  );

-- ── audit_files policies ──

-- SELECT: owner or admin
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
  );

-- INSERT: owner, only if submission is draft
CREATE POLICY audit_files_insert ON public.audit_files
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_files.submission_id
        AND b.owner_id = auth.uid()
        AND s.status = 'draft'
    )
  );

-- DELETE: owner while draft, or admin
CREATE POLICY audit_files_delete ON public.audit_files
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.audit_submissions s
      JOIN public.businesses b ON b.id = s.business_id
      WHERE s.id = audit_files.submission_id
        AND (
          (b.owner_id = auth.uid() AND s.status = 'draft')
          OR public.is_admin()
        )
    )
  );

-- ── audit_scores policies (admin-only) ──

CREATE POLICY audit_scores_select ON public.audit_scores
  FOR SELECT TO authenticated
  USING (public.is_admin());

CREATE POLICY audit_scores_insert ON public.audit_scores
  FOR INSERT TO authenticated
  WITH CHECK (public.is_admin());

CREATE POLICY audit_scores_update ON public.audit_scores
  FOR UPDATE TO authenticated
  USING (public.is_admin());

CREATE POLICY audit_scores_delete ON public.audit_scores
  FOR DELETE TO authenticated
  USING (public.is_admin());

-- ─────────────────────────── GRANTS ───────────────────────────────────
-- Ensure anon and authenticated roles can interact with the new tables
-- (RLS policies enforce the actual access rules)
GRANT SELECT, INSERT, UPDATE    ON public.audit_submissions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audit_answers TO authenticated;
GRANT SELECT, INSERT, DELETE    ON public.audit_files       TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audit_scores TO authenticated;

-- ════════════════════════════════════════════════════════════════════════
-- DONE.
--
-- After running this migration, create the Storage bucket manually:
--   Supabase Dashboard → Storage → New Bucket
--   Name: audit-files
--   Public: OFF
--   Max file size: 5 MB (5242880 bytes)
--   Allowed MIME types: image/png, image/jpeg, application/pdf, image/svg+xml
--
-- Verification queries:
--   SELECT * FROM public.audit_submissions;
--   SELECT * FROM public.audit_answers;
--   SELECT * FROM public.audit_files;
--   SELECT * FROM public.audit_scores;
--   SELECT enumlabel FROM pg_enum WHERE enumtypid = 'business_tier'::regtype;
-- ════════════════════════════════════════════════════════════════════════
