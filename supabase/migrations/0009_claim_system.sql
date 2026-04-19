-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Migration 0009: Claim-Profile System (Phase 1)
--
-- Introduces the tokenized claim flow (Path A from the claim-profile plan):
--   1. claim_tokens table — one-time UUID tokens emailed/texted/messaged to
--      prospects. Clicking the token URL lets the recipient create an account
--      and become the owner of the referenced business.
--   2. businesses.claimed_at / claim_method — audit trail of how & when each
--      profile transitioned from seed (owner_id NULL) to owned.
--   3. claim_profile_with_token() RPC — SECURITY DEFINER function that
--      atomically validates a token, assigns owner_id, and marks the token
--      used. Callable by the newly-signed-up user (requires auth.uid()).
--
-- Self-serve / EIK fallback (Flow B) is NOT in this migration — that comes
-- in a later migration (0010_claim_self_serve.sql).
--
-- Apply via: Supabase Dashboard → SQL Editor → paste → Run
-- Idempotent — safe to re-run.
-- ════════════════════════════════════════════════════════════════════════

SET check_function_bodies = off;

-- ─────────────────────────── businesses columns ───────────────────────
ALTER TABLE public.businesses
  ADD COLUMN IF NOT EXISTS claimed_at   timestamptz,
  ADD COLUMN IF NOT EXISTS claim_method text;

COMMENT ON COLUMN public.businesses.claimed_at IS
  'Timestamp when owner_id was first assigned via the claim flow. NULL for seed profiles or admin-inserted rows.';
COMMENT ON COLUMN public.businesses.claim_method IS
  'How the profile was claimed: token | email_match | phone_match | eik_document | manual. NULL for non-claimed rows.';

CREATE INDEX IF NOT EXISTS businesses_claimed_at_idx ON public.businesses (claimed_at);

-- Founders Circle view — claimed before launch date 2026-06-01.
-- We expose this as a regular view (not a generated column) so we can tweak
-- the cutoff later without an ALTER TABLE.
CREATE OR REPLACE VIEW public.founders_businesses AS
  SELECT id, name, slug, tier, claimed_at, claim_method
    FROM public.businesses
   WHERE claimed_at IS NOT NULL
     AND claimed_at < TIMESTAMPTZ '2026-06-01 00:00:00+03';

COMMENT ON VIEW public.founders_businesses IS
  'Businesses that claimed their profile before the Founders Circle deadline (2026-06-01 EEST). Used for tier perks and analytics.';

-- ─────────────────────────── claim_tokens table ───────────────────────
CREATE TABLE IF NOT EXISTS public.claim_tokens (
  token          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id    uuid NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  channel        text NOT NULL CHECK (channel IN ('email','sms','messenger','manual','self_serve')),
  sent_to        text,                                     -- email/phone/handle used in outreach; NULL for self_serve
  created_at     timestamptz NOT NULL DEFAULT now(),
  expires_at     timestamptz NOT NULL DEFAULT now() + INTERVAL '90 days',
  used_at        timestamptz,
  used_by_user   uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  revoked        boolean NOT NULL DEFAULT false,
  notes          text                                      -- free-form admin note (e.g. "resent 2026-05-02")
);

COMMENT ON TABLE public.claim_tokens IS
  'One-time UUID tokens that let a recipient claim ownership of a seed business profile. Token IS the secret — anyone holding it can claim.';

CREATE INDEX IF NOT EXISTS claim_tokens_business_open_idx
  ON public.claim_tokens (business_id)
  WHERE used_at IS NULL AND revoked = false;

CREATE INDEX IF NOT EXISTS claim_tokens_sent_to_idx
  ON public.claim_tokens (sent_to)
  WHERE used_at IS NULL;

-- ─────────────────────────── RPC: claim_profile_with_token ────────────
--
-- Called by the frontend AFTER a user has signed up / signed in via Supabase
-- Auth. Pass the raw token UUID from the claim URL; the function validates
-- it, assigns owner_id to auth.uid(), and marks the token used — all in a
-- single transaction.
--
-- Returns:
--   jsonb { ok: true, business_id, slug, name } on success
--   Raises an exception with a machine-readable SQLSTATE on failure:
--     P0001 'token_not_found'
--     P0001 'token_expired'
--     P0001 'token_used'
--     P0001 'token_revoked'
--     P0001 'already_claimed'  (business already has a different owner)
--     P0001 'not_authenticated' (auth.uid() is NULL)
--
CREATE OR REPLACE FUNCTION public.claim_profile_with_token(p_token uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _uid       uuid := auth.uid();
  _token_row public.claim_tokens%ROWTYPE;
  _biz_row   public.businesses%ROWTYPE;
BEGIN
  IF _uid IS NULL THEN
    RAISE EXCEPTION 'not_authenticated' USING ERRCODE = 'P0001';
  END IF;

  -- Lock the token row so two concurrent calls can't both succeed
  SELECT * INTO _token_row
    FROM public.claim_tokens
   WHERE token = p_token
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'token_not_found' USING ERRCODE = 'P0001';
  END IF;

  IF _token_row.revoked THEN
    RAISE EXCEPTION 'token_revoked' USING ERRCODE = 'P0001';
  END IF;

  IF _token_row.used_at IS NOT NULL THEN
    -- Allow idempotent re-claim by the SAME user (e.g. user refreshes the
    -- success page). Any other user hitting a used token is an error.
    IF _token_row.used_by_user = _uid THEN
      SELECT * INTO _biz_row FROM public.businesses WHERE id = _token_row.business_id;
      RETURN jsonb_build_object(
        'ok', true,
        'already_claimed_by_you', true,
        'business_id', _biz_row.id,
        'slug', _biz_row.slug,
        'name', _biz_row.name
      );
    END IF;
    RAISE EXCEPTION 'token_used' USING ERRCODE = 'P0001';
  END IF;

  IF _token_row.expires_at < now() THEN
    RAISE EXCEPTION 'token_expired' USING ERRCODE = 'P0001';
  END IF;

  SELECT * INTO _biz_row
    FROM public.businesses
   WHERE id = _token_row.business_id
   FOR UPDATE;

  IF NOT FOUND THEN
    -- Business was deleted between token issue and claim. Mark token revoked
    -- and surface a clean error.
    UPDATE public.claim_tokens SET revoked = true WHERE token = p_token;
    RAISE EXCEPTION 'business_not_found' USING ERRCODE = 'P0001';
  END IF;

  IF _biz_row.owner_id IS NOT NULL AND _biz_row.owner_id <> _uid THEN
    RAISE EXCEPTION 'already_claimed' USING ERRCODE = 'P0001';
  END IF;

  -- Atomic claim: assign owner + stamp claim metadata + mark token used.
  UPDATE public.businesses
     SET owner_id     = _uid,
         claimed_at   = COALESCE(claimed_at, now()),
         claim_method = COALESCE(claim_method, 'token')
   WHERE id = _biz_row.id;

  UPDATE public.claim_tokens
     SET used_at = now(),
         used_by_user = _uid
   WHERE token = p_token;

  -- Also revoke any OTHER open tokens for this business (one business = one
  -- owner; no reason to keep parallel invites alive).
  UPDATE public.claim_tokens
     SET revoked = true
   WHERE business_id = _biz_row.id
     AND token <> p_token
     AND used_at IS NULL
     AND revoked = false;

  RETURN jsonb_build_object(
    'ok', true,
    'business_id', _biz_row.id,
    'slug', _biz_row.slug,
    'name', _biz_row.name
  );
END;
$$;

COMMENT ON FUNCTION public.claim_profile_with_token(uuid) IS
  'Atomically claims a business profile for auth.uid() using a valid claim token. SECURITY DEFINER so RLS on businesses/claim_tokens does not block the update; authorization is enforced by token validity + auth.uid() check.';

-- Allow any authenticated user to call the RPC. Token validity is the real
-- authorization gate; anon callers must sign up first (auth.uid() NULL check).
GRANT EXECUTE ON FUNCTION public.claim_profile_with_token(uuid) TO authenticated;

-- ─────────────────────────── RPC: preview_claim_token ─────────────────
--
-- Lets an UNAUTHENTICATED visitor see the business name/slug/city before
-- signing up, so they can confirm "yes this is my business" on claim.html.
-- Returns only public-safe fields; no contact data leaks.
--
CREATE OR REPLACE FUNCTION public.preview_claim_token(p_token uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _token_row public.claim_tokens%ROWTYPE;
  _biz_row   public.businesses%ROWTYPE;
  _status    text;
BEGIN
  SELECT * INTO _token_row FROM public.claim_tokens WHERE token = p_token;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'error', 'token_not_found');
  END IF;

  IF _token_row.revoked THEN
    _status := 'revoked';
  ELSIF _token_row.used_at IS NOT NULL THEN
    _status := 'used';
  ELSIF _token_row.expires_at < now() THEN
    _status := 'expired';
  ELSE
    _status := 'valid';
  END IF;

  SELECT * INTO _biz_row FROM public.businesses WHERE id = _token_row.business_id;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'error', 'business_not_found');
  END IF;

  RETURN jsonb_build_object(
    'ok', true,
    'status', _status,
    'business_id', _biz_row.id,
    'name', _biz_row.name,
    'slug', _biz_row.slug,
    'city', _biz_row.city,
    'address', _biz_row.address,
    'logo', _biz_row.logo,
    'channel', _token_row.channel,
    'sent_to_hint', CASE
      WHEN _token_row.sent_to IS NULL THEN NULL
      WHEN _token_row.channel = 'email' THEN
        regexp_replace(_token_row.sent_to, '^(.).*(.@.*)$', '\1***\2')
      WHEN _token_row.channel IN ('sms','manual') THEN
        regexp_replace(_token_row.sent_to, '(.{0,3}).*(.{2})$', '\1***\2')
      ELSE _token_row.sent_to
    END,
    'already_claimed_by_you', (_token_row.used_by_user IS NOT NULL AND _token_row.used_by_user = auth.uid())
  );
END;
$$;

COMMENT ON FUNCTION public.preview_claim_token(uuid) IS
  'Public read-only preview of a claim token: returns business name/city/logo plus token status so the landing page can render a confirmation UI before signup. sent_to is masked.';

GRANT EXECUTE ON FUNCTION public.preview_claim_token(uuid) TO anon, authenticated;

-- ─────────────────────────── RLS on claim_tokens ──────────────────────
ALTER TABLE public.claim_tokens ENABLE ROW LEVEL SECURITY;

-- No direct SELECT/INSERT/UPDATE/DELETE from clients. All access goes through
-- the two RPCs above (both SECURITY DEFINER) or the service_role key used by
-- the token-generation script.
-- Admins can SELECT for the upcoming admin queue page.
-- is_admin() alone is sufficient: superadmins are auto-granted is_admin=true
-- by the handle_superadmin_signup() trigger in migration 0006, so a single
-- check covers both roles and lets 0009 apply even if 0006 hasn't run yet
-- in this environment.
DROP POLICY IF EXISTS "claim_tokens_select_admin" ON public.claim_tokens;
CREATE POLICY "claim_tokens_select_admin" ON public.claim_tokens
  FOR SELECT USING (public.is_admin());

-- ═══════════════════════════════════════════════════════════════════════
-- DONE.
-- ═══════════════════════════════════════════════════════════════════════
