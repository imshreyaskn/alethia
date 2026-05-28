-- =============================================================================
-- Migration 003: SaaS Readiness (Multi-tenant & RLS)
-- =============================================================================

-- 1. Create the installations table to map users to GitHub App installations
CREATE OR REPLACE FUNCTION get_user_id_from_github_login(github_login text)
RETURNS UUID
LANGUAGE sql SECURITY DEFINER
AS $$
  SELECT id FROM auth.users WHERE raw_user_meta_data->>'user_name' = github_login LIMIT 1;
$$;

CREATE TABLE IF NOT EXISTS installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Maps to Supabase auth.users
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- GitHub App installation ID
    installation_id BIGINT NOT NULL UNIQUE,
    
    -- JSONB array of repo full names e.g. '["drizzle-org/realive-test-target"]'
    repositories JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_installations_user_id ON installations(user_id);
CREATE INDEX IF NOT EXISTS idx_installations_github_id ON installations(installation_id);

-- Trigger to auto-update updated_at for installations
CREATE OR REPLACE TRIGGER set_installations_updated_at
    BEFORE UPDATE ON installations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2. Enable RLS on installations
ALTER TABLE installations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own installations" ON installations
    FOR SELECT USING (auth.uid() = user_id);

-- (The backend service uses the service_role key to INSERT/UPDATE, bypassing RLS)


-- 3. Enable RLS on pipeline_runs
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Allow users to view runs only for repositories they have installed the app on
CREATE POLICY "Users can view runs for their installed repos" ON pipeline_runs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM installations
            WHERE user_id = auth.uid()
            AND repositories ? repo_full_name
        )
    );

-- Allow backend service to do everything (handled automatically by service_role key)


-- 4. Enable RLS on fix_history
ALTER TABLE fix_history ENABLE ROW LEVEL SECURITY;

-- Allow users to view history only for runs they have access to
CREATE POLICY "Users can view history for their runs" ON fix_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM pipeline_runs
            WHERE pipeline_runs.id = fix_history.run_id
            AND EXISTS (
                SELECT 1 FROM installations
                WHERE user_id = auth.uid()
                AND repositories ? pipeline_runs.repo_full_name
            )
        )
    );
