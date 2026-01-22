# Architecture

Core architectural concepts for the Miracle autonomous coding agent.

---

## System Overview

```
CLI (main.py) → Orchestrator (State Machine) → Agents → Memory/Sandbox → PostgreSQL + pgvector
```

**Core Philosophy**: "The difference between a chatbot and an agent is the loop."

---

## State Machine

### States

```
INIT → PLANNING → CODING → TESTING → REFLECTING → (loop until SUCCESS or FAILED)
```

**State Transitions**:
- **INIT**: Setup workspace, load config
- **PLANNING**: Decompose task, query memory for patterns (runs once)
- **CODING**: Generate code using LLM tools
- **TESTING**: Generate and execute tests in Docker sandbox
- **REFLECTING**: Analyze failures, search for solutions (if tests fail)
- **SUCCESS**: Tests pass, save pattern
- **FAILED**: Max iterations (15) reached

### Loop Control

- **Max iterations**: 15 (configurable via `config/settings.yaml`)
- **Circuit breaker**: Warning at iteration 12, hard stop at 15
- **Checkpoints**: Every 5 iterations, state persisted to database for resume

---

## Core Components

### Orchestrator (`src/orchestrator.py`)

**Responsibilities**:
- State machine transitions
- Iteration counting and circuit breaker
- Checkpoint/resume coordination
- Agent context handoffs
- Metrics tracking (tokens, duration, pass rate)

**Key Methods**:
- `async run()`: Main loop
- `async _run_[state]_state()`: State handlers (one per state)
- `checkpoint_state()`: Persist to DB
- `increment_iteration()`: Track loop count

### Agent System (`src/agents/`)

All agents inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """Execute agent logic and return results"""
        pass
```

| Agent | Responsibility | Tools |
|-------|----------------|-------|
| **Planner** | Task decomposition, subtask creation | `search_success_patterns` |
| **Coder** | Code generation | `create_file`, `read_file`, `list_files` |
| **Tester** | Test generation and execution | `create_test_file`, `run_tests`, `get_coverage` |
| **Reflector** | Error analysis, fix generation | `search_similar_failures`, `pattern_match` |

**Key Principle**: Agents are stateless. All state lives in orchestrator or database.

---

## Data Flow

### Main Loop Flow

```
1. User submits task via CLI
2. INIT: Setup workspace, load context
3. PLANNING:
   - Planner decomposes task
   - Queries memory for similar patterns (vector search)
   - Returns implementation plan
4. CODING:
   - Coder generates code via tool calls
   - Creates files in workspace
5. TESTING:
   - Tester generates pytest + hypothesis tests
   - Executes in Docker sandbox
   - Collects results (JSON)
6. If tests pass → SUCCESS (save pattern, mark complete)
   If tests fail → REFLECTING:
   - Reflector analyzes errors
   - Searches memory for similar failures (vector search)
   - Generates fix hypothesis
   - Increment iteration
   - → Back to CODING (loop)
7. Repeat until tests pass or max_iterations reached
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
  ORDER BY embedding <=> new_error_embedding  -- cosine distance
  LIMIT 5
  ↓
Return similar failures with their solutions
  ↓
LLM uses retrieved solutions to generate fix hypothesis
```

---

## Database Architecture

**Database**: PostgreSQL 14+ with pgvector extension

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `tasks` | Task tracking | UUID, description, status, iterations, final_code |
| `iterations` | Loop logs | task_id, iteration_num, phase, code_snapshot, test_results, error_message, reflection, tokens_used, duration_seconds |
| `failures` | Error memory | error_signature, error_type, solution, code_context, embedding vector(1536) |
| `patterns` | Successful solutions | problem_type, code_template, test_template, usage_count, success_rate, embedding vector(1536) |
| `metrics` | Performance | task_id, metric_type, value, metadata |
| `approvals` | User decisions | approval_type, request_details, approved, reasoning |

### Vector Search

- **Model**: `text-embedding-3-large` (1536 dimensions)
- **Metric**: Cosine similarity (pgvector `<=>` operator)
- **Threshold**: 0.6-0.7 (configurable in `config/database.yaml`)
- **Indexes**: IVFFlat on `failures.embedding` and `patterns.embedding`

---

## LLM Integration

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

Tools are defined in `src/llm/tools.py` as OpenAI function calling schemas:

```python
CREATE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "create_file",
        "description": "Create a new file with content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    }
}
```

Different agents have access to different tool sets.

---

## Architectural Patterns

### 1. State Machine Pattern
Explicit state transitions with handlers per state. All state persisted for resume capability.

### 2. Agent Pattern
Single-responsibility agents with `BaseAgent` interface. Stateless - all state in orchestrator/database.

### 3. Tool Use Pattern
Agents interact with environment via OpenAI function calling. Structured JSON output.

### 4. Memory-Augmented AI
Vector similarity search retrieves past patterns and failures for learning.

### 5. Multi-Layer Safety
Defense in depth: AST scanning → Bandit SAST → User approval → Docker sandbox.

### 6. Configuration-Driven
All behavior in YAML, not code. Environment variable substitution supported.

---

## Architectural Decisions

### Why PostgreSQL + pgvector?
Single database simpler than separate vector DB. ACID guarantees. pgvector sufficient for <100k embeddings.

### Why 15 iterations max?
Balances autonomy vs cost. Prevents infinite loops. User can restart with refined description.

### Why Docker over subprocess?
Stronger isolation (filesystem, network, process). Resource limits. Cross-platform consistency.

### Why function calling over prompt engineering?
Structured JSON output. Better error handling. Easier extensibility.

### Why separate agents?
Separation of concerns. Different prompts per task. Easier to test and debug.

### Why stateless agents?
Simplifies state management. Enables horizontal scaling. State in database for resilience.

---

## Scaling Considerations

### Current Architecture (Single Node)

**Capacity**:
- Concurrent tasks: Limited by CPU cores (1 per Docker container)
- Database: pgvector handles <100k embeddings efficiently
- LLM API: Rate limited by OpenAI tier

**Bottlenecks**:
1. LLM API latency (1-10s per call)
2. Vector search (slower than plain SQL)
3. Docker container spawning (0.5-2s)

### Future Scaling (Multi-Node)

- Add orchestrator instances behind load balancer
- Redis pub/sub for task distribution
- Shared PostgreSQL database
- Vector index sharding by task_type or time
- Cache frequently retrieved patterns (Redis)
- Batch LLM calls where possible

---

## For More Details

- **Component deep-dive**: See [ARCHITECTURE.md](../../ARCHITECTURE.md)
- **System behavior**: See [FUNCTIONALITY.md](../../FUNCTIONALITY.md)
- **Database schema**: See `scripts/init_db.sql`
