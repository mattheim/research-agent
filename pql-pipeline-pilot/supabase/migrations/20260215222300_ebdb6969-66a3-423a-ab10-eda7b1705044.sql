
-- PQLs table
CREATE TABLE public.pqls (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT NOT NULL,
  company_name TEXT,
  product_usage_score NUMERIC,
  last_active_date DATE,
  raw_data JSONB DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'qualified', 'enriched', 'ready_for_review', 'approved', 'sent', 'rejected')),
  qualification_result TEXT,
  agent_metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.pqls ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to pqls" ON public.pqls FOR ALL USING (true) WITH CHECK (true);

-- Enrichments table
CREATE TABLE public.enrichments (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  pql_id UUID NOT NULL REFERENCES public.pqls(id) ON DELETE CASCADE,
  company_info JSONB DEFAULT '{}'::jsonb,
  key_contacts JSONB DEFAULT '[]'::jsonb,
  enrichment_source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.enrichments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to enrichments" ON public.enrichments FOR ALL USING (true) WITH CHECK (true);

-- Email drafts table
CREATE TABLE public.email_drafts (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  pql_id UUID NOT NULL REFERENCES public.pqls(id) ON DELETE CASCADE,
  to_email TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  proposed_offer TEXT,
  ai_reasoning TEXT,
  is_edited BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.email_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to email_drafts" ON public.email_drafts FOR ALL USING (true) WITH CHECK (true);

-- Activity log table
CREATE TABLE public.activity_log (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  pql_id UUID REFERENCES public.pqls(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to activity_log" ON public.activity_log FOR ALL USING (true) WITH CHECK (true);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_pqls_updated_at BEFORE UPDATE ON public.pqls FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER update_email_drafts_updated_at BEFORE UPDATE ON public.email_drafts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
