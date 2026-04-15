-- Email leads table for homepage lead magnet (checklist PDF + future guides)
CREATE TABLE IF NOT EXISTS email_leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE email_leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous insert" ON email_leads
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Admin select only" ON email_leads
  FOR SELECT USING (
    auth.jwt() ->> 'role' = 'service_role'
    OR auth.jwt() -> 'user_metadata' ->> 'role' = 'admin'
  );

CREATE INDEX idx_email_leads_email ON email_leads (email);
CREATE INDEX idx_email_leads_created ON email_leads (created_at DESC);
