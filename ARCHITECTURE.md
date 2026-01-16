# ARCHITECTURE.md

> **Purpose**: Comprehensive technical architecture documentation for the Autonomous Coding Agent system.

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Patterns](#architectural-patterns)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Database Architecture](#database-architecture)
6. [LLM Integration Architecture](#llm-integration-architecture)
7. [Security Architecture](#security-architecture)
8. [Scalability & Performance](#scalability--performance)
9. [Deployment Architecture](#deployment-architecture)
10. [Technical Decisions](#technical-decisions)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                            │
│                    (CLI - Click + Rich)                          │
│   Commands: run, history, resume, cancel                         │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR LAYER                           │
│                   (State Machine Controller)                      │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │   INIT     │→ │  PLANNING  │→ │   CODING   │→ │ VALIDATING│  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
│                                         │              │          │
│                                         ▼              ▼          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  SUCCESS   │← │  TESTING   │← │  CODING    │← │REFLECTING│  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
│                                         ▲              │          │
│                                         └──────────────┘          │
│                                         (Iteration Loop)          │
└────────┬──────────────┬──────────────┬──────────────┬────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────┐ │
│  │   Planner   │  │    Coder    │  │   Tester    │  │Reflec│ │
│  │    Agent    │  │    Agent    │  │    Agent    │  │ tor  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬──┘ │
└─────────┼─────────────────┼─────────────────┼─────────────┼────┘
          │                 │                 │             │
          └─────────────────┴─────────────────┴─────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      LLM INTERFACE LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  OpenAI Client (with retry logic + token tracking)      │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Tool Definitions (create_file, read_file, etc.)        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Prompt Templates (system prompts for each agent)       │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬────────────────┐
         │               │               │                │
         ▼               ▼               ▼                ▼
┌───────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐
│  MEMORY       │ │  SANDBOX   │ │  TESTING   │ │   PROJECT    │
│  SYSTEM       │ │  SYSTEM    │ │  SYSTEM    │ │  SCAFFOLDING │
│               │ │            │ │            │ │              │
│ - DB Manager  │ │ - Docker   │ │ - Test Gen │ │ - Python     │
│ - Vector Store│ │ - Safety   │ │ - Test Run │ │ - Node.js    │
│ - Pattern     │ │ - Resource │ │ - Coverage │ │              │
│   Matcher     │ │   Limits   │ │            │ │              │
└───────┬───────┘ └──────┬─────┘ └──────┬─────┘ └──────────────┘
        │                │               │
        ▼                ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DATA & EXECUTION LAYER                        │
│  ┌────────────────────────┐    ┌────────────────────────────┐   │
│  │  PostgreSQL + pgvector │    │  Docker Containers         │   │
│  │  - Tasks               │    │  - Isolated workspaces     │   │
│  │  - Iterations          │    │  - Resource limits         │   │
│  │  - Failures (vectors)  │    │  - Network disabled        │   │
│  │  - Patterns (vectors)  │    │  - Security scanning       │   │
│  │  - Metrics             │    │                            │   │
│  └────────────────────────┘    └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Philosophy

**"The difference between a chatbot and an agent is the loop."**

This system implements autonomous coding through:
1. **Goal-based operation**: Task descriptions, not prompts
2. **Iterative refinement**: Code → Test → Reflect → Code (loop)
3. **Learning from failure**: Vector similarity search for past solutions
4. **Safety-first execution**: Multi-layer sandboxing and validation
5. **Bounded autonomy**: 15-iteration circuit breaker

---

## 2. Architectural Patterns

### 2.1 State Machine Pattern

**Implementation**: Finite State Machine (FSM)

```python
class OrchestrationState(Enum):
    INIT = "init"           # Initialize workspace, load config
    PLANNING = "planning"    # Decompose task, query memory
    CODING = "coding"        # Generate code via LLM + tools
    TESTING = "testing"      # Run tests in sandbox
    REFLECTING = "reflecting" # Analyze failures, plan fixes
    SUCCESS = "success"      # All tests passed
    FAILED = "failed"        # Max iterations reached
    PAUSED = "paused"        # User interrupted
```

**State Transition Rules**:

| Current State | Event | Next State | Condition |
|---------------|-------|------------|-----------|
| INIT | Workspace ready | PLANNING | Always |
| PLANNING | Plan created | CODING | Always |
| CODING | Code generated | TESTING | Always |
| TESTING | Tests passed | SUCCESS | pass_rate == 100% |
| TESTING | Tests failed | REFLECTING | pass_rate < 100% |
| REFLECTING | Analysis done | CODING | iteration < max_iterations |
| REFLECTING | Max iterations | FAILED | iteration >= max_iterations |
| * | User interrupt | PAUSED | Any time |

**Benefits**:
- **Predictable behavior**: State transitions are explicit
- **Debuggability**: Can inspect current state at any time
- **Resumability**: Can checkpoint and resume from any state
- **Testability**: Can test each state handler in isolation

### 2.2 Agent Pattern

**Implementation**: Specialized AI agents with single responsibilities

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, llm_client: LLMClient, config: Config):
        self.llm_client = llm_client
        self.config = config
        self.logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """
        Execute agent-specific logic.

        Args:
            context: Shared context from orchestrator

        Returns:
            Results to merge back into context
        """
        pass
```

**Agent Responsibilities**:

| Agent | Single Responsibility | Input | Output |
|-------|----------------------|-------|--------|
| **PlannerAgent** | Task decomposition | Task description | Implementation plan, subtasks |
| **CoderAgent** | Code generation | Plan + feedback | Code files |
| **TesterAgent** | Test generation + execution | Code files | Test results |
| **ReflectorAgent** | Failure analysis | Test failures | Error analysis + fix hypothesis |

**Communication**: Agents communicate via **shared context dictionary** managed by orchestrator (not direct agent-to-agent calls).

**Benefits**:
- **Separation of concerns**: Each agent does one thing well
- **Independent testing**: Mock the LLM, test agent logic
- **Extensibility**: Add new agents without modifying existing ones
- **Composability**: Orchestrator can reorder or skip agents

### 2.3 Tool Use Pattern

**Implementation**: LLM function calling (OpenAI API)

```python
# Tool definition (declarative)
CREATE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "create_file",
        "description": "Create a new file with content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    }
}

# Tool handler (imperative)
class CoderAgent:
    def _handle_tool_call(self, tool_call, workspace: Path) -> dict:
        if tool_call.function.name == "create_file":
            args = json.loads(tool_call.function.arguments)
            return self._create_file(args["path"], args["content"], workspace)
```

**Available Tools**:
- `create_file(path, content)` - Write a new file
- `read_file(path)` - Read existing file
- `list_files()` - List workspace contents
- `delete_file(path)` - Remove a file (if implemented)

**Benefits**:
- **Structured output**: LLM generates valid JSON (not free text)
- **Type safety**: Parameters are validated before execution
- **Discoverability**: LLM sees tool descriptions and decides when to use
- **Extensibility**: Add new tools without changing prompts

### 2.4 Repository Pattern

**Implementation**: Abstraction layer over database operations

```python
class DatabaseManager:
    """Centralized database operations"""

    async def create_task(self, description: str, language: str) -> UUID:
        """Create a new task record"""

    async def update_task_status(self, task_id: UUID, status: str):
        """Update task status"""

    async def log_iteration(self, task_id: UUID, iteration_data: dict):
        """Log an iteration"""

    async def store_failure(self, task_id: UUID, error: dict):
        """Store a failure for learning"""
```

**Benefits**:
- **Testability**: Mock database without PostgreSQL
- **Flexibility**: Can swap database implementations
- **Query optimization**: Centralized place for query tuning
- **Transaction management**: Handle ACID properties consistently

### 2.5 Circuit Breaker Pattern

**Implementation**: Prevent infinite loops

```python
class Orchestrator:
    MAX_ITERATIONS = 15
    WARNING_THRESHOLD = 12

    async def run(self):
        while self.current_iteration < self.MAX_ITERATIONS:
            if self.current_iteration == self.WARNING_THRESHOLD:
                self.logger.warning(
                    "Approaching max iterations",
                    current=self.current_iteration,
                    max=self.MAX_ITERATIONS
                )

            next_state = await self._execute_current_state()

            if next_state in (OrchestrationState.SUCCESS, OrchestrationState.FAILED):
                break

            self.current_iteration += 1

        if self.current_iteration >= self.MAX_ITERATIONS:
            self.logger.error("Max iterations reached, task failed")
            return {"status": "failed", "reason": "max_iterations"}
```

**Benefits**:
- **Cost control**: Prevents runaway LLM API costs
- **Time bounds**: User knows task won't run forever
- **Graceful degradation**: Warning before hard stop

---

## 3. Component Architecture

### 3.1 Orchestrator (`src/orchestrator.py`)

**Responsibilities**:
1. State machine management
2. Iteration counting and circuit breaking
3. Context management (shared state across agents)
4. Checkpointing (every 5 iterations)
5. Logging and metrics collection

**Key Methods**:

```python
class Orchestrator:
    async def run(self) -> dict:
        """Main orchestration loop"""

    async def _run_init_state(self) -> OrchestrationState:
        """Initialize workspace, load config"""

    async def _run_planning_state(self) -> OrchestrationState:
        """Invoke PlannerAgent, store plan"""

    async def _run_coding_state(self) -> OrchestrationState:
        """Invoke CoderAgent, generate code"""

    async def _run_testing_state(self) -> OrchestrationState:
        """Invoke TesterAgent, execute tests"""

    async def _run_reflecting_state(self) -> OrchestrationState:
        """Invoke ReflectorAgent, analyze failures"""

    async def _checkpoint(self):
        """Save state to database for resume"""

    async def _transition_to(self, next_state: OrchestrationState):
        """Transition to next state with logging"""
```

**Context Dictionary Structure**:

```python
context = {
    "task_id": UUID,
    "task_description": str,
    "language": str,  # "python" or "node"
    "workspace": Path,
    "current_iteration": int,
    "max_iterations": int,

    # From PlannerAgent
    "plan": {
        "subtasks": List[str],
        "expected_challenges": List[str],
        "similar_patterns": List[dict]
    },

    # From CoderAgent
    "code_files": List[Path],
    "code_content": Dict[str, str],  # path -> content

    # From TesterAgent
    "test_files": List[Path],
    "test_results": {
        "passed": int,
        "failed": int,
        "errors": List[dict],
        "coverage": float
    },

    # From ReflectorAgent
    "analysis": {
        "root_cause": str,
        "similar_failures": List[dict],
        "fix_hypothesis": str
    }
}
```

### 3.2 Agent Layer

#### PlannerAgent

**Responsibilities**:
- Decompose high-level task into subtasks
- Query memory for similar successful patterns
- Identify potential challenges
- Create implementation plan

**LLM Prompt Structure**:

```python
system_prompt = """
You are an expert software architect. Given a task description, create a detailed
implementation plan. Consider:
1. Subtasks and their dependencies
2. Expected challenges and edge cases
3. Testing strategy

Break complex tasks into manageable steps.
"""

user_prompt = f"""
Task: {task_description}
Language: {language}

Similar successful patterns from past:
{similar_patterns}

Create an implementation plan.
"""
```

**Memory Integration**:
- Embeds task description
- Searches vector DB for similar past tasks (similarity > 0.7)
- Includes top 3 similar patterns in prompt context

#### CoderAgent

**Responsibilities**:
- Generate code based on plan and feedback
- Use function calling to create files
- Scaffold project structure (if needed)
- Follow language-specific conventions

**Tool Usage Flow**:

```
1. LLM receives task + plan
2. LLM decides to call create_file(path="main.py", content="...")
3. Agent validates path (must be in workspace)
4. Agent writes file to disk
5. Agent returns tool result to LLM
6. LLM continues or finishes
7. Agent returns list of created files
```

**Language Support**:

| Language | Scaffolding | Test Framework | Dependency Manager |
|----------|-------------|----------------|-------------------|
| Python | `__init__.py`, `main.py`, `tests/` | pytest + hypothesis | pip + requirements.txt |
| Node.js | `package.json`, `index.js`, `test/` | jest | npm |

#### TesterAgent

**Responsibilities**:
- Generate comprehensive tests (unit + edge cases)
- Use property-based testing (hypothesis for Python)
- Execute tests in Docker sandbox
- Parse test output and extract failures
- Calculate coverage

**Test Generation Strategy**:

```python
# Generated test structure
def test_{function_name}_happy_path():
    """Test normal operation"""

def test_{function_name}_edge_cases():
    """Test boundary conditions"""

def test_{function_name}_error_handling():
    """Test error conditions"""

@given(st.integers(), st.integers())  # hypothesis property test
def test_{function_name}_properties(a, b):
    """Test mathematical properties"""
```

**Test Execution**:
1. Generate tests (LLM)
2. Write test files to workspace
3. Spin up Docker container
4. Install dependencies (if approved)
5. Run pytest
6. Capture output (stdout, stderr, exit code)
7. Parse pytest output (JSON format)
8. Extract failures and stack traces

#### ReflectorAgent

**Responsibilities**:
- Analyze test failures (not just symptoms, root causes)
- Query memory for similar past failures
- Generate fix hypothesis
- Store failure patterns in vector DB

**Analysis Process**:

```python
1. Parse test failure message
   - Extract error type (e.g., "KeyError")
   - Extract stack trace
   - Identify failing line

2. Embed error context
   - Error message + stack trace + failing code

3. Search vector DB for similar failures
   - Find failures with similarity > 0.6
   - Retrieve solutions that worked

4. Generate fix hypothesis
   - "The issue is likely X because Y"
   - "Similar failure was fixed by Z"
   - "Suggested fix: Do A and B"

5. Store this failure for future reference
   - Embed failure context
   - Insert into failures table
```

### 3.3 LLM Interface Layer

**Responsibilities**:
- Abstract OpenAI API calls
- Handle retries with exponential backoff
- Track token usage
- Support model fallback sequence
- Manage prompt templates

**Retry Strategy** (using `tenacity`):

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(OpenAIError),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def chat_completion(self, messages, model, tools=None):
    try:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response
    except RateLimitError as e:
        # Will retry with exponential backoff
        raise
    except OpenAIError as e:
        # Try fallback model
        if self.config.fallback_models:
            model = self.config.fallback_models.pop(0)
            raise  # Retry with fallback model
        else:
            # No more fallbacks
            raise CodeGenerationError(f"All models failed: {e}")
```

**Token Tracking**:

```python
class TokenCounter:
    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def track_usage(self, response):
        usage = response.usage
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens

        # Log to database
        self.db_manager.record_token_usage(
            task_id=self.task_id,
            iteration=self.iteration,
            tokens=usage.total_tokens
        )
```

### 3.4 Memory System

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory System                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  VectorStore     │         │  DatabaseManager │         │
│  │                  │         │                  │         │
│  │ - embed()        │────────▶│ - execute_query()│         │
│  │ - search()       │         │ - transactions   │         │
│  └────────┬─────────┘         └──────────────────┘         │
│           │                                                  │
│           │ uses                                             │
│           │                                                  │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────────┐      │
│  │   OpenAI Embeddings API                          │      │
│  │   Model: text-embedding-3-large                  │      │
│  │   Dimensions: 1536                               │      │
│  └──────────────────────────────────────────────────┘      │
│           │                                                  │
│           │ stores in                                        │
│           ▼                                                  │
│  ┌──────────────────────────────────────────────────┐      │
│  │   PostgreSQL + pgvector                          │      │
│  │   - failures table (error + embedding)           │      │
│  │   - patterns table (solution + embedding)        │      │
│  │   - Indexed with IVFFlat (cosine similarity)     │      │
│  └──────────────────────────────────────────────────┘      │
│           │                                                  │
│           │ retrieved by                                     │
│           ▼                                                  │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ PatternMatcher   │         │ FailureAnalyzer  │         │
│  │                  │         │                  │         │
│  │ - find_similar_  │         │ - find_similar_  │         │
│  │   solutions()    │         │   failures()     │         │
│  └──────────────────┘         └──────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Vector Similarity Search**:

```sql
-- Find similar failures (cosine similarity)
SELECT
    id,
    task_id,
    error_message,
    solution,
    1 - (embedding <=> %s::vector) AS similarity
FROM failures
WHERE 1 - (embedding <=> %s::vector) > 0.6  -- Threshold
ORDER BY similarity DESC
LIMIT 5;

-- Create IVFFlat index for fast approximate search
CREATE INDEX ON failures
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Embedding Generation**:

```python
async def _generate_embedding(self, text: str) -> List[float]:
    """Generate embedding for text using OpenAI API"""
    response = await self.openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding  # 1536-dimensional vector
```

**When Memory is Queried**:

| Agent | Query Type | Purpose |
|-------|-----------|---------|
| Planner | Find similar successful tasks | Retrieve implementation patterns |
| Reflector | Find similar past failures | Learn from past mistakes |

### 3.5 Sandbox System

**Multi-Layer Security**:

```
┌─────────────────────────────────────────────────────────────┐
│                     Layer 1: AST Scanning                    │
│  Blocks: eval(), exec(), __import__(), compile()            │
│  Before code ever runs                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ ✅ Pass
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Layer 2: Bandit SAST                     │
│  Security scanning: SQL injection, hardcoded secrets, etc.  │
│  Static analysis                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ ✅ Pass
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Layer 3: User Approval                   │
│  Prompt for: network access, subprocess calls               │
│  User can deny dangerous operations                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ ✅ Approved
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     Layer 4: Docker Sandbox                  │
│  - Non-root user (sandbox_user)                             │
│  - Resource limits: 1 CPU, 1GB RAM, 5min timeout            │
│  - Network disabled by default                               │
│  - Filesystem: /workspace only (bind mount)                  │
│  - No access to host system                                  │
└─────────────────────────────────────────────────────────────┘
```

**Docker Container Specification**:

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 sandbox_user

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox_user

# Container runs with these limits (set via Docker API):
# --cpus=1
# --memory=1g
# --network=none
# --read-only (except /workspace)
# --pids-limit=100
```

**Resource Limits** (via Docker API):

```python
container = docker_client.containers.run(
    image="sandbox:python3.11",
    command=["python", "-m", "pytest", "tests/"],
    detach=True,
    remove=True,
    network_mode="none",  # Disable network
    mem_limit="1g",  # 1GB RAM
    cpu_quota=100000,  # 1 CPU core
    pids_limit=100,  # Max 100 processes
    volumes={
        str(workspace): {"bind": "/workspace", "mode": "rw"}
    },
    working_dir="/workspace",
    user="sandbox_user"
)

# Wait for completion with timeout
try:
    result = container.wait(timeout=300)  # 5 minutes
except requests.exceptions.Timeout:
    container.kill()
    raise ExecutionTimeoutError("Code execution exceeded 5 minutes")
```

---

## 4. Data Flow

### 4.1 Complete Task Execution Flow

```
[USER]
  │
  ├─> "Write a REST API for managing todos"
  │
  ▼
[CLI - main.py]
  │
  ├─> Parse command
  ├─> Validate input
  └─> Create task record in DB
  │
  ▼
[ORCHESTRATOR - State: INIT]
  │
  ├─> Create workspace directory
  ├─> Load configuration
  └─> Initialize context
  │
  ▼
[ORCHESTRATOR - State: PLANNING]
  │
  ├─> Call PlannerAgent.execute()
  │    │
  │    ├─> Embed task description
  │    ├─> Query vector DB for similar patterns
  │    ├─> Build LLM prompt with context
  │    ├─> Call OpenAI API
  │    └─> Parse response (plan with subtasks)
  │
  ├─> Store plan in context
  └─> Transition to CODING
  │
  ▼
[ORCHESTRATOR - State: CODING]  ◄──────────────┐
  │                                             │
  ├─> Call CoderAgent.execute()                │
  │    │                                        │
  │    ├─> Build prompt (plan + past feedback) │
  │    ├─> Call OpenAI with tools             │
  │    ├─> LLM calls create_file()            │
  │    ├─> Agent writes files to workspace     │
  │    └─> Return list of files created        │
  │                                             │
  ├─> Store code files in context             │
  └─> Transition to TESTING                    │
  │                                             │
  ▼                                             │
[ORCHESTRATOR - State: TESTING]                │
  │                                             │
  ├─> Call TesterAgent.execute()               │
  │    │                                        │
  │    ├─> Generate tests (LLM)                │
  │    ├─> Write test files                    │
  │    ├─> Create Docker container             │
  │    ├─> Run pytest in container             │
  │    ├─> Capture output                      │
  │    └─> Parse results                       │
  │                                             │
  ├─> Store test results in context            │
  │                                             │
  ├─> Check pass rate                          │
  │    │                                        │
  │    ├─> 100% passed? ─YES──> [SUCCESS] ✅   │
  │    │                                        │
  │    └─> Failed? ─NO──> Transition to REFLECTING
  │                                             │
  ▼                                             │
[ORCHESTRATOR - State: REFLECTING]             │
  │                                             │
  ├─> Call ReflectorAgent.execute()            │
  │    │                                        │
  │    ├─> Analyze test failures               │
  │    ├─> Embed error context                 │
  │    ├─> Query vector DB for similar failures│
  │    ├─> Build prompt with similar solutions │
  │    ├─> Call OpenAI API                     │
  │    └─> Generate fix hypothesis             │
  │                                             │
  ├─> Store failure in DB (with embedding)     │
  ├─> Store analysis in context                │
  ├─> Increment iteration counter              │
  │                                             │
  ├─> Check iteration count                    │
  │    │                                        │
  │    ├─> < 15? ─YES──> Transition to CODING ─┘
  │    │
  │    └─> >= 15? ─NO──> [FAILED] ❌
  │
  ▼
[DATABASE]
  │
  ├─> Update task status (success/failed)
  ├─> Log final metrics
  └─> Store completion timestamp
  │
  ▼
[USER]
  │
  └─> View results in terminal (Rich UI)
```

### 4.2 Memory Retrieval Flow

```
[Agent needs similar patterns]
  │
  ▼
[Generate embedding for query]
  │
  ├─> Query: "REST API with authentication"
  ├─> Call OpenAI Embeddings API
  └─> Receive 1536-dim vector
  │
  ▼
[Search vector database]
  │
  ├─> SQL: SELECT ... WHERE similarity > 0.7
  ├─> pgvector performs cosine similarity
  └─> Returns top 5 matches
  │
  ▼
[Filter and rank results]
  │
  ├─> Filter by similarity threshold (0.7)
  ├─> Rank by recency (newer = better)
  └─> Return to agent
  │
  ▼
[Agent uses context]
  │
  ├─> Include in LLM prompt
  ├─> "Similar past solution: ..."
  └─> LLM generates better code
```

### 4.3 Checkpoint and Resume Flow

```
[Checkpoint Trigger]
  │
  ├─> Every 5 iterations
  ├─> Before user interrupt (Ctrl+C)
  └─> On critical errors
  │
  ▼
[Serialize State]
  │
  ├─> Current state (CODING, TESTING, etc.)
  ├─> Iteration number
  ├─> Context dictionary (JSON)
  └─> Workspace path
  │
  ▼
[Store in Database]
  │
  ├─> UPDATE tasks SET checkpoint_state = ...
  └─> Commit transaction
  │
  ▼
[User resumes later]
  │
  ├─> Command: python -m src.main resume <task_id>
  │
  ▼
[Load Checkpoint]
  │
  ├─> Query: SELECT checkpoint_state FROM tasks WHERE id = ...
  ├─> Deserialize context
  └─> Restore orchestrator state
  │
  ▼
[Continue Execution]
  │
  └─> Resume from saved state
```

---

## 5. Database Architecture

### 5.1 Schema Design

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

### 5.2 Query Patterns

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

### 5.3 Data Lifecycle

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

---

## 6. LLM Integration Architecture

### 6.1 Model Selection Strategy

```yaml
# config/openai.yaml
provider: "openai"

models:
  planner: "gpt-4-turbo-preview"     # Reasoning-heavy, needs GPT-4
  coder: "gpt-4-turbo-preview"       # Code generation, needs GPT-4
  tester: "gpt-4-turbo-preview"      # Test generation, can use GPT-4
  reflector: "gpt-4-turbo-preview"   # Error analysis, needs GPT-4
  embedding: "text-embedding-3-large" # 1536-dim embeddings

fallback_sequence:
  - "gpt-4-turbo-preview"
  - "gpt-4"
  - "gpt-3.5-turbo-16k"  # Last resort (cheaper but less capable)

parameters:
  temperature: 0.2      # Low for deterministic code
  top_p: 1.0
  max_tokens: 4096
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

**Why These Models?**

| Agent | Model Choice | Rationale |
|-------|-------------|-----------|
| Planner | GPT-4 Turbo | Needs strong reasoning for task decomposition |
| Coder | GPT-4 Turbo | Best code generation quality, fewer syntax errors |
| Tester | GPT-4 Turbo | Generates comprehensive tests, edge cases |
| Reflector | GPT-4 Turbo | Deep error analysis, root cause identification |
| Embedding | text-embedding-3-large | High-dimensional embeddings (1536D) for better similarity |

### 6.2 Cost Optimization

**Strategies**:

1. **Cache similar queries**: Don't re-embed identical error messages
2. **Lazy retrieval**: Only query vector DB when needed
3. **Prompt compression**: Remove unnecessary context
4. **Model fallback**: Use GPT-3.5 for simple tasks (if configured)
5. **Token counting**: Warn when approaching budget limits

```python
class CostTracker:
    GPT4_TURBO_INPUT_COST = 0.01 / 1000   # $0.01 per 1K tokens
    GPT4_TURBO_OUTPUT_COST = 0.03 / 1000  # $0.03 per 1K tokens
    EMBEDDING_COST = 0.00013 / 1000       # $0.00013 per 1K tokens

    def calculate_cost(self, prompt_tokens, completion_tokens, embedding_tokens):
        cost = (
            prompt_tokens * self.GPT4_TURBO_INPUT_COST +
            completion_tokens * self.GPT4_TURBO_OUTPUT_COST +
            embedding_tokens * self.EMBEDDING_COST
        )
        return cost

    def check_budget(self, task_id):
        total_cost = self.get_total_cost(task_id)
        if total_cost > self.config.max_budget_per_task:
            raise BudgetExceededError(
                f"Task {task_id} exceeded budget: ${total_cost:.2f}"
            )
```

### 6.3 Prompt Engineering

**System Prompts** (loaded from `config/system_prompts.yaml`):

```yaml
coder: |
  You are an expert software engineer. Generate clean, well-documented code.

  Guidelines:
  - Follow language best practices (PEP 8 for Python, ESLint for Node.js)
  - Include type hints (Python) or JSDoc (Node.js)
  - Handle errors gracefully
  - Write self-documenting code with clear variable names
  - Add comments only where logic is non-obvious

  Use the provided tools to create files:
  - create_file(path, content): Create a new file
  - read_file(path): Read existing file
  - list_files(): List workspace contents

  Generate code iteratively. If tests fail, learn from the feedback.

reflector: |
  You are an expert debugger. Analyze test failures and identify root causes.

  Process:
  1. Parse the error message and stack trace
  2. Identify the root cause (not just the symptom)
  3. Consider similar past failures and their solutions
  4. Generate a specific fix hypothesis

  Be precise. Avoid vague suggestions like "check your code" or "add error handling".
  Provide actionable fixes: "Change line X to Y because Z".
```

---

## 7. Security Architecture

### 7.1 Threat Model

**Threats**:
1. **Arbitrary code execution**: Malicious code accessing host system
2. **Data exfiltration**: Code reading secrets or sensitive files
3. **Resource exhaustion**: Infinite loops consuming CPU/RAM
4. **Network abuse**: Making unauthorized external requests
5. **Dependency confusion**: Installing malicious packages

**Mitigations**:

| Threat | Mitigation | Layer |
|--------|-----------|-------|
| Arbitrary code execution | AST scanning + Docker isolation | 1 + 4 |
| Data exfiltration | Path validation + network disabled | 3 + 4 |
| Resource exhaustion | CPU/RAM/time limits in Docker | 4 |
| Network abuse | User approval + network disabled | 3 + 4 |
| Dependency confusion | Allowlist + manual approval | 3 |

### 7.2 AST Scanning Rules

```python
class SafetyChecker:
    # Blocked imports (never allowed)
    DANGEROUS_IMPORTS = [
        "os",           # File system access
        "subprocess",   # Execute shell commands
        "pty",          # Pseudo-terminal (shell escape)
        "socket",       # Network sockets
        "__builtin__",  # Python internals
        "__import__",   # Dynamic imports
        "ctypes",       # C bindings
        "pickle",       # Arbitrary code execution
    ]

    # Blocked function calls
    DANGEROUS_CALLS = [
        "eval",
        "exec",
        "compile",
        "open",  # Unless path is within workspace
    ]

    def check_code(self, code: str, workspace: Path) -> List[str]:
        """
        Scan code for dangerous operations.

        Returns:
            List of violation messages (empty if safe)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]

        violations = []
        violations.extend(self._check_imports(tree))
        violations.extend(self._check_function_calls(tree))
        violations.extend(self._check_file_operations(tree, workspace))

        return violations
```

### 7.3 Approval Workflow

```python
class ApprovalManager:
    def requires_approval(self, operation: str, details: dict) -> bool:
        """Check if operation requires user approval"""
        approval_rules = self.config.safety_rules.approval_required

        # Network operations always require approval
        if operation in ["network_request", "socket_connection"]:
            return True

        # Subprocess calls require approval
        if operation == "subprocess_call":
            # Unless it's a safe command (e.g., pytest)
            command = details.get("command", "")
            if command.startswith(("pytest", "python -m pytest")):
                return False
            return True

        # Installing dependencies requires approval
        if operation == "install_dependency":
            package = details.get("package", "")
            if package in self.config.allowed_dependencies:
                return True  # Still prompt, but mark as "recommended"
            return True

        return operation in approval_rules

    async def prompt_user(self, operation: str, details: dict) -> bool:
        """Prompt user for approval (blocking)"""
        from src.ui.approval_prompt import ApprovalPrompt

        prompt = ApprovalPrompt()
        approved = prompt.ask(
            operation=operation,
            details=details,
            safety_level="medium"  # or "high", "critical"
        )

        # Log decision
        await self.db_manager.log_approval(
            task_id=self.task_id,
            operation=operation,
            approved=approved,
            details=details
        )

        return approved
```

---

## 8. Scalability & Performance

### 8.1 Current Limitations

| Resource | Current Limit | Bottleneck |
|----------|--------------|------------|
| Concurrent tasks | 1 | Single-threaded orchestrator |
| Max iterations | 15 | Cost control |
| LLM API rate | 10K RPM (depends on tier) | OpenAI rate limits |
| Vector search | <100K embeddings | pgvector index size |
| Docker containers | Unlimited | System resources |

### 8.2 Scaling Strategies

**Horizontal Scaling** (future enhancement):

```
┌─────────────────────────────────────────────────────────┐
│                   Load Balancer / Queue                  │
│                    (Celery + Redis)                      │
└────────┬────────────────┬───────────────┬───────────────┘
         │                │               │
         ▼                ▼               ▼
    ┌─────────┐      ┌─────────┐    ┌─────────┐
    │ Worker 1│      │ Worker 2│    │ Worker N│
    │ Orchestr│      │ Orchestr│    │ Orchestr│
    └────┬────┘      └────┬────┘    └────┬────┘
         │                │               │
         └────────────────┴───────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │ Shared PostgreSQL      │
              │ (task queue + results) │
              └────────────────────────┘
```

**Vertical Scaling** (current):
- Increase Docker container limits (CPU, RAM)
- Use faster GPU-based embedding generation
- Cache frequently-retrieved patterns in Redis

### 8.3 Performance Optimizations

**Database**:
```sql
-- Use prepared statements (avoid SQL injection + faster)
PREPARE get_similar_failures AS
SELECT id, error_message, solution, similarity
FROM (
    SELECT id, error_message, solution,
           1 - (embedding <=> $1::vector) AS similarity
    FROM failures
) subquery
WHERE similarity > $2
ORDER BY similarity DESC
LIMIT $3;

-- Execute with parameters
EXECUTE get_similar_failures('[...]'::vector, 0.6, 5);

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW task_success_rates AS
SELECT
    language,
    task_type,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful,
    AVG(current_iteration) AS avg_iterations
FROM tasks
GROUP BY language, task_type;

-- Refresh periodically
REFRESH MATERIALIZED VIEW task_success_rates;
```

**Caching**:
```python
from functools import lru_cache
import hashlib

class VectorStore:
    @lru_cache(maxsize=1000)
    def _generate_embedding_cached(self, text: str) -> tuple:
        """Cache embeddings for identical text (returns tuple for hashability)"""
        embedding = self._generate_embedding(text)  # Calls OpenAI API
        return tuple(embedding)  # Convert list to tuple for caching

    def embed(self, text: str) -> List[float]:
        """Public method with caching"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cached_key = f"embedding:{text_hash}"

        # Check Redis cache first
        cached = self.redis_client.get(cached_key)
        if cached:
            return json.loads(cached)

        # Generate and cache
        embedding = list(self._generate_embedding_cached(text))
        self.redis_client.setex(cached_key, 86400, json.dumps(embedding))  # 24h TTL
        return embedding
```

---

## 9. Deployment Architecture

### 9.1 Local Development

```
┌──────────────────────────────────────────┐
│           Developer Laptop                │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Python 3.11 Virtual Environment   │  │
│  │  - src/ (autonomous agent code)    │  │
│  │  - pytest (running tests)          │  │
│  └────────────────────────────────────┘  │
│                  │                        │
│                  ▼                        │
│  ┌────────────────────────────────────┐  │
│  │  Docker Compose                    │  │
│  │  ┌──────────────┐  ┌────────────┐ │  │
│  │  │ PostgreSQL   │  │  Sandbox   │ │  │
│  │  │ + pgvector   │  │ Container  │ │  │
│  │  └──────────────┘  └────────────┘ │  │
│  └────────────────────────────────────┘  │
│                                           │
└──────────────────────────────────────────┘
```

**Setup**:
```bash
# Install dependencies
pip install -r requirements.txt

# Start services
docker-compose up -d

# Initialize database
python scripts/setup_db.py

# Run agent
python -m src.main run --task "Your task here"
```

### 9.2 Production Deployment (Future)

```
┌─────────────────────────────────────────────────────────┐
│                      Cloud Provider                      │
│                   (AWS / GCP / Azure)                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Load Balancer / API Gateway            │ │
│  └────────┬───────────────────────┬───────────────────┘ │
│           │                       │                      │
│           ▼                       ▼                      │
│  ┌─────────────────┐     ┌─────────────────┐           │
│  │  ECS/K8s Pod 1  │     │  ECS/K8s Pod N  │           │
│  │  - Orchestrator │     │  - Orchestrator │           │
│  │  - Agents       │     │  - Agents       │           │
│  └────────┬────────┘     └────────┬────────┘           │
│           │                       │                      │
│           └───────────┬───────────┘                      │
│                       │                                  │
│           ┌───────────┴──────────────┐                  │
│           │                          │                  │
│           ▼                          ▼                  │
│  ┌──────────────────┐       ┌──────────────────┐      │
│  │  RDS PostgreSQL  │       │  Docker Runtime  │      │
│  │  + pgvector      │       │  (for sandboxes) │      │
│  └──────────────────┘       └──────────────────┘      │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────┐                                  │
│  │  S3 / Cloud      │                                  │
│  │  Storage (logs)  │                                  │
│  └──────────────────┘                                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Considerations**:
- **Database**: Managed PostgreSQL (RDS, Cloud SQL) with pgvector extension
- **Container orchestration**: Kubernetes or ECS for auto-scaling
- **Secrets management**: AWS Secrets Manager, GCP Secret Manager
- **Logging**: CloudWatch, Stackdriver, or ELK stack
- **Monitoring**: Prometheus + Grafana for metrics
- **Cost tracking**: Tag resources by task_id for cost attribution

---

## 10. Technical Decisions

### 10.1 Key Architectural Decisions

**Decision 1: PostgreSQL + pgvector instead of dedicated vector DB (Pinecone, Weaviate)**

**Rationale**:
- ✅ **Simplicity**: One database for both relational and vector data
- ✅ **ACID guarantees**: Task state + embeddings in same transaction
- ✅ **Cost**: No additional SaaS fees for vector DB
- ✅ **Scale**: pgvector handles <100K embeddings well (sufficient for MVP)
- ❌ **Scale limitations**: Dedicated vector DBs are faster at >1M embeddings

**Trade-off**: Accepted. If we reach 100K+ tasks, migrate to Pinecone.

---

**Decision 2: Max 15 iterations (hard limit)**

**Rationale**:
- ✅ **Cost control**: Each iteration costs $0.10-$0.50 in LLM API calls
- ✅ **User experience**: Prevents tasks running indefinitely
- ✅ **Forcing function**: Encourages better task decomposition
- ❌ **Capability limit**: Some complex tasks might need >15 iterations

**Trade-off**: Accepted. Users can resume with more context if needed.

---

**Decision 3: Synchronous orchestration (not async agents)**

**Rationale**:
- ✅ **Simplicity**: State transitions are deterministic and debuggable
- ✅ **Cost**: Don't pay for multiple parallel LLM calls
- ✅ **Correctness**: Each iteration learns from the previous
- ❌ **Speed**: Could parallelize some operations (e.g., test generation + pattern retrieval)

**Trade-off**: Accepted for MVP. Future: Parallelize where safe (no dependencies).

---

**Decision 4: Docker sandboxing (not VMs or cloud functions)**

**Rationale**:
- ✅ **Speed**: Containers start in <1 second (VMs take minutes)
- ✅ **Cost**: No per-invocation costs (unlike Lambda)
- ✅ **Portability**: Works on any machine with Docker
- ✅ **Isolation**: Good enough for code execution safety
- ❌ **Security**: Not as isolated as VMs (shared kernel)

**Trade-off**: Accepted. For production, consider Firecracker (microVMs) for stronger isolation.

---

**Decision 5: OpenAI API (not self-hosted LLMs)**

**Rationale**:
- ✅ **Quality**: GPT-4 is state-of-the-art for code generation
- ✅ **Simplicity**: No model training or GPU infrastructure
- ✅ **Reliability**: 99.9% uptime SLA
- ❌ **Cost**: $0.01-$0.03 per 1K tokens (adds up)
- ❌ **Latency**: Network calls add ~1-2 seconds per request
- ❌ **Privacy**: Code is sent to OpenAI (not suitable for proprietary code)

**Trade-off**: Accepted for MVP. Future: Support self-hosted LLMs (Ollama, vLLM) for privacy-sensitive use cases.

---

### 10.2 Open Questions

1. **Should we support multi-file refactoring in one iteration?**
   - Pros: More powerful, fewer iterations
   - Cons: Harder to test, more tokens used, higher risk of breaking changes

2. **Should we add a "validator" state before testing?**
   - Pros: Catch syntax errors before expensive Docker execution
   - Cons: More states, slower iteration loop

3. **Should we auto-approve safe operations (e.g., installing `pytest`)?**
   - Pros: Better UX, fewer interruptions
   - Cons: Security risk if allowlist is wrong

4. **Should we cache LLM responses for identical inputs?**
   - Pros: Faster, cheaper
   - Cons: Non-determinism if prompts include timestamps or randomness

5. **Should we support custom LLM providers (Anthropic, Cohere)?**
   - Pros: Flexibility, competition
   - Cons: Maintenance burden, different APIs

---

**Last Updated**: 2026-01-16
**Maintained By**: System Architects
**Related Documents**: `AGENT-PLANNING.md`, `AGENT-EXECUTION.md`, `FUNCTIONALITY.md`, `DEPENDENCIES.md`
