# AUTONOMOUS CODING AGENT - Implementation Specification

## Document Purpose
Complete handoff specification for implementing an autonomous coding agent system. This document contains all essential implementation details.

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

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python | 3.11+ |
| LLM Provider | OpenAI API | Flexible - any OpenAI-compatible model |
| Database | PostgreSQL | 14+ with pgvector extension |
| Vector DB | pgvector | Integrated into Postgres |
| Embeddings | OpenAI | text-embedding-3-large or ada-002 |
| Testing | pytest + hypothesis | Property-based testing |
| Sandbox | Docker | Dynamic container spawning via docker-py |
| CLI | Rich + Click | Interactive terminal UI |
| Logging | structlog | JSON structured logs |
| Code Analysis | Bandit + AST | Security scanning |

---

## 3. SYSTEM ARCHITECTURE

### High-Level Flow
```
CLI → Orchestrator (State Machine) → Agents (Planner/Coder/Tester/Reflector) → Memory System → PostgreSQL + pgvector
```

### Orchestrator State Machine
**States**: INIT → PLANNING → CODING → TESTING → REFLECTING → (loop until SUCCESS or FAILED)

**Key Features**:
- Max iterations: 15 (configurable)
- Circuit breaker: warning at 12, hard stop at 15
- Checkpoint every 5 iterations (persist to DB for resume)
- Track metrics per iteration (tokens, duration, pass rate)

### Agent Interaction Example
1. User: "Build a REST API for todo items with SQLite"
2. **PLANNER**: Decompose task, query memory for similar patterns
3. **CODER**: Generate code, use tools (create_file, read_file, list_files)
4. **TESTER**: Generate pytest tests, execute in Docker sandbox
5. **REFLECTOR** (if failed): Analyze errors, vector search for similar failures, generate fix hypothesis
6. Loop to CODING until tests pass or max iterations reached

---

## 4. DATABASE SCHEMA

### Core Tables
- **tasks**: Task tracking (UUID, description, status, iterations, final_code, final_tests)
- **iterations**: Loop logs (task_id, iteration_num, phase, code_snapshot, test_results, error_message, reflection, hypothesis, tokens_used, duration_seconds)
- **failures**: Error memory (error_signature, error_type, solution, code_context, embedding vector(1536))
- **patterns**: Successful solutions (problem_type, code_template, test_template, dependencies, usage_count, success_rate, embedding vector(1536))
- **metrics**: Performance data (task_id, metric_type, value, metadata)
- **approvals**: User approval tracking (approval_type, request_details, approved, reasoning)

### Vector Search
- **Model**: OpenAI text-embedding-3-large (1536 dimensions)
- **Similarity**: Cosine distance
- **Threshold**: 0.6-0.7 (configurable)
- **Queries**:
  - "Find similar past failures for this error"
  - "Find successful solutions to similar tasks"

### Indexes
- IVFFlat indexes on `failures.embedding` and `patterns.embedding` for vector search
- Standard indexes on status, created_at, task_id for common queries

**Full schema**: See `scripts/init_db.sql`

---

## 5. FILE STRUCTURE

```
autonomous_agent/
├── src/
│   ├── main.py                   # CLI entry point
│   ├── orchestrator.py           # State machine controller
│   ├── config_loader.py          # YAML config loading
│   ├── agents/                   # AI agents (BaseAgent subclass)
│   │   ├── base_agent.py         # Abstract base
│   │   ├── planner.py            # Task decomposition
│   │   ├── coder.py              # Code generation
│   │   ├── tester.py             # Test generation + execution
│   │   └── reflector.py          # Error analysis
│   ├── llm/
│   │   ├── openai_client.py      # OpenAI API wrapper (flexible)
│   │   ├── tools.py              # Function calling definitions
│   │   ├── prompts.py            # Prompt templates
│   │   └── token_counter.py      # Token usage tracking
│   ├── memory/
│   │   ├── db_manager.py         # PostgreSQL CRUD operations
│   │   ├── vector_store.py       # Embedding + similarity search
│   │   ├── pattern_matcher.py    # Similarity search logic
│   │   └── failure_analyzer.py   # Failure pattern analysis
│   ├── sandbox/
│   │   ├── docker_executor.py    # Docker container management
│   │   ├── safety_checker.py     # AST + Bandit scanning
│   │   ├── resource_limits.py    # CPU/RAM/time constraints
│   │   └── sandbox_manager.py    # Execution coordinator
│   ├── testing/
│   │   ├── test_generator.py     # Auto-generate pytest tests
│   │   ├── test_runner.py        # Execute tests in sandbox
│   │   └── coverage_analyzer.py  # Coverage checking
│   ├── projects/
│   │   └── scaffolder.py        # Language-specific project setup
│   ├── ui/
│   │   ├── cli.py               # Rich terminal UI
│   │   ├── logger.py            # Structured logging
│   │   ├── progress.py          # Progress bars
│   │   └── approval_prompt.py   # Interactive prompts
│   └── utils/
│       ├── circuit_breaker.py   # Loop prevention
│       ├── state_saver.py       # Checkpoint/resume
│       └── metrics_collector.py # Performance tracking
├── config/                      # YAML configuration files
│   ├── settings.yaml            # System settings
│   ├── database.yaml            # DB connection
│   ├── openai.yaml              # LLM models
│   ├── system_prompts.yaml      # Agent prompts
│   ├── allowed_deps.json        # Dependency allowlist
│   └── safety_rules.yaml        # AST scanning rules
├── scripts/                     # Setup/migration scripts
├── tests/                       # Unit/integration/e2e tests
├── sandbox/workspace/           # Code execution area
└── logs/                        # Structured logs
```

---

## 6. AGENT SYSTEM DESIGN

### Base Agent Interface
```python
class BaseAgent(ABC):
    def __init__(self, llm_client, config):
        self.llm_client = llm_client
        self.config = config

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """Execute agent logic and return results"""
        pass
```

### Agent Responsibilities

| Agent | Input | Output | Tools |
|-------|-------|--------|-------|
| Planner | Task description | Implementation plan, subtasks | Query memory (vector search) |
| Coder | Plan + feedback | Code files | create_file, read_file, list_files |
| Tester | Code files | Test files + results | create_file, execute_tests |
| Reflector | Test failures | Error analysis + fix hypothesis | vector_search, pattern_match |

### Tool Use Pattern
All agents use OpenAI function calling. Tools defined in `src/llm/tools.py`.

**Example Coder Tool**:
```python
{
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

---

## 7. SAFETY ARCHITECTURE

### Multi-Layer Protection

**Layer 1: AST Scanning**
- Blocks: `eval()`, `exec()`, `__import__`, dangerous modules (os, subprocess, pty, socket)
- Implemented in `src/sandbox/safety_checker.py`

**Layer 2: Bandit Security Scan**
- SAST for common vulnerabilities (SQL injection, hardcoded secrets, etc.)
- Configurable severity threshold

**Layer 3: User Approval**
- Required for: network access, subprocess execution, new dependencies
- Interactive prompts via Rich CLI

**Layer 4: Docker Sandbox**
- CPU: 1 core
- RAM: 1GB
- Timeout: 5 minutes
- Network: disabled (requires approval to enable)
- Filesystem: `/workspace` only (bind mount, non-root user)

### Configuration
All safety rules in `config/safety_rules.yaml`:
- `blocked_imports`: List of blocked modules
- `blocked_functions`: List of blocked function calls
- `approval_required`: List of operations requiring user approval

---

## 8. CONFIGURATION SYSTEM

All behavior is configurable via YAML (not code):

| File | Purpose | Key Settings |
|------|---------|--------------|
| `settings.yaml` | System settings | max_iterations, checkpoint_frequency, log_level |
| `openai.yaml` | LLM models | Model names per agent, parameters, fallback sequence |
| `database.yaml` | Database connection | Host, port, credentials, pool size |
| `system_prompts.yaml` | Agent prompts | System prompts for each agent type |
| `allowed_deps.json` | Dependency allowlist | Approved packages, blocked imports |
| `safety_rules.yaml` | Safety rules | AST patterns to block, approval triggers |

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `DB_PASSWORD`: PostgreSQL password

---

## 9. DOCKER SETUP

### Docker Compose (PostgreSQL + pgvector)
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: autonomous_agent
      POSTGRES_USER: agent_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
```

### Dockerfile.sandbox
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 sandbox_user
WORKDIR /workspace
USER sandbox_user
```

---

## 10. CLI INTERFACE

### Commands
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

### Features
- Rich terminal UI with progress bars
- Real-time log streaming with filtering
- Interactive approval prompts (Y/N for dangerous operations)
- Metrics dashboard (success rate, iterations, time)

---

## 11. TESTING FRAMEWORK

### Test Structure
```
tests/
├── unit/                 # Fast, isolated unit tests
│   ├── test_agents/      # Test each agent
│   ├── test_orchestrator.py
│   ├── test_memory/
│   └── test_sandbox/
├── integration/          # Multi-component tests
│   ├── test_full_loop.py # CODING → TESTING → REFLECTING
│   └── test_memory_retrieval.py
└── e2e/                  # End-to-end scenarios
    ├── test_simple_task.py    # "Write a function to add"
    ├── test_api_task.py       # "Build a REST API"
    └── test_node_task.py      # "Create a Node.js CLI"
```

### Testing Principles
- Mock LLM calls in unit tests (expensive, non-deterministic)
- Use pytest fixtures for database setup/teardown
- Test state transitions exhaustively
- Property-based testing for safety checker (hypothesis)
- Snapshot testing for generated code quality

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

## 13. OPEN QUESTIONS

1. **OpenAI Model Selection**: Should we default to `gpt-4-turbo-preview` for all agents, or use different models per agent (e.g., gpt-3.5 for simpler tasks)?
2. **Embedding Model**: `text-embedding-3-large` (better quality, higher cost) vs `text-embedding-ada-002` (cheaper)?
3. **Docker vs Subprocess**: Start with subprocess execution (simpler) or go straight to Docker (production-ready)?
4. **Bandit Severity**: What severity level should block execution? (HIGH only, MEDIUM+, warn all)
5. **Pattern Storage**: Pre-seed database with common patterns, or start with empty memory?

**Default decisions**: Use gpt-4-turbo-preview, text-embedding-3-large, subprocess initially (migrate to Docker), block HIGH severity, start with empty memory.

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

- Multi-language support (extend beyond Python)
- Parallel execution (run multiple subtasks concurrently)
- Cost optimization (model selection based on task complexity)
- Human-in-the-loop (optional manual review after each iteration)
- Web UI (visual dashboard for monitoring)
- Cloud deployment (Kubernetes orchestration)
- Collaborative learning (share patterns across agent instances)
- Reinforcement learning (fine-tune agent behavior based on success metrics)

---

## 16. FILES TO REFERENCE

- **Setup & Config**: `AGENT-PLANNING.md`, `AGENT-EXECUTION.md`
- **Architecture**: `ARCHITECTURE.md` (deep technical details)
- **Functionality**: `FUNCTIONALITY.md` (system behavior and flows)
- **Database**: `scripts/init_db.sql` (complete schema)
- **Dependencies**: `DEPENDENCIES.md` (setup instructions)
- **Configuration examples**: `config/*.yaml`

---

**END OF HANDOFF DOCUMENT**

**Last Updated**: 2025-01-21
**Purpose**: Complete specification for AI agents implementing the autonomous coding agent system
