# Component Architecture

> **Purpose**: Detailed architecture of individual system components.

---

## 3.1 Orchestrator (`src/orchestrator.py`)

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
    "language": str,  # e.g., "python", "node", "go", etc.
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

---

## 3.2 Agent Layer

### PlannerAgent

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

### CoderAgent

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

The system is language-agnostic and can support any language by providing the appropriate scaffolding and test runners. Examples:

| Language | Scaffolding | Test Framework | Dependency Manager |
|----------|-------------|----------------|-------------------|
| Python | `__init__.py`, `main.py`, `tests/` | pytest + hypothesis | pip + requirements.txt |
| Node.js | `package.json`, `index.js`, `test/` | jest | npm |
| Go | `go.mod`, `main.go`, `*_test.go` | go test | go mod |
| ... | Custom scaffolding | Any framework | Any manager |

### TesterAgent

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

### ReflectorAgent

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

---

## 3.3 LLM Interface Layer

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

---

## 3.4 Memory System

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

---

## 3.5 Sandbox System

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
│                Layer 4: Docker Sandbox (Optional)            │
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