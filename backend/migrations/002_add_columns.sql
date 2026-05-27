-- Migration 002: Add columns needed for HITL gate, fixer, and validator
-- Run this in Supabase → SQL Editor

ALTER TABLE pipeline_runs
  ADD COLUMN IF NOT EXISTS failure_category      TEXT,
  ADD COLUMN IF NOT EXISTS classification_reason TEXT,
  ADD COLUMN IF NOT EXISTS test_file_content     TEXT,
  ADD COLUMN IF NOT EXISTS source_file_content   TEXT,
  ADD COLUMN IF NOT EXISTS user_hint             TEXT,
  ADD COLUMN IF NOT EXISTS patched_test_file     TEXT,
  ADD COLUMN IF NOT EXISTS patch_diff            TEXT,
  ADD COLUMN IF NOT EXISTS stop_reason           TEXT,
  ADD COLUMN IF NOT EXISTS validation_passed     BOOLEAN,
  ADD COLUMN IF NOT EXISTS validation_error      TEXT,
  ADD COLUMN IF NOT EXISTS retry_count           INT DEFAULT 0;
