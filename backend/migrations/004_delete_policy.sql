-- =============================================================================
-- MIGRATION: 004_delete_policy
-- Adds a DELETE policy to the pipeline_runs table so users can delete their runs
-- =============================================================================

-- Allow users to delete pipeline runs if they own the repository
CREATE POLICY "Users can delete runs for their installed repos" ON pipeline_runs
FOR DELETE USING (
    EXISTS (
        SELECT 1 FROM installations
        WHERE installations.user_id = auth.uid()
          AND installations.repositories ? pipeline_runs.repo_full_name
    )
);
