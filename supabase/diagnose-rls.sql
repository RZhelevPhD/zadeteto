-- ════════════════════════════════════════════════════════════════════════
-- DIAGNOSTIC: Why is anon INSERT into contact_messages failing?
-- Run this in Supabase SQL Editor (your normal logged-in session, not anon).
-- Returns 4 result sets — paste the output back to me.
-- ════════════════════════════════════════════════════════════════════════

-- 1. Confirm RLS is enabled on the table
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled,
  forcerowsecurity AS force_rls
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('contact_messages', 'reports', 'partner_applications', 'feedback_log', 'reviews', 'businesses');

-- 2. Show all policies on contact_messages with full details (roles, command, qual)
SELECT
  pol.polname AS policy_name,
  pol.polcmd AS command,           -- 'r'=SELECT, 'a'=INSERT, 'w'=UPDATE, 'd'=DELETE, '*'=ALL
  pol.polpermissive AS permissive,
  pg_get_expr(pol.polqual, pol.polrelid) AS using_expr,
  pg_get_expr(pol.polwithcheck, pol.polrelid) AS with_check_expr,
  ARRAY(
    SELECT rolname FROM pg_roles WHERE oid = ANY(pol.polroles)
  ) AS applies_to_roles
FROM pg_policy pol
JOIN pg_class cls ON cls.oid = pol.polrelid
JOIN pg_namespace ns ON ns.oid = cls.relnamespace
WHERE ns.nspname = 'public'
  AND cls.relname = 'contact_messages';

-- 3. Show table-level grants on contact_messages
SELECT
  grantee,
  privilege_type,
  is_grantable
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND table_name = 'contact_messages'
ORDER BY grantee, privilege_type;

-- 4. Try the INSERT manually as the anon role to see the exact error
-- This switches your editor session to anon temporarily
SET LOCAL ROLE anon;
INSERT INTO public.contact_messages (name, email, message)
VALUES ('SQL Editor Test', 'test@diag.invalid', 'Test from SQL editor as anon role');
RESET ROLE;
