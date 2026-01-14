# AUTONOMOUS CODING AGENT - Complete Implementation Specification

## Document Purpose
This is a complete handoff specification for Claude Code to implement an autonomous coding agent system. All architectural decisions, constraints, and implementation details are documented below.

---

## 1. PROJECT OVERVIEW

### Mission
Build an autonomous agent that:
- Accepts coding tasks as goals (not prompts)
- Writes code iteratively in a loop
- Generates and runs tests automatically
- Learns from failures using vector similarity
- Doesn't stop until code is functional or max iterations reached

### Core Philosophy
**"The difference between a chatbot and an agent is the loop."**

---

## 2. TECHNICAL STACK

### Core Technologies
| Component | Technology | Version/Notes |
|-----------|-----------|---------------|
| **Language** | Python | 3.11+ |
| **LLM Provider** | OpenAI API | Flexible - any model via API |
| **Database** | PostgreSQL | 14+ with pgvector extension |
| **Vector DB** | pgvector | Integrated into Postgres |
| **Embeddings** | OpenAI Embeddings API | text-embedding-3-large or ada-002 |
| **Testing** | pytest + hypothesis | Property-based testing |
| **Sandbox** | Docker | Dynamic container spawning via docker-py |
| **CLI** | Rich + Click | Interactive terminal UI |
| **Logging** | structlog | JSON structured logs |
| **Code Analysis** | Bandit + AST | Security scanning |

### Environment
- **Primary**: Linux VM (corporate environment)
- **Future**: Docker deployment ready
- **Execution**: Local initially, cloud-ready architecture

---

## 3. SYSTEM ARCHITECTURE

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLI INTERFACE                              │
│                                                                 │
│  • Rich terminal UI (progress bars, syntax highlighting)       │
│  • Interactive approval prompts (Y/N for dangerous ops)         │
│  • Real-time log streaming with filtering                      │
│  • Metrics dashboard (success rate, iterations, time)          │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ User Goals
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                                │
│                   (State Machine Core)                          │
│                                                                 │
│  Flow: INIT → PLANNING → CODING → TESTING → REFLECTING → LOOP  │
│                                                                 │
│  Responsibilities:                                              │
│  • Manage iteration counter (current/max)                       │
│  • Circuit breaker (warning at 12, hard stop at 15)            │
│  • State persistence (checkpoint to DB for resume)              │
│  • Coordinate agent handoffs                                    │
│  • Track metrics per iteration                                 │
│                                                                 │
└──┬────────┬─────────┬──────────┬─────────┬────────────────────┘
   │        │         │          │         │
   │        │         │          │         │
   ▼        ▼         ▼          ▼         ▼
┌─────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│PLAN │ │ CODE │ │  TEST  │ │REFLECT │ │  MEMORY  │
│ NER │ │  R   │ │  ER    │ │  OR    │ │ MANAGER  │
└─────┘ └──────┘ └────────┘ └────────┘ └──────────┘
   │        │         │          │         │
   │        │         │          │         │
   ▼        ▼         ▼          ▼         ▼
```

### Detailed Component Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  State Machine:                                         │     │
│  │  INIT → PLANNING → CODING → TESTING → REFLECTING       │     │
│  │         ↑_____________________|                         │     │
│  │                 (loop until success or max_iter)        │     │
│  └────────────────────────────────────────────────────────┘     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┬──────────────┐
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐
│   PLANNER    │ │  CODER   │ │  TESTER  │ │  REFLECTOR   │ │    MEMORY    │
│              │ │          │ │          │ │              │ │   MANAGER    │
│ • Decompose  │ │ • Write  │ │ • Generate│ │ • Parse err │ │              │
│   task       │ │   code   │ │   tests  │ │ • Find root │ │ • Postgres   │
│ • Create     │ │ • Use    │ │ • Execute│ │   cause     │ │   + pgvector │
│   subtasks   │ │   tools  │ │   pytest │ │ • Vector    │ │ • OpenAI     │
│ • Query past │ │ • Apply  │ │ • Capture│ │   search    │ │   embeddings │
│   patterns   │ │   patterns│   output  │ │   similar   │ │ • Store:     │
│              │ │          │ │ • Check  │ │   failures  │ │   - Tasks    │
│ OpenAI API   │ │ OpenAI   │ │   coverage│ │ • Generate │ │   - Iterations│
│ (flexible)   │ │  API     │ │          │ │   hypothesis│ │   - Failures │
│              │ │          │ │ pytest + │ │              │ │   - Patterns │
│              │ │          │ │hypothesis│ │ OpenAI API   │ │   - Metrics  │
└──────────────┘ └────┬─────┘ └──────────┘ └──────────────┘ └──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │   EXECUTOR   │
              │  (Sandbox)   │
              │              │
              │ • Docker     │
              │   container  │
              │ • Resource   │
              │   limits:    │
              │   - CPU: 1   │
              │   - RAM: 1GB │
              │   - Time:5min│
              │ • FS: /sandbox│
              │   only       │
              │ • Network:   │
              │   restricted │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │    SAFETY    │
              │   CHECKER    │
              │              │
              │ • AST parse  │
              │ • Bandit scan│
              │ • Block:     │
              │   - eval()   │
              │   - exec()   │
              │   - /__      │
              │ • Approve:   │
              │   - network  │
              │   - deps     │
              └──────────────┘
```

### Agent Interaction Flow

```
User Input: "Build a REST API for todo items with SQLite backend"
    ↓
┌───────────────────────────────────────────────────────────┐
│ ITERATION 1                                               │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  PLANNER:                                                 │
│  ├─ Query memory for similar "REST API" patterns         │
│  ├─ Break into subtasks:                                 │
│  │   1. Setup Flask app structure                        │
│  │   2. Create SQLite models                             │
│  │   3. Implement CRUD endpoints                         │
│  │   4. Add error handling                               │
│  └─ Generate initial code structure                      │
│                                                           │
│  CODER:                                                   │
│  ├─ Write Flask app with SQLite                          │
│  ├─ Use tool: create_file("app.py", code)               │
│  └─ Generate requirements.txt                            │
│                                                           │
│  TESTER:                                                  │
│  ├─ Generate pytest tests for each endpoint              │
│  ├─ Use hypothesis for property-based input testing      │
│  ├─ Execute in Docker sandbox                            │
│  └─ Result: FAILED - Import error: flask not found       │
│                                                           │
│  REFLECTOR:                                               │
│  ├─ Parse error: "ModuleNotFoundError: flask"            │
│  ├─ Root cause: Missing dependency                       │
│  ├─ Vector search: Similar failures found (3 matches)    │
│  ├─ Hypothesis: Need to install flask                    │
│  └─ Action: Request dependency approval                  │
│                                                           │
│  CLI PROMPT:                                              │
│  → "Agent requests to install: flask, flask-sqlalchemy"  │
│  → "Approve? [Y/n]"                                      │
│                                                           │
└───────────────────────────────────────────────────────────┘
    ↓ (User approves)
┌───────────────────────────────────────────────────────────┐
│ ITERATION 2                                               │
├───────────────────────────────────────────────────────────┤
│  Dependencies installed manually by user                  │
│  Tests re-run: FAILED - Missing table initialization      │
│  Reflector: Add db.create_all()                          │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ ITERATION 3                                               │
├───────────────────────────────────────────────────────────┤
│  Tests: PASSED ✓                                          │
│  Store success pattern in memory                          │
│  Mark task as COMPLETED                                   │
└───────────────────────────────────────────────────────────┘
```

---

## 4. DATABASE SCHEMA

### PostgreSQL + pgvector Schema

```sql
-- ============================================
-- SETUP: Enable pgvector extension
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: tasks
-- Main task tracking and lifecycle
-- ============================================
CREATE TABLE tasks (
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

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);

-- ============================================
-- TABLE: iterations
-- Detailed log of each loop cycle
-- ============================================
CREATE TABLE iterations (
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

CREATE INDEX idx_iterations_task ON iterations(task_id, iteration_number);
CREATE INDEX idx_iterations_phase ON iterations(phase);

-- ============================================
-- TABLE: failures
-- Failure memory for learning (with embeddings)
-- ============================================
CREATE TABLE failures (
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

CREATE INDEX idx_failures_type ON failures(error_type);
CREATE INDEX idx_failures_embedding ON failures USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- TABLE: patterns
-- Successful solution templates (reusable knowledge)
-- ============================================
CREATE TABLE patterns (
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

CREATE INDEX idx_patterns_type ON patterns(problem_type);
CREATE INDEX idx_patterns_embedding ON patterns USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_patterns_usage ON patterns(usage_count DESC);

-- ============================================
-- TABLE: metrics
-- Performance tracking for training data
-- ============================================
CREATE TABLE metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
    
    metric_type VARCHAR(50) NOT NULL,    -- 'duration', 'token_usage', 'success', 'error_rate'
    value FLOAT NOT NULL,
    metadata JSONB,                      -- Context-specific data
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_type ON metrics(metric_type);
CREATE INDEX idx_metrics_task ON metrics(task_id);
CREATE INDEX idx_metrics_time ON metrics(recorded_at DESC);

-- ============================================
-- TABLE: approvals
-- Track user approval decisions for learning
-- ============================================
CREATE TABLE approvals (
    approval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(task_id),
    iteration_id UUID REFERENCES iterations(iteration_id),
    
    approval_type VARCHAR(50) NOT NULL,  -- 'dependency', 'network', 'filesystem'
    request_details JSONB NOT NULL,      -- What was requested
    approved BOOLEAN NOT NULL,           -- User's decision
    reasoning TEXT,                      -- User's optional comment
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_approvals_type ON approvals(approval_type, approved);

-- ============================================
-- VIEWS: Useful queries for metrics
-- ============================================

-- Success rate by problem type
CREATE VIEW success_rate_by_type AS
SELECT 
    problem_type,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END), 3) as success_rate,
    ROUND(AVG(total_iterations), 1) as avg_iterations
FROM tasks
WHERE status IN ('success', 'failed')
GROUP BY problem_type;

-- Recent failures for dashboard
CREATE VIEW recent_failures AS
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
```

### Database Connection Config

```python
# config/database.yaml
database:
  host: localhost
  port: 5432
  name: autonomous_agent
  user: agent_user
  password: ${DB_PASSWORD}  # From environment
  
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  
  pgvector:
    dimension: 1536  # OpenAI embedding size
    index_lists: 100  # For IVFFlat index
```

---

## 5. FILE STRUCTURE

```
autonomous_agent/
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
│
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Postgres + pgvector setup
├── Dockerfile                    # Future: agent containerization
│
├── config/
│   ├── settings.yaml             # Main configuration
│   ├── database.yaml             # DB connection settings
│   ├── openai.yaml               # OpenAI API config (flexible)
│   ├── allowed_deps.json         # Curated dependency allowlist
│   ├── safety_rules.yaml         # AST scanning rules
│   └── system_prompts.yaml       # Agent prompts by phase
│
├── src/
│   ├── __init__.py
│   │
│   ├── main.py                   # Entry point CLI
│   ├── orchestrator.py           # Main state machine controller
│   ├── config_loader.py          # Load YAML configs
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py         # Abstract base class
│   │   ├── planner.py            # Task decomposition agent
│   │   ├── coder.py              # Code generation agent
│   │   ├── tester.py             # Test generation & execution
│   │   └── reflector.py          # Error analysis agent
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── openai_client.py      # OpenAI API wrapper (FLEXIBLE)
│   │   ├── tools.py              # Function/tool definitions
│   │   ├── prompts.py            # Prompt templates
│   │   └── token_counter.py      # Track usage
│   │
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── docker_executor.py    # Docker container management
│   │   ├── safety_checker.py     # AST + Bandit scanning
│   │   ├── resource_limits.py    # CPU/RAM/time constraints
│   │   └── sandbox_manager.py    # Coordinate execution
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── db_manager.py         # Postgres CRUD operations
│   │   ├── vector_store.py       # Embedding generation & search
│   │   ├── pattern_matcher.py    # Similarity search logic
│   │   └── failure_analyzer.py   # Analyze failure patterns
│   │
│   ├── testing/
│   │   ├── __init__.py
│   │   ├── test_generator.py     # Auto-generate pytest tests
│   │   ├── test_runner.py        # Execute tests in sandbox
│   │   └── coverage_analyzer.py  # Check test coverage
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── cli.py                # Rich terminal interface
│   │   ├── logger.py             # Structured logging
│   │   ├── progress.py           # Progress bars
│   │   └── approval_prompt.py    # Interactive Y/N prompts
│   │
│   └── utils/
│       ├── __init__.py
│       ├── metrics_collector.py  # Track all metrics
│       ├── state_saver.py        # Checkpoint/resume logic
│       └── circuit_breaker.py    # Stop infinite loops
│
├── tests/                        # Unit tests for the agent itself
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_agents/
│   ├── test_memory/
│   └── test_sandbox/
│
├── sandbox/                      # Isolated workspace for code execution
│   ├── .gitkeep
│   └── workspace/                # Per-task directories created here
│
├── logs/                         # Structured JSON logs
│   ├── agent.log
│   ├── execution.log
│   └── metrics.log
│
├── scripts/
│   ├── setup_db.py               # Initialize database schema
│   ├── install_pgvector.sh       # Setup pgvector extension
│   └── seed_patterns.py          # Pre-populate common patterns
│
└── docs/
    ├── architecture.md
    ├── api_reference.md
    └── examples/
        ├── rest_api_task.md
        └── data_pipeline_task.md
```

---

## 6. CORE CONFIGURATION FILES

### config/settings.yaml
```yaml
# Main system configuration
system:
  name: "Autonomous Coding Agent"
  version: "0.1.0"
  environment: "development"  # development, production

orchestrator:
  max_iterations: 15
  circuit_breaker:
    warning_threshold: 12
    hard_stop: 15
  checkpoint_interval: 5  # Save state every N iterations
  timeout_per_iteration: 600  # 10 minutes

sandbox:
  engine: "docker"
  workspace_root: "./sandbox/workspace"
  resource_limits:
    cpu_count: 1
    memory_mb: 1024
    execution_timeout: 300  # 5 minutes
    disk_quota_mb: 500
  network:
    enabled: false  # Require approval
    allowed_domains: []  # Populated after approval
  
safety:
  ast_scan: true
  bandit_scan: true
  block_operations:
    - "eval"
    - "exec"
    - "compile"
    - "__import__"
    - "open"  # Outside sandbox
  require_approval:
    - "network_request"
    - "subprocess"
    - "file_write_outside_sandbox"
    - "dependency_install"

dependencies:
  mode: "allowlist"  # allowlist, auto (future), manual
  allowlist_file: "config/allowed_deps.json"
  auto_approve: false

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # json, text
  outputs:
    - "console"
    - "file"
  file_path: "logs/agent.log"
  rotation: "100MB"

metrics:
  enabled: true
  collect:
    - "iteration_duration"
    - "token_usage"
    - "test_pass_rate"
    - "error_types"
    - "pattern_matches"
  export_interval: 60  # seconds
```

### config/openai.yaml
```yaml
# OpenAI API Configuration (FLEXIBLE)
openai:
  api_key: ${OPENAI_API_KEY}  # From environment
  organization: ${OPENAI_ORG_ID}  # Optional
  
  # Model selection - FLEXIBLE TO USE ANY OPENAI MODEL
  models:
    # Primary agent models
    planner: "gpt-4-turbo-preview"    # Can be: gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.
    coder: "gpt-4-turbo-preview"      # Can be: any chat completion model
    tester: "gpt-4-turbo-preview"     # Can be: any chat completion model
    reflector: "gpt-4-turbo-preview"  # Can be: any chat completion model
    
    # Embedding model
    embedding: "text-embedding-3-large"  # Can be: text-embedding-3-small, text-embedding-ada-002
  
  # API parameters
  temperature: 0.2  # Low for code generation
  max_tokens: 4096
  top_p: 1.0
  frequency_penalty: 0.0
  presence_penalty: 0.0
  
  # Rate limiting
  requests_per_minute: 50
  tokens_per_minute: 150000
  
  # Retry logic
  retry:
    max_attempts: 3
    backoff_factor: 2
    initial_delay: 1
  
  # Function calling
  function_calling:
    enabled: true
    parallel_calls: true
  
  # Streaming (future)
  streaming:
    enabled: false

# Model fallback strategy
fallback:
  enabled: true
  sequence:
    - "gpt-4-turbo-preview"
    - "gpt-4"
    - "gpt-3.5-turbo-16k"
```

### config/allowed_deps.json
```json
{
  "description": "Curated allowlist of dependencies the agent can request",
  "version": "1.0.0",
  "categories": {
    "web_frameworks": [
      "flask",
      "fastapi",
      "django",
      "starlette",
      "uvicorn"
    ],
    "data_processing": [
      "pandas",
      "numpy",
      "scipy",
      "polars"
    ],
    "databases": [
      "sqlalchemy",
      "psycopg2-binary",
      "pymongo",
      "redis"
    ],
    "testing": [
      "pytest",
      "pytest-cov",
      "hypothesis",
      "unittest-mock"
    ],
    "utilities": [
      "requests",
      "pydantic",
      "click",
      "rich",
      "python-dotenv"
    ],
    "async": [
      "aiohttp",
      "asyncio",
      "httpx"
    ]
  },
  "blocked": [
    "os",
    "subprocess",
    "pty",
    "pickle",
    "marshal"
  ],
  "notes": "Agent must request approval even for allowlisted packages"
}
```

### config/system_prompts.yaml
```yaml
# System prompts for each agent phase

planner:
  system: |
    You are a Planning Agent. Your job is to break down coding tasks into actionable subtasks.
    
    You have access to memory of past successful patterns. Query them first.
    
    Output a structured plan with:
    1. Problem analysis
    2. Subtasks (ordered)
    3. Dependencies needed
    4. Expected challenges
    
    Be specific and concrete. Avoid vague steps like "implement logic".
  
  user_template: |
    Task: {task_description}
    
    Goal: {goal}
    
    Similar past patterns found:
    {pattern_matches}
    
    Create a detailed implementation plan.

coder:
  system: |
    You are a Coding Agent. Write clean, functional, well-documented code.
    
    Rules:
    - Include docstrings
    - Add type hints
    - Handle errors gracefully
    - Follow PEP 8
    - No placeholder comments like "# TODO: implement"
    
    You have access to tools:
    - create_file(path, content)
    - read_file(path)
    - list_files()
    
    Write complete, executable code.
  
  user_template: |
    Plan: {plan}
    
    Current iteration: {iteration}
    Previous attempt errors: {previous_errors}
    
    Write the code to accomplish this task.

tester:
  system: |
    You are a Testing Agent. Generate comprehensive tests using pytest and hypothesis.
    
    Test categories to include:
    1. Happy path tests
    2. Edge cases (empty, null, boundary values)
    3. Error handling
    4. Property-based tests (hypothesis)
    
    Use fixtures, parametrize, and clear assertions.
    Aim for >80% coverage.
  
  user_template: |
    Code to test:
    {code}
    
    Function signatures:
    {signatures}
    
    Generate complete pytest test file.

reflector:
  system: |
    You are a Reflection Agent. Analyze test failures and determine root causes.
    
    Process:
    1. Parse error message and stack trace
    2. Identify error pattern (ImportError, TypeError, etc.)
    3. Determine root cause (not just symptom)
    4. Search memory for similar past failures
    5. Generate hypothesis for fix
    6. Suggest specific code changes
    
    Be precise. Avoid generic advice like "check your logic".
  
  user_template: |
    Test output:
    {test_results}
    
    Error:
    {error_message}
    
    Stack trace:
    {stack_trace}
    
    Code context:
    {code}
    
    Similar past failures:
    {similar_failures}
    
    Analyze and propose a fix.
```

---

## 7. KEY IMPLEMENTATION DETAILS

### 7.1 Orchestrator State Machine

```python
# Pseudo-code for orchestrator logic

class OrchestrationState(Enum):
    INIT = "init"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    REFLECTING = "reflecting"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"

class Orchestrator:
    def __init__(self, task_id, max_iterations=15):
        self.task_id = task_id
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.state = OrchestrationState.INIT
        self.context = {}  # Shared state across agents
        
    def run(self):
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            # Circuit breaker warning
            if self.current_iteration == 12:
                if not self.user_confirm_continue():
                    self.state = OrchestrationState.PAUSED
                    break
            
            # State machine progression
            if self.state == OrchestrationState.PLANNING:
                self.execute_planning_phase()
            elif self.state == OrchestrationState.CODING:
                self.execute_coding_phase()
            elif self.state == OrchestrationState.TESTING:
                success = self.execute_testing_phase()
                if success:
                    self.state = OrchestrationState.SUCCESS
                    break
                else:
                    self.state = OrchestrationState.REFLECTING
            elif self.state == OrchestrationState.REFLECTING:
                self.execute_reflection_phase()
                self.state = OrchestrationState.CODING  # Loop back
            
            # Checkpoint state
            if self.current_iteration % 5 == 0:
                self.save_checkpoint()
        
        if self.current_iteration >= self.max_iterations:
            self.state = OrchestrationState.FAILED
        
        return self.finalize()
```

### 7.2 OpenAI Client (FLEXIBLE)

```python
# Design to support ANY OpenAI model via configuration

class OpenAIClient:
    def __init__(self, config):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.models = config['models']  # Loaded from config/openai.yaml
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def chat_completion(self, agent_type, messages, tools=None):
        """
        Generic chat completion supporting ANY OpenAI model.
        
        Args:
            agent_type: "planner", "coder", "tester", "reflector"
            messages: List of message dicts
            tools: Optional tool definitions for function calling
        """
        model = self.models.get(agent_type, "gpt-4-turbo-preview")
        
        params = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**params)
        
        # Track tokens
        self.log_token_usage(response.usage)
        
        return response
    
    def embed(self, text):
        """Generate embedding using configured model."""
        model = self.models.get("embedding", "text-embedding-3-large")
        
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        
        return response.data[0].embedding
```

### 7.3 Safety Checker

```python
import ast
import bandit
from bandit.core import manager as bandit_manager

class SafetyChecker:
    BLOCKED_OPERATIONS = [
        "eval", "exec", "compile", "__import__",
        "open",  # Will check if path is in sandbox
    ]
    
    def check_code(self, code_str, sandbox_path):
        """
        Returns: (is_safe, issues, approval_needed)
        """
        issues = []
        approval_needed = []
        
        # AST analysis
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"], []
        
        # Check for blocked operations
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self.get_func_name(node)
                
                if func_name in self.BLOCKED_OPERATIONS:
                    if func_name == "open":
                        # Check if file path is in sandbox
                        if not self.is_path_in_sandbox(node, sandbox_path):
                            issues.append(f"Blocked: open() outside sandbox")
                    else:
                        issues.append(f"Blocked: {func_name}()")
                
                # Network operations need approval
                if func_name in ["requests.get", "urllib.request.urlopen", "socket.connect"]:
                    approval_needed.append(f"Network request: {func_name}")
        
        # Bandit scan
        bandit_issues = self.run_bandit(code_str)
        issues.extend(bandit_issues)
        
        is_safe = len(issues) == 0
        return is_safe, issues, approval_needed
```

### 7.4 Vector Similarity Search

```python
class VectorStore:
    def __init__(self, db_manager, openai_client):
        self.db = db_manager
        self.openai = openai_client
    
    def find_similar_failures(self, error_message, limit=5):
        """
        Find similar past failures using cosine similarity.
        """
        # Generate embedding for current error
        query_embedding = self.openai.embed(error_message)
        
        # Vector search in PostgreSQL
        query = """
            SELECT 
                failure_id,
                error_signature,
                root_cause,
                solution,
                1 - (embedding <=> %s::vector) AS similarity
            FROM failures
            WHERE fixed = TRUE
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        results = self.db.execute(query, (query_embedding, query_embedding, limit))
        return results
    
    def store_failure(self, error_data):
        """
        Store failure with embedding for future searches.
        """
        embedding = self.openai.embed(error_data['error_signature'])
        
        query = """
            INSERT INTO failures 
            (task_id, iteration_id, error_signature, error_type, 
             root_cause, solution, code_context, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING failure_id
        """
        
        return self.db.execute(query, (
            error_data['task_id'],
            error_data['iteration_id'],
            error_data['error_signature'],
            error_data['error_type'],
            error_data['root_cause'],
            error_data['solution'],
            error_data['code_context'],
            embedding
        ))
```

### 7.5 Test Generator (pytest + hypothesis)

```python
class TestGenerator:
    def generate_tests(self, code, function_signatures):
        """
        Generate pytest tests with hypothesis for property-based testing.
        """
        prompt = f"""
        Generate comprehensive pytest tests for this code:
        
        {code}
        
        Include:
        1. Standard test cases (happy path)
        2. Edge cases (empty, None, boundary values)
        3. Error handling tests
        4. Hypothesis property-based tests for functions with clear properties
        
        Example hypothesis test:
        ```python
        from hypothesis import given, strategies as st
        
        @given(st.integers(), st.integers())
        def test_addition_commutative(a, b):
            assert add(a, b) == add(b, a)
        ```
        
        Generate complete, runnable test file.
        """
        
        # Call LLM with tool use to create test file
        response = self.openai.chat_completion(
            agent_type="tester",
            messages=[{"role": "user", "content": prompt}],
            tools=self.get_file_tools()
        )
        
        return response
```

---

## 8. CRITICAL CONSTRAINTS & REQUIREMENTS

### 8.1 Iteration Limits
- **Max iterations**: 15 (HARD LIMIT)
- **Warning threshold**: 12 (prompt user to continue)
- **Checkpoint frequency**: Every 5 iterations
- **Timeout per iteration**: 10 minutes

### 8.2 Dependency Management
- **Mode**: Allowlist-only (no auto-install)
- **Process**: 
  1. Agent detects missing import
  2. Check against `allowed_deps.json`
  3. If allowed → CLI prompt user for approval
  4. User manually runs `pip install`
  5. Agent resumes with dependency available
- **Blocked**: Direct `subprocess.run(["pip", "install", ...])` calls

### 8.3 Code Safety Rules
| Operation | Action |
|-----------|--------|
| `eval()`, `exec()`, `compile()` | **BLOCK** - Never allow |
| `open()` outside `/sandbox` | **BLOCK** - Filesystem restricted |
| Network requests (`requests`, `urllib`) | **APPROVE** - Prompt user |
| `subprocess` calls | **APPROVE** - Prompt user |
| File writes in `/sandbox` | **ALLOW** - Safe zone |
| Import from `allowed_deps.json` | **APPROVE** - User must install |

### 8.4 Logging Requirements
All logs must be:
- **Structured JSON** format
- **Include context**: task_id, iteration, phase, timestamp
- **Separate files**: agent.log, execution.log, metrics.log
- **Rotation**: 100MB max per file
- **Fields to capture**:
  ```json
  {
    "timestamp": "2025-01-13T10:30:45.123Z",
    "level": "INFO",
    "task_id": "uuid",
    "iteration": 3,
    "phase": "testing",
    "event": "test_execution_complete",
    "data": {
      "passed": 8,
      "failed": 2,
      "duration": 2.3
    }
  }
  ```

### 8.5 Metrics to Track
| Metric | Type | Purpose |
|--------|------|---------|
| `iteration_duration` | Float | Optimize performance |
| `token_usage_per_phase` | Int | Cost tracking |
| `test_pass_rate` | Float | Success indicator |
| `error_type_frequency` | Counter | Pattern identification |
| `pattern_match_count` | Int | Memory effectiveness |
| `user_approval_rate` | Float | Trust calibration |
| `similarity_score_distribution` | Histogram | Vector search quality |

---

## 9. DOCKER SETUP

### docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: agent_postgres
    environment:
      POSTGRES_USER: agent_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: autonomous_agent
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Sandbox executor (future: run agent here)
  sandbox:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    container_name: agent_sandbox
    volumes:
      - ./sandbox:/workspace
    network_mode: none  # Isolated network
    mem_limit: 1g
    cpus: 1
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp

volumes:
  postgres_data:
```

### Dockerfile.sandbox
```dockerfile
FROM python:3.11-slim

# Install only essential packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 sandbox_user

# Set working directory
WORKDIR /workspace

# Copy only requirements (dependencies pre-installed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER sandbox_user

# Default command (overridden by executor)
CMD ["/bin/bash"]
```

---

## 10. REQUIREMENTS.TXT

```txt
# Core dependencies
python-dotenv==1.0.0
pyyaml==6.0.1

# OpenAI (flexible model support)
openai==1.12.0

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.25
pgvector==0.2.4

# Testing
pytest==8.0.0
pytest-cov==4.1.0
pytest-timeout==2.2.0
hypothesis==6.98.0

# Code analysis
bandit==1.7.6
pylint==3.0.3

# Docker
docker==7.0.0

# CLI & UI
click==8.1.7
rich==13.7.0
prompt-toolkit==3.0.43

# Logging
structlog==24.1.0
python-json-logger==2.0.7

# Utilities
tenacity==8.2.3  # Retry logic
tiktoken==0.6.0  # Token counting
```

---

## 11. CLI INTERFACE SPECIFICATION

### User Flow
```bash
$ python -m src.main

╔════════════════════════════════════════════════════════════╗
║        AUTONOMOUS CODING AGENT v0.1.0                      ║
╚════════════════════════════════════════════════════════════╝

? Enter your coding task: Build a REST API for managing todo items with SQLite

? Task type: [web_app] / data_pipeline / cli_tool / other: web_app

🔍 Searching memory for similar tasks... Found 3 patterns
📋 Initializing task (ID: abc-123)

╭─────────────────────────────────────────────────────────────╮
│  ITERATION 1/15                                             │
├─────────────────────────────────────────────────────────────┤
│  ⚡ Planning...                                             │
│     └─ Query past patterns [####------] 40%                │
│     └─ Generated 4 subtasks                                │
│  ✅ Planning complete (2.3s, 450 tokens)                    │
│                                                             │
│  ⚡ Coding...                                               │
│     └─ Writing app.py [##########] 100%                    │
│     └─ Writing models.py [##########] 100%                 │
│  ✅ Coding complete (5.1s, 1200 tokens)                     │
│                                                             │
│  ⚡ Testing...                                              │
│     └─ Generating tests [##########] 100%                  │
│     └─ Executing in sandbox...                             │
│  ❌ Tests failed: ModuleNotFoundError: flask                │
╰─────────────────────────────────────────────────────────────╯

⚠️  APPROVAL REQUIRED
┌─────────────────────────────────────────────────────────────┐
│  Agent requests to install dependencies:                    │
│    • flask (v3.0.0)                                         │
│    • flask-sqlalchemy (v3.1.1)                              │
│                                                             │
│  These packages are in the allowlist.                       │
│  Install manually: pip install flask flask-sqlalchemy       │
│                                                             │
│  Continue after installation? [Y/n]:                        │
└─────────────────────────────────────────────────────────────┘

[User installs and presses Y]

╭─────────────────────────────────────────────────────────────╮
│  ITERATION 2/15                                             │
├─────────────────────────────────────────────────────────────┤
│  ⚡ Testing (retry)...                                      │
│     └─ Executing in sandbox...                             │
│  ❌ Tests failed: RuntimeError: No application context      │
│                                                             │
│  ⚡ Reflecting...                                           │
│     └─ Error analysis [##########] 100%                    │
│     └─ Found 2 similar past failures                       │
│     └─ Root cause: Missing app.app_context()              │
│     └─ Hypothesis: Add context manager to tests            │
│  ✅ Reflection complete (3.2s, 680 tokens)                  │
╰─────────────────────────────────────────────────────────────╯

[... continues ...]

╭─────────────────────────────────────────────────────────────╮
│  ITERATION 5/15                                             │
├─────────────────────────────────────────────────────────────┤
│  ⚡ Testing...                                              │
│     └─ Executing in sandbox...                             │
│  ✅ All tests passed! (12/12)                               │
│                                                             │
│  📊 Coverage: 87%                                           │
╰─────────────────────────────────────────────────────────────╯

┌─────────────────────────────────────────────────────────────┐
│  ✅ TASK COMPLETED SUCCESSFULLY                             │
│                                                             │
│  📁 Files created:                                          │
│     • app.py (145 lines)                                    │
│     • models.py (38 lines)                                  │
│     • test_app.py (89 lines)                                │
│     • requirements.txt                                      │
│                                                             │
│  📊 Statistics:                                             │
│     • Iterations: 5 / 15                                    │
│     • Duration: 3m 42s                                      │
│     • Tokens used: 8,450                                    │
│     • Tests: 12 passed, 0 failed                            │
│                                                             │
│  💾 Pattern saved to memory for future tasks                │
└─────────────────────────────────────────────────────────────┘

? View generated code? [Y/n]:
```

### CLI Commands
```bash
# Start new task
python -m src.main

# Resume paused task
python -m src.main --resume <task_id>

# View task history
python -m src.main --history

# Show metrics dashboard
python -m src.main --metrics

# Configure settings
python -m src.main --config
```

---

## 12. IMPLEMENTATION PRIORITY

### Phase 1: Foundation (Week 1)
- [ ] Project structure setup
- [ ] Configuration loading system
- [ ] Database schema creation
- [ ] OpenAI client wrapper (flexible model support)
- [ ] Basic orchestrator state machine
- [ ] CLI skeleton with Rich

### Phase 2: Core Loop (Week 2)
- [ ] Planner agent with memory queries
- [ ] Coder agent with tool use
- [ ] Test generator (pytest + hypothesis)
- [ ] Test runner in subprocess (before Docker)
- [ ] Basic reflector (error parsing)

### Phase 3: Memory & Learning (Week 3)
- [ ] Vector store implementation
- [ ] Pattern matching system
- [ ] Failure indexing
- [ ] Similarity search
- [ ] Success pattern extraction

### Phase 4: Safety & Sandbox (Week 4)
- [ ] AST code scanner
- [ ] Bandit integration
- [ ] Docker executor
- [ ] Resource limits enforcement
- [ ] Approval prompt system

### Phase 5: Polish & Optimization (Week 5)
- [ ] Metrics collection & export
- [ ] Advanced CLI features
- [ ] Error handling & recovery
- [ ] Circuit breaker refinement
- [ ] Comprehensive testing

---

## 13. OPEN QUESTIONS FOR CLAUDE CODE

1. **OpenAI Model Selection**: Should we default to `gpt-4-turbo-preview` for all agents, or use different models per agent (e.g., gpt-3.5 for simpler tasks)?

2. **Embedding Model**: `text-embedding-3-large` (better quality, higher cost) vs `text-embedding-ada-002` (cheaper)?

3. **Docker vs Subprocess**: For initial implementation, should we:
   - Start with subprocess execution (simpler, faster to implement)
   - Go straight to Docker (more secure, production-ready)

4. **Bandit Severity**: What severity level should block execution?
   - Block only HIGH
   - Block MEDIUM and above
   - Warn on all, block on HIGH

5. **Pattern Storage**: Should we pre-seed the database with common patterns (REST API, data processing templates), or start with empty memory?

---

## 14. SUCCESS CRITERIA

The agent is considered successful when:

1. **Functional**: Can complete at least 3 different types of tasks:
   - REST API creation
   - Data processing script
   - CLI tool implementation

2. **Learning**: Demonstrates improvement:
   - Fewer iterations on similar tasks (2nd attempt < 1st attempt)
   - Successfully retrieves and applies past patterns

3. **Safe**: Zero security incidents:
   - No code execution outside sandbox
   - No unauthorized network access
   - No filesystem breaches

4. **Autonomous**: Minimal user intervention:
   - User only needed for approvals
   - No manual debugging required
   - Automatically recovers from common errors

5. **Observable**: Complete visibility:
   - Real-time progress tracking
   - Detailed logs for analysis
   - Metrics for performance evaluation

---

## 15. FUTURE ENHANCEMENTS (Post-MVP)

- **Multi-language support**: Extend beyond Python
- **Parallel execution**: Run multiple subtasks concurrently
- **Cost optimization**: Model selection based on task complexity
- **Human-in-the-loop**: Optional manual review after each iteration
- **Web UI**: Visual dashboard for monitoring
- **Cloud deployment**: Kubernetes orchestration
- **Collaborative learning**: Share patterns across agent instances
- **Reinforcement learning**: Fine-tune agent behavior based on success metrics

---

## 16. CONTACT & FEEDBACK

This specification is designed to be complete and actionable. If Claude Code encounters ambiguity or needs clarification:

1. **Configuration decisions**: Default to most secure/conservative option
2. **Technical choices**: Document assumption in comments
3. **Missing details**: Create reasonable placeholder, flag for review

**Implementation Philosophy**: Build iteratively, test continuously, document thoroughly.

---

**END OF HANDOFF DOCUMENT**
