# ARCHITECTURE.md

> **Purpose**: Technical architecture documentation for Autonomous Coding Agent system.

---

## System Overview

**High-Level Architecture**:
```
CLI → Orchestrator (State Machine) → Agents (Planner/Coder/Tester/Reflector) → Memory/Sandbox/Testing → PostgreSQL + pgvector + Docker
```

**Core Components**:
- **CLI Layer**: Click + Rich for interactive commands
- **Orchestrator**: State machine controller managing iteration loop
- **Agent Layer**: Four specialized agents with single responsibilities
- **LLM Interface**: OpenAI client with function calling, retry logic, token tracking
- **Memory System**: PostgreSQL + pgvector for vector similarity search
- **Sandbox System**: Docker containers with AST + Bandit safety scanning
- **Testing System**: Pytest/hypothesis generation and execution

---

## Architectural Patterns

### 1. State Machine Pattern
Orchestrator uses explicit state transitions: `INIT → PLANNING → CODING → TESTING → REFLECTING → (loop until SUCCESS or FAILED)`

### 2. Agent Pattern
Each agent inherits from `BaseAgent` with `async execute(context: dict) -> dict` interface. Stateless - all state in orchestrator/database.

### 3. Tool Use Pattern
Agents interact with environment via OpenAI function calling (create_file, read_file, list_files, etc.)

### 4. Memory-Augmented AI
Vector similarity search (pgvector) retrieves past patterns and failures for learning.

### 5. Multi-Layer Safety
AST scanning → Bandit SAST → User approval → Docker sandbox (defense in depth).

### 6. Configuration-Driven
All behavior in YAML, not code. Environment substitution supported.

---

## Component Architecture

### Orchestrator (`src/orchestrator.py`)
**Responsibilities**:
- State machine transitions and iteration management
- Circuit breaker (warning at 12, stop at 15)
- Checkpoint every 5 iterations (persist to DB)
- Coordinate agent handoffs via context dictionary
- Track metrics (tokens, duration, pass rate)

**Key Methods**:
- `async run()`: Main orchestration loop
- `async _run_[state]_state()`: State handlers (one per state)
- `checkpoint_state()`: Persist to database for resume
- `increment_iteration()`: Track loop count

### Agent System (`src/agents/`)

**BaseAgent Interface**:
```python
class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """Execute agent logic and return results"""
        pass
```

**Agents**:

| Agent | File | Responsibility | Tools |
|-------|------|----------------|-------|
| Planner | `planner.py` | Task decomposition, subtask creation | vector_search (memory) |
| Coder | `coder.py` | Code generation | create_file, read_file, list_files |
| Tester | `tester.py` | Test generation and execution | create_file, execute_tests |
| Reflector | `reflector.py` | Error analysis, fix generation | vector_search, pattern_match |

### LLM Interface (`src/llm/`)

**Components**:
- `openai_client.py`: Wrapper with retry (Tenacity), token tracking
- `tools.py`: Function calling definitions per agent
- `prompts.py`: System prompt templates
- `token_counter.py`: Usage tracking for cost optimization

**Configuration**: `config/openai.yaml` - models per agent, parameters, fallback sequence

### Memory System (`src/memory/`)

**Components**:
- `db_manager.py`: PostgreSQL CRUD operations, connection pooling
- `vector_store.py`: Embedding generation (OpenAI), similarity search
- `pattern_matcher.py`: Retrieve successful solutions for similar tasks
- `failure_analyzer.py`: Retrieve similar past errors

**Vector Search**:
- Model: text-embedding-3-large (1536 dimensions)
- Metric: Cosine similarity
- Threshold: 0.6-0.7 (configurable)

### Sandbox System (`src/sandbox/`)

**Components**:
- `docker_executor.py`: Container lifecycle management
- `safety_checker.py`: AST + Bandit scanning
- `resource_limits.py`: CPU/RAM/time enforcement
- `sandbox_manager.py`: Execution coordination

**Safety Layers**:
1. AST scanning - blocks eval, exec, __import__, dangerous modules
2. Bandit scan - SAST for vulnerabilities
3. User approval - network/subsystem access requires prompt
4. Docker isolation - CPU: 1 core, RAM: 1GB, timeout: 5min, network disabled

### Testing System (`src/testing/`)

**Components**:
- `test_generator.py`: Auto-generate pytest + hypothesis tests
- `test_runner.py`: Execute in sandbox, capture JSON results
- `coverage_analyzer.py`: Coverage checking and reporting

---

## Data Flow

### Main Loop Flow
```
1. User submits task via CLI
2. Orchestrator → INIT state (setup workspace)
3. Orchestrator → PLANNING state
   - Planner agent decomposes task
   - Queries memory for similar patterns
   - Returns implementation plan
4. Orchestrator → CODING state
   - Coder agent generates code using tools
   - Creates files in workspace
5. Orchestrator → TESTING state
   - Tester agent generates pytest tests
   - Executes in Docker sandbox
   - Collects results
6. If tests pass: → SUCCESS state, mark task complete
   If tests fail: → REFLECTING state
   - Reflector agent analyzes errors
   - Searches memory for similar failures
   - Generates fix hypothesis
   - Increments iteration counter
   - → Back to CODING state (loop)
7. Loop until tests pass or max_iterations (15) reached
```

### Memory Retrieval Flow
```
Error occurs → Reflector receives error message
  ↓
VectorStore generates embedding (text-embedding-3-large)
  ↓
Query PostgreSQL failures table:
  SELECT id, error_message, solution
  FROM failures
  ORDER BY embedding <=> new_error_embedding
  LIMIT 5
  ↓
Return similar failures with their solutions
  ↓
LLM uses retrieved solutions to generate fix hypothesis
```

---

## Database Architecture

**Database**: PostgreSQL 14+ with pgvector extension

**Core Tables** (detailed schema in `scripts/init_db.sql`):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| tasks | Task tracking | UUID, description, status, iterations, final_code |
| iterations | Loop logs | task_id, iteration_num, phase, code_snapshot, test_results, error_message, reflection, hypothesis, tokens_used, duration_seconds |
| failures | Error memory | error_signature, error_type, solution, code_context, embedding vector(1536) |
| patterns | Successful solutions | problem_type, code_template, test_template, usage_count, success_rate, embedding vector(1536) |
| metrics | Performance | task_id, metric_type, value, metadata |
| approvals | User decisions | approval_type, request_details, approved, reasoning |

**Indexes**:
- IVFFlat on `failures.embedding` and `patterns.embedding` (vector search)
- B-tree on status, created_at, task_id (common queries)

**Views**:
- `success_rate_by_type`: Aggregate metrics by problem type
- `recent_failures`: Dashboard query for latest errors

---

## LLM Integration Architecture

### OpenAI Client (`src/llm/openai_client.py`)

**Features**:
- Retry logic (Tenacity): exponential backoff, max 3 attempts
- Token tracking: per-call and cumulative
- Fallback sequence: primary → secondary models
- Error handling: rate limits, timeouts, API errors

**Configuration** (`config/openai.yaml`):
```yaml
models:
  planner: "gpt-4-turbo-preview"
  coder: "gpt-4-turbo-preview"
  tester: "gpt-4-turbo-preview"
  reflector: "gpt-4-turbo-preview"
  embedding: "text-embedding-3-large"

fallback_sequence:
  - "gpt-4-turbo-preview"
  - "gpt-4"
  - "gpt-3.5-turbo"

parameters:
  temperature: 0.2
  max_tokens: 4096
  top_p: 1.0
```

### Tool Definitions

**Coder Tools** (`src/llm/tools.py`):
- `create_file(path, content)`: Write file to workspace
- `read_file(path)`: Read file content
- `list_files(directory)`: List workspace files
- `delete_file(path)`: Remove file

**Tester Tools**:
- `create_test_file(path, content)`: Write test file
- `run_tests()`: Execute pytest in sandbox
- `get_coverage()`: Get coverage report

**Reflector Tools**:
- `search_similar_failures(error_message)`: Vector search
- `search_success_patterns(problem_type)`: Vector search

### System Prompts

Defined in `config/system_prompts.yaml`:
- `planner`: Task decomposition expert
- `coder`: Clean, testable code generator
- `tester`: Comprehensive test writer (pytest + hypothesis)
- `reflector`: Error analysis and solution finder

---

## Security Architecture

### Multi-Layer Protection

**Layer 1: AST Scanning** (`src/sandbox/safety_checker.py`)
- Blocks: `eval()`, `exec()`, `__import__`
- Dangerous modules: os, subprocess, pty, socket, sys
- Configurable via `config/safety_rules.yaml`

**Layer 2: Bandit SAST**
- Scans for SQL injection, hardcoded secrets, unsafe functions
- Configurable severity threshold (block HIGH, warn MEDIUM)

**Layer 3: User Approval**
- Required for: network access, subprocess calls, new dependencies
- Interactive Rich CLI prompts
- Track decisions in `approvals` table for learning

**Layer 4: Docker Sandbox**
- Resource limits: CPU 1 core, RAM 1GB, timeout 5 min
- Network disabled by default (approval required to enable)
- Filesystem: bind mount `/workspace` only
- Non-root user (uid 1000)
- Read-only filesystem (except workspace)

### Configuration

`config/safety_rules.yaml`:
```yaml
blocked_imports: [os, subprocess, pty, socket, sys, ...]
blocked_functions: [eval, exec, compile, ...]
approval_required: [requests, urllib, httpx, subprocess.run, ...]
```

`config/allowed_deps.json`:
- Curated allowlist of approved packages
- Version pinning for reproducibility
- Block unknown dependencies

---

## Scalability & Performance

### Current Architecture (Single Node)

**Capacity**:
- Concurrent tasks: Limited by CPU cores (1 per container)
- Database: pgvector handles <100k embeddings efficiently
- LLM API: Rate limited by OpenAI (tier-based)

**Bottlenecks**:
1. **LLM API latency**: Each agent call adds 1-10s
2. **Vector search**: O(log n) for IVFFlat index, still slower than plain SQL
3. **Docker overhead**: Container spawning takes 0.5-2s

### Future Scaling (Multi-Node)

**Horizontal Scaling**:
- Add orchestrator instances behind load balancer
- Redis pub/sub for task distribution
- Shared PostgreSQL database
- Vector index sharding (by task_type or time)

**Performance Optimizations**:
- Cache frequently retrieved patterns (Redis)
- Batch LLM calls where possible
- Pre-embed common patterns at startup
- Use faster embedding model (ada-002) for indexing, large model for queries

---

## Deployment Architecture

### Current: Single-Server Deployment

**Components on single host**:
```
┌─────────────────────────────────────┐
│  Single Linux Server               │
│                                   │
│  ┌─────────────────────────────┐   │
│  │  Python Application        │   │
│  │  - CLI                    │   │
│  │  - Orchestrator           │   │
│  │  - Agents                 │   │
│  └─────────────────────────────┘   │
│           │                         │
│  ┌────────▼───────────────────┐   │
│  │  PostgreSQL + pgvector     │   │
│  └─────────────────────────────┘   │
│           │                         │
│  ┌────────▼───────────────────┐   │
│  │  Docker Daemon            │   │
│  │  - Sandbox containers     │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Future: Kubernetes Deployment

**Pods**:
- `orchestrator-pod`: Stateless, scalable
- `database-pod`: PostgreSQL with persistent volume
- `vector-index-pod`: Optional dedicated vector search

**Services**:
- Load balancer for orchestrator replicas
- Internal service for database access

**Configuration Management**:
- ConfigMaps for YAML files
- Secrets for API keys and passwords

---

## Technical Decisions

### Past Decisions (Rationale)

| Decision | Why |
|----------|-----|
| **PostgreSQL + pgvector** | Single DB simpler than separate vector DB, ACID guarantees, pgvector sufficient for <100k embeddings |
| **Max 15 iterations** | Balance autonomy vs cost, prevents infinite loops, user can restart with more context |
| **Docker over subprocess** | Stronger isolation (filesystem, network, process), resource limits, cross-platform consistency |
| **Function calling over prompt engineering** | Structured JSON output, better error handling, easier extensibility |
| **Separate agents** | Separation of concerns, different prompts per task, easier test/debug |
| **Stateless agents** | Simplifies state management, enables horizontal scaling, state in database for resilience |
| **YAML configuration** | No code changes for tuning, environment substitution, version control friendly |

### Trade-offs

| Option | Chosen | Alternative | Trade-off |
|--------|---------|-------------|------------|
| Vector DB | pgvector | Pinecone/Milvus | pgvector is slower at scale but simpler deployment |
| Sandbox | Docker | gVisor/VM | VM is more secure but slower/heavier |
| Test Framework | pytest+hypothesis | unittest | hypothesis adds property-based testing power |
| LLM Provider | OpenAI | Anthropic/Local | OpenAI has best tool support but proprietary |

---

## Files to Reference

- **Implementation**: `AGENT-PLANNING.md`, `AGENT-EXECUTION.md`, `autonomous_coding_agent_handoff.md`
- **Functionality**: `FUNCTIONALITY.md` (system behavior)
- **Database**: `scripts/init_db.sql` (complete schema)
- **Configuration**: `config/*.yaml` (all config files)
- **Dependencies**: `DEPENDENCIES.md` (setup instructions)

---

**Last Updated**: 2025-01-21
**Purpose**: Technical architecture for developers and AI agents
