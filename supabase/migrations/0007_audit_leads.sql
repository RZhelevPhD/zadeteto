-- Audit leads table for Google profile audit tool
CREATE TABLE IF NOT EXISTS audit_leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  business_name TEXT NOT NULL,
  google_maps_url TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  score INTEGER,
  answers JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Allow anonymous inserts (public audit tool)
ALTER TABLE audit_leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous insert" ON audit_leads
  FOR INSERT WITH CHECK (true);

-- Admin-only select
CREATE POLICY "Admin select only" ON audit_leads
  FOR SELECT USING (
    auth.jwt() ->> 'role' = 'service_role'
    OR auth.jwt() -> 'user_metadata' ->> 'role' = 'admin'
  );

-- Index for rate limiting (1 audit per email per day)
CREATE INDEX idx_audit_leads_email_date ON audit_leads (email, created_at DESC);
