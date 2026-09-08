-- =============================================================================
-- Migration 005: Schema Fixes (Status Constraint & PR URL)
--
-- 1. Updates valid_status constraint to include all runtime statuses used by code:
--    VALIDATED, VALIDATION_FAILED, DELIVERED, REJECTED, FAILED, FIX_READY
-- 2. Adds pr_url column to pipeline_runs if not already present
-- =============================================================================

-- 1. Update valid_status CHECK constraint
ALTER TABLE public.pipeline_runs DROP CONSTRAINT IF EXISTS valid_status;

ALTER TABLE public.pipeline_runs ADD CONSTRAINT valid_status CHECK (status IN (
    'CLASSIFYING',
    'WAITING_FOR_APPROVAL',
    'FIXING',
    'VALIDATED',
    'VALIDATION_FAILED',
    'DELIVERED',
    'STOPPED',
    'REJECTED',
    'FAILED',
    'FIX_READY',
    'DISMISSED'
));

-- 2. Add pr_url column
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS pr_url TEXT;
