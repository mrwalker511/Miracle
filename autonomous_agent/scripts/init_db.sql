-- ============================================
-- AUTONOMOUS CODING AGENT - Database Schema
-- PostgreSQL + pgvector
-- ============================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: tasks
-- Main task tracking and lifecycle
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    description TEXT NOT NULL,           -- User's original goal
    goal TEXT NOT NULL,                  -- Structured goal statement
    status VARCHAR(20) NOT NULL          -- planning, running, success, failed, paused
        CHECK (status IN ('planning', 'running', 'success', 'failed', 'paused')),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_iterations INT DEFAULT 0,
    final_code TEXT,                     -- Successful code if completed
    final_tests TEXT,                    -- Generated tests
    metadata JSONB,                      -- Additional context (subtasks, etc.)

    CONSTRAINT reasonable_iterations CHECK (total_iterations <= 100)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);

-- ============================================
-- TABLE: iterations
-- Detailed log of each loop cycle
-- ============================================
CREATE TABLE IF NOT EXISTS iterations (
    iteration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    iteration_number INT NOT NULL,
    phase VARCHAR(20) NOT NULL           -- planning, coding, testing, reflecting
        CHECK (phase IN ('planning', 'coding', 'testing', 'reflecting')),

    -- Code state
    code_snapshot TEXT,                  -- Code at this iteration
    test_code TEXT,                      -- Generated tests

    -- Execution results
    test_results JSONB,                  -- pytest output (passed, failed, errors)
    test_passed BOOLEAN,
    error_message TEXT,                  -- If tests failed
    stack_trace TEXT,

    -- Reflection
    reflection TEXT,                     -- LLM's analysis
    hypothesis TEXT,                     -- What to try next

    -- Metrics
    tokens_used INT,                     -- OpenAI tokens this iteration
    duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_iteration_number CHECK (iteration_number > 0)
);

CREATE INDEX IF NOT EXISTS idx_iterations_task ON iterations(task_id, iteration_number);
CREATE INDEX IF NOT EXISTS idx_iterations_phase ON iterations(phase);

-- ============================================
-- TABLE: failures
-- Failure memory for learning (with embeddings)
-- ============================================
CREATE TABLE IF NOT EXISTS failures (
    failure_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    iteration_id UUID REFERENCES iterations(iteration_id) ON DELETE CASCADE,

    -- Error classification
    error_signature TEXT NOT NULL,       -- Normalized error pattern (e.g., "ImportError: module 'X'")
    error_type VARCHAR(100) NOT NULL,    -- ImportError, AttributeError, etc.
    full_error TEXT,                     -- Complete error message

    -- Analysis
    root_cause TEXT,                     -- LLM's determination
    solution TEXT,                       -- What fixed it
    code_context TEXT,                   -- Relevant code snippet

    -- Vector search
    embedding vector(1536),              -- OpenAI embedding for similarity

    -- Metadata
    fixed BOOLEAN DEFAULT FALSE,         -- Was this eventually resolved?
    fix_iteration INT,                   -- Which iteration solved it
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_failures_type ON failures(error_type);
CREATE INDEX IF NOT EXISTS idx_failures_embedding ON failures USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- TABLE: patterns
-- Successful solution templates (reusable knowledge)
-- ============================================
CREATE TABLE IF NOT EXISTS patterns (
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_type VARCHAR(100) NOT NULL,  -- "REST API", "Data Processing", etc.
    description TEXT NOT NULL,           -- Human-readable summary

    -- Solution
    code_template TEXT NOT NULL,         -- Reusable code pattern
    test_template TEXT,                  -- Associated test pattern
    dependencies JSONB,                  -- Required packages

    -- Effectiveness tracking
    usage_count INT DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,      -- % of times it led to success
    last_used TIMESTAMP,

    -- Vector search
    embedding vector(1536),

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_success_rate CHECK (success_rate >= 0 AND success_rate <= 1)
);

CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(problem_type);
CREATE INDEX IF NOT EXISTS idx_patterns_embedding ON patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_patterns_usage ON patterns(usage_count DESC);

-- ============================================
-- TABLE: metrics
-- Performance tracking for training data
-- ============================================
CREATE TABLE IF NOT EXISTS metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,

    metric_type VARCHAR(50) NOT NULL,    -- 'duration', 'token_usage', 'success', 'error_rate'
    value FLOAT NOT NULL,
    metadata JSONB,                      -- Context-specific data
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_task ON metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(recorded_at DESC);

-- ============================================
-- TABLE: approvals
-- Track user approval decisions for learning
-- ============================================
CREATE TABLE IF NOT EXISTS approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id),
    iteration_id UUID REFERENCES iterations(iteration_id),

    approval_type VARCHAR(50) NOT NULL,  -- 'dependency', 'network', 'filesystem'
    request_details JSONB NOT NULL,      -- What was requested
    approved BOOLEAN NOT NULL,           -- User's decision
    reasoning TEXT,                      -- User's optional comment

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_type ON approvals(approval_type, approved);

-- ============================================
-- VIEWS: Useful queries for metrics
-- ============================================

-- Success rate by problem type
CREATE OR REPLACE VIEW success_rate_by_type AS
SELECT
    COALESCE((metadata->>'problem_type')::TEXT, 'unknown') as problem_type,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END), 3) as success_rate,
    ROUND(AVG(total_iterations), 1) as avg_iterations
FROM tasks
WHERE status IN ('success', 'failed')
GROUP BY (metadata->>'problem_type');

-- Recent failures for dashboard
CREATE OR REPLACE VIEW recent_failures AS
SELECT
    f.failure_id,
    f.error_type,
    f.error_signature,
    f.root_cause,
    f.fixed,
    t.description as task_description,
    f.created_at
FROM failures f
JOIN tasks t ON f.task_id = t.task_id
ORDER BY f.created_at DESC
LIMIT 20;

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agent_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agent_user;
