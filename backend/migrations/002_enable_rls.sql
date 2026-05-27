-- =============================================================================
-- Migration 002: Enable Row Level Security (RLS)
--
-- WHY?
-- Supabase tables without RLS are fully public — anyone with the anon key
-- can read/write them. Since Realive's data is sensitive (CI logs, code diffs,
-- repo names), we lock it down.
--
-- HOW OUR AUTH WORKS:
-- - Our FastAPI backend uses the SERVICE ROLE key → bypasses RLS (full access ✅)
-- - The anon key (what a browser/public client would use) → blocked by RLS ✅
-- - No RLS policies are needed because we never expose Supabase directly to users.
--   All access goes through our backend API.
-- =============================================================================

-- Enable RLS on both tables
-- This blocks all access by default for non-service-role keys
ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fix_history   ENABLE ROW LEVEL SECURITY;

-- Verify: both should now show rls_enabled = true
SELECT tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('pipeline_runs', 'fix_history');
