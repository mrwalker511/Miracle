-- Migration: add 'cancelled' to the tasks.status CHECK constraint
-- Run this against any existing database created before this change.

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_status_check
    CHECK (status IN ('planning', 'running', 'success', 'failed', 'paused', 'cancelled'));
