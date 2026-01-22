# AGENT-PLANNING.md

> **Purpose**: Concise guide for AI planning agents working on architecture, feature design, and strategic decisions.

## Quick Context

**Project**: Miracle - Autonomous Coding Agent
**Type**: Meta-AI system (AI that generates and tests code autonomously)
**Core Philosophy**: "The difference between a chatbot and an agent is the loop"
**Architecture**: State Machine + Autonomous Agent Loop
**Language**: Python 3.11+
**Tech Stack**: Click/Rich CLI, OpenAI GPT (via custom client with Tenacity), PostgreSQL + pgvector, pytest/hypothesis, Docker, structlog

---

## System Architecture

### Core Flow
```
CLI (main.py) → Orchestrator → Agents (Planner/Coder/Tester/Reflector) → Memory System → PostgreSQL + pgvector
```

### State Machine
States: `INIT → PLANNING → CODING → TESTING → REFLECTING → (loop until SUCCESS or FAILED)`
- Max iterations: 15 (configurable, circuit breaker at 12)
- Checkpoints every 5 iterations
- All state persisted in database for resume capability

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Orchestrator | `src/orchestrator.py` | State machine controller, manages iterations, circuit breaker |
| Agents | `src/agents/*.py` | Planner, Coder, Tester, Reflector (all inherit from `BaseAgent`) |
| Memory | `src/memory/*.py` | Vector similarity search, pattern retrieval, failure analysis |
| LLM Interface | `src/llm/*.py` | OpenAI client with tool definitions, flexible model support |
| Sandbox | `src/sandbox/*.py` | Docker execution with AST + Bandit safety scanning |
| Testing | `src/testing/*.py` | Pytest/hypothesis test generation and execution |

---

## Planning Agent Responsibilities

1. **Design new features** fitting the state machine architecture
2. **Plan refactors** without breaking the orchestration loop
3. **Architect integrations** with new LLM providers or tools
4. **Design database schema** maintaining vector search capabilities
5. **Plan multi-agent coordination** strategies
6. **Design safety mechanisms** for code execution
7. **Create testing strategies** for autonomous systems

---

## Architectural Principles

1. **Separation of Concerns**: Each agent has single responsibility
2. **Stateless Agents**: All state lives in orchestrator or database
3. **Tool Use Pattern**: Agents interact via function calling
4. **Learning Through Memory**: Vector similarity search finds relevant past experiences
5. **Safety First**: Multi-layer (AST scanning, sandboxing, user approval)
6. **Configurable Everything**: YAML-driven, not hardcoded

---

## Database Schema (PostgreSQL + pgvector)

**Core tables:**
- `tasks` - Task tracking (UUID, description, status, iterations, final_code)
- `iterations` - Loop logs (task_id, iteration_num, phase, code_snapshot, test_results, error_message, reflection, hypothesis, tokens_used, duration_seconds)
- `failures` - Error memory (error_signature, error_type, solution, code_context, embedding vector(1536))
- `patterns` - Successful solutions (problem_type, code_template, test_template, usage_count, success_rate, embedding vector(1536))
- `metrics` - Performance data (task_id, metric_type, value, metadata)

**Vector search:**
- Model: `text-embedding-3-large` (1536 dimensions)
- Similarity: Cosine distance
- Threshold: 0.6-0.7 (configurable)
- Queries: "Find similar failures", "Find successful patterns for X"

---

## LLM Configuration

All models configurable via `config/openai.yaml`:
- Models per agent: `planner`, `coder`, `tester`, `reflector`
- Fallback sequence for reliability
- Parameters: temperature (0.2), max_tokens (4096), top_p

**Tool definitions** in `src/llm/tools.py`:
- Coder tools: `create_file`, `read_file`, `list_files`, etc.
- All tools defined as function-calling schemas
- Different agents can have different tool sets

---

## Configuration System

All behavior in YAML (not code):

| File | Purpose |
|------|---------|
| `config/settings.yaml` | System settings (max_iterations, checkpoint_frequency, log_level) |
| `config/openai.yaml` | LLM models and parameters |
| `config/database.yaml` | PostgreSQL connection and pool settings |
| `config/system_prompts.yaml` | Agent system prompts |
| `config/allowed_deps.json` | Dependency allowlist |
| `config/safety_rules.yaml` | AST patterns to block, approval triggers |

**Adding new config:** 1) Add to YAML, 2) Load in `ConfigLoader`, 3) Use in code. Always provide defaults and validate.

---

## Testing Strategy

**Current:** Minimal unit tests, no integration/e2e tests

**Recommended structure:**
```
tests/
├── unit/                 # Mock LLM calls, pytest fixtures
├── integration/          # Multi-component tests
├── e2e/                  # Real OpenAI API calls (slow, run nightly)
└── fixtures/             # Mock responses, sample tasks
```

**Key principles:** Mock LLM calls in unit tests, test state transitions exhaustively, property-based testing for safety, snapshot testing for code quality.

---

## Extension Points

### Adding New Agent Type
1. Create class inheriting from `BaseAgent` in `src/agents/`
2. Implement `async execute(self, context: dict) -> dict`
3. Add to `OrchestrationState` enum in `orchestrator.py`
4. Create state handler method in orchestrator
5. Add model to `config/openai.yaml`
6. Add system prompt to `config/system_prompts.yaml`

### Adding New Language Support
1. Create scaffolder in `src/projects/scaffolder.py`
2. Create Dockerfile for sandbox
3. Add test runner in `src/testing/test_runner.py`
4. Update safety rules in `config/safety_rules.yaml`

### Adding New LLM Provider
1. Create client wrapper in `src/llm/` matching OpenAI interface
2. Add provider config to YAML
3. Update orchestrator initialization to select client based on config

---

## Safety Architecture

Multi-layer protection:
1. **AST scanning** - Blocks eval, exec, __import__, dangerous modules
2. **Bandit scan** - SAST for security vulnerabilities
3. **User approval** - Required for network/subsystem access
4. **Docker sandbox** - CPU: 1 core, RAM: 1GB, Timeout: 5min, Network: disabled by default

---

## Key Metrics to Track

Success rate, avg iterations to success, token usage per task, execution time, safety violations per task, memory hit rate (similar failures found), code quality (Bandit scores, test coverage), user interventions per task.

---

## Planning Checklist

When planning features:
- [ ] Fits state machine architecture? Which state?
- [ ] LLM interaction pattern? New agent or extend existing? Tools needed?
- [ ] Learning from memory? What gets embedded? What retrieval queries?
- [ ] Safety implications? Dangerous operations? User approval?
- [ ] Configurable? Add to YAML with defaults?
- [ ] Testing strategy? Unit, integration, e2e?
- [ ] Database impact? New tables/columns? Migration? Indexes?
- [ ] Failure handling? Circuit breaker? Logging? Recovery?

---

## Architectural Decisions (Rationale)

1. **PostgreSQL + pgvector** - Single DB simpler than separate vector DB, ACID guarantees, pgvector sufficient for <100k embeddings
2. **Max 15 iterations** - Balance autonomy vs cost, prevents infinite loops
3. **Docker over subprocess** - Stronger isolation (filesystem, network, process), resource limits, cross-platform
4. **Function calling over prompt engineering** - Structured JSON output, better error handling, easier extensibility
5. **Separate agents** - Separation of concerns, different prompts per task, easier test/debug

---

## Files to Reference

- Full handoff: `autonomous_coding_agent_handoff.md` (1516 lines - comprehensive spec)
- Architecture: `ARCHITECTURE.md` (technical details)
- Functionality: `FUNCTIONALITY.md` (system behavior)
- Database: `scripts/init_db.sql` (schema)
- Config examples: `config/*.yaml`

---

## Success Criteria

1. ✅ Implementation plan clear and actionable
2. ✅ Architectural decisions documented with rationale
3. ✅ Database schema changes include migration scripts
4. ✅ Configuration backward compatible or migration provided
5. ✅ Testing strategy defined (unit, integration, e2e)
6. ✅ Safety implications analyzed
7. ✅ Extension points identified
8. ✅ Success metrics defined
9. ✅ Handoff document for execution agent complete

---

**Last Updated**: 2025-01-21
**Maintained By**: AI Planning Agents
**Related**: `AGENT-EXECUTION.md`, `ARCHITECTURE.md`, `FUNCTIONALITY.md`
