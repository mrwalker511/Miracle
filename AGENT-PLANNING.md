# AGENT-PLANNING.md

> **Purpose**: This document is for AI planning agents working on high-level architecture, feature design, and strategic decisions for the Autonomous Coding Agent project.

---

## 🎯 Quick Context

**Project**: Miracle - Autonomous Coding Agent
**Type**: Meta-AI system (an AI that generates and tests code autonomously)
**Core Philosophy**: "The difference between a chatbot and an agent is the loop"
**Main Pattern**: State Machine + Autonomous Agent Loop
**Languages**: Python 3.11+ (core), generates Python/Node.js code

---

## 📋 Planning Agent Responsibilities

When assigned to this project, planning agents should:

1. **Design new features** that fit the state machine architecture
2. **Plan refactors** without breaking the orchestration loop
3. **Architect integrations** with new LLM providers or tools
4. **Design database schema changes** that maintain vector search capabilities
5. **Plan multi-agent coordination** strategies
6. **Design safety mechanisms** for code execution
7. **Create testing strategies** for autonomous systems

---

## 🏗️ System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Entry Point                          │
│                   (src/main.py - Click)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                              │
│              (State Machine Controller)                      │
│                                                              │
│  States: INIT → PLANNING → CODING → TESTING → REFLECTING    │
│  Max Iterations: 15 (configurable)                           │
│  Circuit Breaker: Warning at 12, Stop at 15                  │
└─────┬────────┬────────┬────────┬──────────┬─────────────────┘
      │        │        │        │          │
      ▼        ▼        ▼        ▼          ▼
  ┌───────┐ ┌──────┐ ┌───────┐ ┌──────────┐ ┌─────────────┐
  │Planner│ │Coder │ │Tester │ │Reflector │ │Memory System│
  │Agent  │ │Agent │ │Agent  │ │Agent     │ │             │
  └───┬───┘ └───┬──┘ └───┬───┘ └────┬─────┘ └──────┬──────┘
      │         │        │          │               │
      └─────────┴────────┴──────────┴───────────────┤
                                                     │
                                                     ▼
                                    ┌─────────────────────────┐
                                    │ PostgreSQL + pgvector   │
                                    │ - Task tracking         │
                                    │ - Iteration logs        │
                                    │ - Failure patterns      │
                                    │ - Success patterns      │
                                    │ - Embeddings (1536-dim) │
                                    └─────────────────────────┘
```

### State Machine Flow

```
[INIT]
  │
  ├─> Set up workspace
  ├─> Load configuration
  └─> Transition to PLANNING
       │
       ▼
[PLANNING] (runs once)
  │
  ├─> Break down task into subtasks
  ├─> Query memory for similar patterns
  ├─> Create implementation plan
  └─> Transition to CODING
       │
       ▼
[CODING]
  │
  ├─> Generate code using LLM + tools
  ├─> Create files in workspace
  └─> Transition to TESTING
       │
       ▼
[TESTING]
  │
  ├─> Generate pytest tests
  ├─> Run in Docker sandbox
  ├─> Collect results
  └─> Tests pass? ──YES──> [SUCCESS] ✅
       │
       NO
       │
       ▼
[REFLECTING]
  │
  ├─> Analyze failures
  ├─> Search memory for similar errors
  ├─> Generate fix hypothesis
  ├─> Increment iteration counter
  └─> Counter < 15? ──YES──> [CODING] (loop)
       │
       NO
       │
       ▼
[FAILED] ❌
```

### Key Architectural Principles

1. **Separation of Concerns**: Each agent has a single responsibility
2. **Stateless Agents**: All state lives in the orchestrator or database
3. **Tool Use Pattern**: Agents interact with the environment via function calling
4. **Learning Through Memory**: Vector similarity search finds relevant past experiences
5. **Safety First**: Multi-layer safety (AST scanning, sandboxing, user approval)
6. **Configurable Everything**: YAML-driven configuration, not hardcoded values

---

## 🧩 Core Components

### 1. Orchestrator (`src/orchestrator.py`)
**Role**: State machine controller
**Key Decisions**:
- When to transition between states
- When to checkpoint (every 5 iterations)
- When to activate circuit breaker (12 iterations warning, 15 hard stop)
- How to handle user interruptions (pause/resume)

**Planning Considerations**:
- Adding new states requires updating `OrchestrationState` enum
- State transitions must be idempotent
- All state changes should be logged for debugging

### 2. Agent System (`src/agents/`)

#### Base Agent Pattern
All agents inherit from `BaseAgent`:
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

#### Agent Responsibilities

| Agent | Input | Output | LLM Model |
|-------|-------|--------|-----------|
| **Planner** | Task description | Implementation plan, subtasks | gpt-4-turbo-preview |
| **Coder** | Plan + feedback | Code files | gpt-4-turbo-preview |
| **Tester** | Code files | Test files + results | gpt-4-turbo-preview |
| **Reflector** | Test failures | Error analysis + fix hypothesis | gpt-4-turbo-preview |

**Planning Considerations**:
- New agents must implement the `BaseAgent` interface
- Agents communicate via context dictionaries (orchestrator manages)
- Agents should be stateless; state goes in database
- Tool definitions live in `src/llm/tools.py`

### 3. Memory System (`src/memory/`)

**Components**:
- `DatabaseManager`: CRUD operations on PostgreSQL
- `VectorStore`: Embedding generation + similarity search
- `PatternMatcher`: Retrieves similar successful solutions
- `FailureAnalyzer`: Retrieves similar past errors

**Database Schema** (PostgreSQL + pgvector):
```sql
-- Core tables
tasks         -- UUID, description, status, language, created_at, updated_at
iterations    -- task_id, iteration_num, state, code_generated, tests_run, passed
failures      -- UUID, task_id, error_message, stack_trace, embedding vector(1536)
patterns      -- UUID, task_type, solution_code, description, embedding vector(1536)
metrics       -- task_id, iteration_num, duration_seconds, tokens_used, pass_rate

-- Indexes
CREATE INDEX idx_failures_embedding ON failures USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_patterns_embedding ON patterns USING ivfflat (embedding vector_cosine_ops);
```

**Vector Similarity Search**:
- Embedding model: `text-embedding-3-large` (1536 dimensions)
- Similarity metric: Cosine similarity
- Retrieval threshold: 0.6-0.7 (configurable)
- Query types:
  - "Find similar past failures for this error"
  - "Find successful solutions to similar tasks"

**Planning Considerations**:
- Adding new retrieval patterns requires new embeddings
- Schema changes need migration scripts (`scripts/migrate_db.py`)
- Consider indexing strategy for large-scale deployments
- Vector search is expensive; cache frequently retrieved patterns

### 4. LLM Interface (`src/llm/`)

**Flexibility Principle**: Support ANY OpenAI-compatible model

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
  temperature: 0.2      # Low for deterministic code
  max_tokens: 4096
  top_p: 1.0
```

**Tool Definitions** (`src/llm/tools.py`):
```python
CODER_TOOLS = [
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
    },
    # ... more tools
]
```

**Planning Considerations**:
- Adding new tools requires updating tool definitions + handler functions
- Different agents can have different tool sets
- Tool validation happens before execution
- Consider rate limits for OpenAI API (tier-based)

### 5. Sandbox System (`src/sandbox/`)

**Multi-Layer Safety**:

```
User Code Request
  │
  ├─> Layer 1: AST Scanning (blocks eval, exec, __import__)
  ├─> Layer 2: Bandit Security Scan (SAST)
  ├─> Layer 3: User Approval Prompt (network/subprocess)
  └─> Layer 4: Docker Execution (resource limits, network disabled)
       │
       └─> Success or Sandboxed Failure
```

**Docker Container Specs**:
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 sandbox_user
WORKDIR /workspace
USER sandbox_user

# Resource limits (via Docker API):
# - CPU: 1 core
# - RAM: 1GB
# - Timeout: 5 minutes
# - Network: disabled (requires approval to enable)
# - Filesystem: /workspace only (bind mount)
```

**Planning Considerations**:
- Adding support for new languages requires new Docker images
- Resource limits should scale with task complexity
- Consider adding GPU support for ML tasks
- Network isolation is critical; approval flow must be robust

---

## 🔧 Configuration Architecture

**Configuration Philosophy**: All behavior is configurable via YAML, not code.

### Configuration Files

| File | Purpose | Key Settings |
|------|---------|--------------|
| `config/settings.yaml` | System settings | `max_iterations`, `checkpoint_frequency`, `log_level` |
| `config/openai.yaml` | LLM models | Model names, parameters, fallback sequence |
| `config/database.yaml` | Database connection | Host, port, credentials, pool size |
| `config/system_prompts.yaml` | Agent prompts | System prompts for each agent type |
| `config/allowed_deps.json` | Dependency allowlist | Approved packages, blocked imports |
| `config/safety_rules.yaml` | Safety rules | AST patterns to block, approval triggers |

### Example: Adding a New Configuration Option

1. **Define in YAML**:
```yaml
# config/settings.yaml
orchestrator:
  max_iterations: 15
  checkpoint_frequency: 5
  enable_parallel_testing: false  # NEW OPTION
```

2. **Load in Code**:
```python
# src/config_loader.py
class Config:
    def __init__(self, config_dir: str):
        self.settings = self._load_yaml("settings.yaml")
        self.enable_parallel_testing = self.settings["orchestrator"]["enable_parallel_testing"]
```

3. **Use in Orchestrator**:
```python
if self.config.enable_parallel_testing:
    await self.run_tests_parallel()
```

**Planning Considerations**:
- Configuration changes should be backward compatible
- Provide sensible defaults for new options
- Document configuration options in `autonomous_agent/README.md`
- Validate configuration on load (JSON schema)

---

## 🧪 Testing Strategy

### Current State
- Unit tests: Minimal coverage in `autonomous_agent/tests/`
- Integration tests: None
- End-to-end tests: Manual testing only

### Recommended Testing Architecture

```
tests/
├── unit/                       # Fast, isolated unit tests
│   ├── test_agents/
│   │   ├── test_planner.py
│   │   ├── test_coder.py
│   │   ├── test_tester.py
│   │   └── test_reflector.py
│   ├── test_orchestrator.py
│   ├── test_memory/
│   │   ├── test_vector_store.py
│   │   └── test_db_manager.py
│   └── test_sandbox/
│       ├── test_safety_checker.py
│       └── test_docker_executor.py
│
├── integration/                # Multi-component tests
│   ├── test_full_loop.py       # CODING → TESTING → REFLECTING
│   ├── test_memory_retrieval.py
│   └── test_llm_integration.py
│
├── e2e/                        # End-to-end scenarios
│   ├── test_simple_task.py     # "Write a function to add two numbers"
│   ├── test_api_task.py        # "Build a REST API"
│   └── test_node_task.py       # "Create a Node.js CLI"
│
└── fixtures/
    ├── mock_llm_responses.json
    ├── sample_tasks.json
    └── expected_outputs/
```

**Testing Principles**:
1. **Mock LLM calls** in unit tests (expensive and non-deterministic)
2. **Use pytest fixtures** for database setup/teardown
3. **Test state transitions** exhaustively (orchestrator is critical)
4. **Property-based testing** for safety checker (hypothesis library)
5. **Snapshot testing** for generated code quality

**Planning Considerations**:
- CI/CD pipeline needs PostgreSQL + pgvector (Docker Compose)
- Integration tests should run against real OpenAI API (with budget limits)
- E2E tests are slow; run nightly, not on every commit
- Maintain test fixtures for common task types

---

## 🔌 Extension Points

### Adding a New Agent Type

**Example**: Adding a `DocumenterAgent` to generate documentation

1. **Create agent class**:
```python
# src/agents/documenter.py
from src.agents.base_agent import BaseAgent

class DocumenterAgent(BaseAgent):
    async def execute(self, context: dict) -> dict:
        code_files = context.get("code_files")

        prompt = self._build_prompt(code_files)
        response = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=self.config.models.documenter
        )

        return {"documentation": response.choices[0].message.content}

    def _build_prompt(self, code_files: list[str]) -> str:
        return f"Generate documentation for: {code_files}"
```

2. **Add to orchestrator**:
```python
# src/orchestrator.py
class OrchestrationState(Enum):
    # ... existing states
    DOCUMENTING = "documenting"

async def _run_documenting_state(self):
    documenter = DocumenterAgent(self.llm_client, self.config)
    result = await documenter.execute(self.context)
    self.context["documentation"] = result["documentation"]
    return OrchestrationState.SUCCESS
```

3. **Configure LLM**:
```yaml
# config/openai.yaml
models:
  documenter: "gpt-4-turbo-preview"
```

4. **Add system prompt**:
```yaml
# config/system_prompts.yaml
documenter: |
  You are an expert technical writer. Generate clear, comprehensive documentation.
```

### Adding Support for a New Language

**Example**: Adding Go support

1. **Create scaffolder**:
```python
# src/projects/scaffolder.py
class GoScaffolder:
    def scaffold(self, workspace: Path, task_description: str):
        # Create go.mod
        # Create main.go
        # Create tests/
```

2. **Update Docker image**:
```dockerfile
# Dockerfile.sandbox.go
FROM golang:1.21
RUN useradd -m -u 1000 sandbox_user
WORKDIR /workspace
USER sandbox_user
```

3. **Add test execution**:
```python
# src/testing/test_runner.py
class GoTestRunner:
    def run_tests(self, workspace: Path) -> TestResult:
        # Execute: go test ./...
```

4. **Update safety rules**:
```yaml
# config/safety_rules.yaml
go:
  blocked_imports:
    - "os/exec"
    - "syscall"
  approval_required:
    - "net/http"
```

### Adding a New LLM Provider

**Example**: Adding Anthropic Claude support

1. **Create client**:
```python
# src/llm/anthropic_client.py
from anthropic import Anthropic

class AnthropicClient:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    async def chat_completion(self, messages, model, tools=None):
        # Map OpenAI-style calls to Anthropic API
```

2. **Add configuration**:
```yaml
# config/llm_provider.yaml
provider: "anthropic"  # or "openai"
anthropic:
  models:
    planner: "claude-3-opus-20240229"
    coder: "claude-3-opus-20240229"
```

3. **Update orchestrator**:
```python
# src/orchestrator.py
def _initialize_llm_client(self):
    if self.config.llm_provider == "anthropic":
        return AnthropicClient(self.config.anthropic_api_key)
    else:
        return OpenAIClient(self.config.openai_api_key)
```

---

## 📊 Key Metrics to Track

When planning features, consider tracking:

1. **Success Rate**: % of tasks completed within max_iterations
2. **Average Iterations to Success**: Mean iterations before passing tests
3. **Token Usage**: Total tokens per task (cost optimization)
4. **Execution Time**: Wall-clock time per task
5. **Safety Violations**: # of blocked operations per task
6. **Memory Hit Rate**: % of reflections that found similar past failures
7. **Code Quality**: Bandit severity scores, test coverage %
8. **User Interventions**: # of approval prompts per task

**Database Storage**:
```sql
-- metrics table
CREATE TABLE metrics (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    iteration_num INT,
    duration_seconds FLOAT,
    tokens_used INT,
    tests_passed INT,
    tests_failed INT,
    safety_violations INT,
    memory_hits INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Feature Planning Checklist

When planning a new feature:

- [ ] **Does it fit the state machine architecture?**
  - Which state does it belong to?
  - Does it require a new state?

- [ ] **What's the LLM interaction pattern?**
  - New agent or extend existing?
  - What tools does it need?

- [ ] **How does it learn from memory?**
  - What gets embedded?
  - What retrieval queries are needed?

- [ ] **What are the safety implications?**
  - New dangerous operations?
  - Requires user approval?

- [ ] **Is it configurable?**
  - Add to YAML config
  - Provide sensible defaults

- [ ] **How will it be tested?**
  - Unit tests for logic
  - Integration tests for state transitions
  - E2E tests for user workflows

- [ ] **What's the database impact?**
  - New tables or columns?
  - Migration script needed?
  - Index requirements?

- [ ] **How does it handle failures?**
  - Circuit breaker behavior?
  - Logging strategy?
  - Recovery mechanism?

---

## 🧠 Architectural Decisions

### Past Decisions (from existing code)

1. **Why PostgreSQL + pgvector instead of dedicated vector DB?**
   - Simpler deployment (one database)
   - ACID guarantees for task state
   - pgvector is sufficient for <100k embeddings

2. **Why max 15 iterations?**
   - Balance between autonomy and cost
   - Prevents infinite loops
   - User can restart with more context if needed

3. **Why Docker for sandboxing instead of subprocess?**
   - Stronger isolation (filesystem, network, process)
   - Resource limits (CPU, RAM)
   - Cross-platform consistency

4. **Why function calling instead of prompt engineering?**
   - Structured output (JSON)
   - Better error handling
   - Easier to extend with new tools

5. **Why separate agents instead of one LLM call?**
   - Separation of concerns
   - Different prompts for different tasks
   - Easier to test and debug

### Questions for Future Decisions

- **Should we support multi-file refactoring in one iteration?**
  - Pros: More powerful, fewer iterations
  - Cons: Harder to test, more tokens

- **Should we add a validator agent before testing?**
  - Pros: Catch syntax errors before Docker execution
  - Cons: More iterations, more cost

- **Should we parallelize test execution?**
  - Pros: Faster feedback
  - Cons: More complex orchestration, resource contention

- **Should we support interactive debugging?**
  - Pros: User can guide the agent
  - Cons: Breaks autonomy, complex UI

---

## 📚 Further Reading

- **Main README**: `/home/user/Miracle/autonomous_agent/README.md`
- **Handoff Document**: `/home/user/Miracle/autonomous_coding_agent_handoff.md` (1,516 lines, comprehensive)
- **Database Schema**: `/home/user/Miracle/autonomous_agent/scripts/init_db.sql`
- **Configuration Examples**: All files in `/home/user/Miracle/autonomous_agent/config/`
- **Architecture Diagrams**: See `ARCHITECTURE.md`
- **Functionality Details**: See `FUNCTIONALITY.md`

---

## 🤝 Collaboration with Execution Agents

**Planning agents** focus on:
- High-level architecture
- Feature design
- Database schema
- Configuration structure
- Testing strategy

**Execution agents** focus on:
- Implementing the plan
- Writing code
- Running tests
- Fixing bugs
- Refactoring

**Handoff Protocol**:
1. Planning agent creates detailed implementation plan
2. Planning agent documents key decisions and trade-offs
3. Execution agent implements according to plan
4. Execution agent reports blockers back to planning agent
5. Planning agent adjusts plan if needed

**Document all plans in**: `docs/plans/YYYY-MM-DD-feature-name.md`

---

## ✅ Planning Agent Success Criteria

A planning agent has succeeded when:

1. ✅ Implementation plan is clear and actionable
2. ✅ All architectural decisions are documented with rationale
3. ✅ Database schema changes include migration scripts
4. ✅ Configuration changes are backward compatible
5. ✅ Testing strategy is defined (unit, integration, e2e)
6. ✅ Safety implications are analyzed
7. ✅ Extension points are identified
8. ✅ Success metrics are defined
9. ✅ Handoff document for execution agent is complete

---

**Last Updated**: 2026-01-16
**Maintained By**: AI Planning Agents
**Related Documents**: `AGENT-EXECUTION.md`, `ARCHITECTURE.md`, `FUNCTIONALITY.md`, `DEPENDENCIES.md`
