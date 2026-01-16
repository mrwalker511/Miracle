# Database Architecture

> **Purpose**: PostgreSQL + pgvector schema design and query patterns.

---

## 5.1 Schema Design

```sql
-- Core task tracking
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    language VARCHAR(20) NOT NULL,  -- 'python' or 'node'
    status VARCHAR(20) NOT NULL,     -- 'running', 'success', 'failed', 'paused'
    current_iteration INT DEFAULT 0,
    max_iterations INT DEFAULT 15,
    workspace_path TEXT,
    checkpoint_state JSONB,          -- For resume functionality
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Iteration history (audit trail)
CREATE TABLE iterations (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_num INT NOT NULL,
    state VARCHAR(20) NOT NULL,      -- 'planning', 'coding', 'testing', 'reflecting'
    code_generated JSONB,            -- {filename: content}
    tests_run INT DEFAULT 0,
    tests_passed INT DEFAULT 0,
    tests_failed INT DEFAULT 0,
    error_messages JSONB,            -- [{error: ..., traceback: ...}]
    duration_seconds FLOAT,
    tokens_used INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Failure memory (for learning)
CREATE TABLE failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    error_type VARCHAR(100),         -- 'KeyError', 'TypeError', etc.
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    failing_code TEXT,
    solution TEXT,                   -- How it was fixed (filled later)
    embedding vector(1536),          -- OpenAI embedding
    created_at TIMESTAMP DEFAULT NOW()
);

-- Success patterns (for retrieval)
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL, -- 'rest_api', 'cli_tool', 'data_processing'
    task_description TEXT NOT NULL,
    solution_code JSONB NOT NULL,    -- {filename: content}
    implementation_notes TEXT,
    language VARCHAR(20),
    embedding vector(1536),          -- OpenAI embedding
    success_rate FLOAT DEFAULT 1.0,  -- How often this pattern worked
    times_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_num INT,
    metric_name VARCHAR(50),         -- 'duration', 'tokens', 'memory_usage'
    metric_value FLOAT,
    unit VARCHAR(20),                -- 'seconds', 'tokens', 'MB'
    created_at TIMESTAMP DEFAULT NOW()
);

-- User approval logs (for security audit)
CREATE TABLE approvals (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,  -- 'network_access', 'subprocess_call'
    approved BOOLEAN NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_iterations_task_id ON iterations(task_id, iteration_num);
CREATE INDEX idx_failures_task_id ON failures(task_id);
CREATE INDEX idx_patterns_task_type ON patterns(task_type);

-- Vector similarity indexes (IVFFlat for approximate nearest neighbor)
CREATE INDEX idx_failures_embedding ON failures
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_patterns_embedding ON patterns
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## 5.2 Query Patterns

**Common Queries**:

```sql
-- Get task with full iteration history
SELECT
    t.*,
    json_agg(i ORDER BY i.iteration_num) AS iterations
FROM tasks t
LEFT JOIN iterations i ON i.task_id = t.id
WHERE t.id = $1
GROUP BY t.id;

-- Find similar failures (vector similarity)
SELECT
    id,
    error_message,
    solution,
    1 - (embedding <=> $1::vector) AS similarity
FROM failures
WHERE 1 - (embedding <=> $1::vector) > 0.6
ORDER BY similarity DESC
LIMIT 5;

-- Get task success metrics
SELECT
    language,
    COUNT(*) AS total_tasks,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful,
    AVG(current_iteration) AS avg_iterations,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) AS avg_duration_seconds
FROM tasks
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY language;
```

---

## 5.3 Data Lifecycle

```
[Task Created]
  │
  ├─> Insert into tasks table (status='running')
  │
  ▼
[Each Iteration]
  │
  ├─> Insert into iterations table
  ├─> If failure: Insert into failures table
  └─> Insert into metrics table
  │
  ▼
[Task Completes]
  │
  ├─> Update tasks table (status='success'/'failed')
  ├─> If successful: Insert solution into patterns table
  └─> Final metrics insertion
  │
  ▼
[Retention Policy]
  │
  ├─> Iterations: Keep forever (audit trail)
  ├─> Failures: Keep successful solutions forever
  ├─> Metrics: Aggregate and archive after 1 year
  └─> Logs: Rotate after 100MB or 30 days
```