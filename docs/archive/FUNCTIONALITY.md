# FUNCTIONALITY.md

> **Purpose**: Documentation of system behaviors, operations, and flows.

---

## Core Functionality

### What System Does
Accepts high-level coding tasks and autonomously generates working code through iterative refinement:

1. **Understands task**: Breaks down requirements into actionable subtasks
2. **Generates code**: Creates files using LLM-powered code generation
3. **Tests itself**: Generates and runs tests to validate correctness
4. **Learns from failures**: Analyzes errors and searches for similar past solutions
5. **Iterates until success**: Continues loop up to 15 times or until tests pass

**Key Differentiator**: Not a code completion tool or chatbot. An autonomous agent that runs in a loop until goal is achieved.

### Input/Output

**Input**:
```bash
python -m src.main run \
    --task "Build a REST API with endpoints for creating and listing todos" \
    --language python
```

**Output** (in workspace):
```
workspace_<task_id>/
├── main.py              # Generated code
├── requirements.txt     # Dependencies
├── tests/
│   └── test_main.py    # Auto-generated tests
└── .success            # Created when tests pass
```

---

## Iteration Loop Behavior

### Loop Structure
```
[PLANNING] → [CODING] → [TESTING] → (if failed) → [REFLECTING] → back to [CODING]
                                            (if passed) → [SUCCESS]
                                            (max_iter) → [FAILED]
```

### Iteration Details

**PLANNING State** (runs once):
- Receives: Task description
- Queries memory for similar past tasks (vector search)
- Decomposes into subtasks
- Returns: Implementation plan with subtasks

**CODING State** (runs each iteration):
- Receives: Plan + reflection from previous iteration
- Generates code using LLM
- Uses tools: `create_file`, `read_file`, `list_files`
- Returns: Created files list

**TESTING State** (runs each iteration):
- Receives: Code files
- Generates pytest + hypothesis tests
- Executes in Docker sandbox
- Returns: Test results (JSON), pass/fail, errors

**REFLECTING State** (runs if tests fail):
- Receives: Test failures
- Analyzes error type and stack trace
- Vector search for similar failures in memory
- Generates fix hypothesis
- Increments iteration counter
- Returns: Hypothesis, similar failures found

### Circuit Breaker
- **Warning at 12 iterations**: Log warning, continue
- **Hard stop at 15 iterations**: Mark task as FAILED, stop

### Checkpointing
Every 5 iterations:
- Persist orchestrator state to database
- Save context (code, tests, reflection)
- Enables resume after interruption

---

## Agent Behaviors

### Planner Agent

**Goal**: Decompose complex tasks into actionable subtasks

**Process**:
1. Vector search for similar task patterns in memory
2. If patterns found, adapt them to current task
3. Decompose into 3-7 subtasks (manageable scope)
4. Identify dependencies (language, frameworks)
5. Return: List of subtasks, implementation approach

**Tools**: `search_success_patterns(problem_type)`

### Coder Agent

**Goal**: Generate clean, testable code

**Process**:
1. Receive plan + feedback from previous iteration
2. Write code files one at a time using `create_file`
3. Read existing files with `read_file` for context
4. Follow code style: PEP 8, type hints, docstrings
5. Create requirements.txt with version-pinned dependencies

**Tools**: `create_file`, `read_file`, `list_files`

### Tester Agent

**Goal**: Generate comprehensive tests and validate code

**Process**:
1. Analyze code files to understand structure
2. Generate pytest tests for each function/class
3. Add hypothesis property-based tests for edge cases
4. Execute tests in Docker sandbox
5. Collect results (passed/failed, errors, coverage)
6. Return: Test results JSON

**Tools**: `create_test_file`, `run_tests`, `get_coverage`

**Test Generation Principles**:
- Happy path testing
- Error handling testing
- Edge cases (empty input, null, boundaries)
- Property-based tests (hypothesis)
- Aim for 80%+ coverage

### Reflector Agent

**Goal**: Analyze failures and generate fix hypotheses

**Process**:
1. Parse error message and stack trace
2. Categorize error type (ImportError, AttributeError, etc.)
3. Vector search for similar failures in memory
4. If similar failures found: extract their solutions
5. Generate hypothesis: specific fix to try
6. Return: Hypothesis, similar failures, reasoning

**Tools**: `search_similar_failures(error_message)`

**Error Analysis**:
- Normalize error signatures (e.g., "ImportError: module 'X'")
- Identify root cause (missing dependency, wrong type, logic error)
- Map to common solutions (import, type conversion, add condition)

---

## Tool Use Mechanics

### Function Calling Pattern

All agents use OpenAI function calling:

```python
response = await llm_client.chat_completion(
    messages=[...],
    tools=[create_file_tool, read_file_tool, ...]
)

# LLM returns tool call
tool_call = response.choices[0].message.tool_calls[0]
args = json.loads(tool_call.function.arguments)
result = handle_tool(tool_call.function.name, args)
```

### Available Tools

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
- `search_similar_failures(error_message)`: Vector search failures table
- `search_success_patterns(problem_type)`: Vector search patterns table

### Tool Safety

Before execution:
- Validate tool arguments (path within workspace, valid types)
- For `create_file`: Run AST + Bandit scan on content
- If safety violation: Block tool call, log warning, ask user approval

---

## Memory and Learning

### Pattern Storage

**When**: After task SUCCESS
**What**: Store successful code + tests as reusable pattern
**Process**:
1. Extract core solution (remove task-specific details)
2. Generate embedding via OpenAI API
3. Store in `patterns` table with:
   - `problem_type`: Category (e.g., "REST API", "Data Processing")
   - `code_template`: Reusable code
   - `test_template`: Associated test pattern
   - `embedding`: Vector for similarity search
   - `usage_count`: Increment when pattern is retrieved

### Failure Storage

**When**: After task FAILED or iteration fails tests
**What**: Store error + solution if eventually fixed
**Process**:
1. Extract error signature (normalized error message)
2. Generate embedding
3. Store in `failures` table with:
   - `error_signature`: Normalized pattern
   - `error_type`: ImportError, AttributeError, etc.
   - `solution`: What fixed it (if known)
   - `code_context`: Relevant code snippet
   - `embedding`: Vector for similarity search

### Pattern Retrieval

**When**: PLANNING state (search patterns), REFLECTING state (search failures)
**Process**:
1. Generate embedding for query (task description or error message)
2. Query PostgreSQL with pgvector:
   ```sql
   SELECT id, code_template, solution, usage_count
   FROM patterns
   ORDER BY embedding <=> query_embedding
   LIMIT 5
   ```
3. Return top 5 most similar results
4. LLM uses retrieved patterns to generate plan or fix

### Learning Effectiveness

Track metrics:
- **Pattern hit rate**: % of planning queries that find useful patterns
- **Failure hit rate**: % of reflections that find similar past failures
- **Pattern success rate**: % of patterns that led to task success
- **Usage count**: Most frequently used patterns

---

## Safety Mechanisms

### Pre-Execution Safety (AST Scanning)

**Scanner** (`src/sandbox/safety_checker.py`):
- Parse generated code with Python AST
- Block dangerous operations:
  - `eval()` and `exec()` calls
  - `__import__` built-in
  - Imports of dangerous modules: os, subprocess, pty, socket, sys
- Return list of violations or pass

**Result**:
- If violations: Block execution, log warning, ask user
- If clean: Proceed to execution

### SAST Scanning (Bandit)

**Scanner**:
- Run `bandit` on generated code
- Check for SQL injection, hardcoded secrets, unsafe functions
- Configurable severity threshold

**Result**:
- HIGH severity: Block execution
- MEDIUM severity: Warn, ask user
- LOW severity: Allow with log

### User Approval Flow

**When**: Network access, subprocess, new dependencies, safety violation

**Process**:
1. CLI prompts: "Agent requests [operation]. Approve? [Y/n]"
2. User enters Y or n
3. Store decision in `approvals` table
4. If approved: Execute operation
5. If denied: Log, generate alternative approach

**Learning from Approvals**:
- Track which requests are typically approved
- Suggest auto-approve for common safe operations

### Docker Sandbox Execution

**Container Setup**:
- Base image: `python:3.11-slim`
- Non-root user: `sandbox_user` (uid 1000)
- Working directory: `/workspace` (bind mount)
- Resource limits: CPU 1 core, RAM 1GB, timeout 5 min
- Network: disabled (approval required to enable)
- Read-only: entire filesystem except `/workspace`

**Test Execution**:
```bash
docker run --rm \
  --cpus=1 \
  --memory=1g \
  --network=none \
  --user=1000 \
  -v /path/to/workspace:/workspace \
  -w /workspace \
  python-sandbox \
  pytest tests/ -v --tb=short
```

---

## Error Handling

### LLM API Errors

**Types**: Rate limits, timeouts, service unavailable

**Handling**:
- Retry with exponential backoff (Tenacity)
- Max 3 attempts
- Log warnings for each retry
- After failures: Use fallback model or mark task as FAILED

### Database Errors

**Types**: Connection failed, query failed, deadlock

**Handling**:
- Retry transient errors (connection lost)
- Log error with context
- If persistent: Mark task as PAUSED
- Provide error details to user

### Docker Errors

**Types**: Container spawn failed, execution timeout

**Handling**:
- Log full error message
- If spawn failed: Check Docker daemon, mark task as PAUSED
- If timeout: Increase timeout (configurable), retry

### Code Generation Errors

**Types**: Tool call invalid, code won't parse, circular dependencies

**Handling**:
- Validate tool calls before execution
- Compile generated code before testing
- If error: Pass to Reflector for analysis
- Loop continues until fix found or max iterations

---

## User Interactions

### Interactive Commands

**Start Task**:
```bash
python -m src.main run
# Prompts: task description, language, task type
```

**Resume Task**:
```bash
python -m src.main --resume <task_id>
# Reloads state from database checkpoints
```

**View History**:
```bash
python -m src.main --history
# Lists all tasks with status, iterations, duration
```

**View Metrics**:
```bash
python -m src.main --metrics
# Shows success rate, avg iterations, token usage
```

### Approval Prompts

**Examples**:
```
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
```

```
⚠️  SAFETY VIOLATION
┌─────────────────────────────────────────────────────────────┐
│  Code contains blocked import: 'socket'                     │
│                                                             │
│  This could be dangerous.                                   │
│  Review code and approve? [Y/n]:                           │
└─────────────────────────────────────────────────────────────┘
```

### Real-Time Progress

Rich CLI shows:
```
╭─────────────────────────────────────────────────────────────╮
│  ITERATION 3/15                                             │
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
```

---

## Edge Cases and Limitations

### Known Limitations

1. **Task Complexity**: Limited to single-file or simple multi-file projects
   - Can't handle large refactoring across many files
   - May struggle with domain-specific knowledge

2. **Iteration Limits**: Max 15 iterations
   - Complex tasks may need more attempts
   - User can restart with different description

3. **Language Support**: Primarily Python
   - Can generate code for any language
   - But testing/scaffolding optimized for Python
   - Node.js/Go support requires additional work

4. **Memory Learning**: Requires history
   - Cold start: No patterns in database
   - Improves over time as tasks complete

5. **Network Access**: Blocked by default
   - Requires user approval
   - May block legitimate API usage
   - User can pre-approve domains in config

### Edge Case Handling

**Empty Task**: Return error, prompt for valid description
**Ambiguous Task**: Planner asks for clarification via CLI
**Circular Dependencies**: Reflector detects, asks user for guidance
**Memory Exhausted**: Docker OOM kills container, log error, retry with more RAM
**Database Full**: Alert user, suggest cleanup of old tasks
**LLM Hallucination**: Tests fail → Reflector → Loop until working code
**Infinite Loop**: Circuit breaker at 15 iterations, mark FAILED
**User Interruption**: Ctrl+C → graceful shutdown, checkpoint state
**Network Outage**: Retry with backoff, pause if persistent
**Docker Daemon Down**: Detect on startup, alert user, pause task

---

## Observability

### Structured Logging

**Format**: JSON via structlog
**Fields**: timestamp, level, task_id, iteration, agent, message, metadata

**Example**:
```json
{
  "timestamp": "2025-01-21T10:30:45Z",
  "level": "info",
  "task_id": "abc-123",
  "iteration": 3,
  "agent": "coder",
  "message": "Generated file: app.py",
  "metadata": {
    "file_size": 1450,
    "tokens_used": 1200
  }
}
```

**Log Levels**:
- `debug`: Detailed agent internals
- `info`: State transitions, progress updates
- `warning`: Safety violations, retries
- `error`: Failed operations, API errors
- `critical`: System failures, task abandonment

### Metrics Collection

**Stored in `metrics` table**:

| Metric Type | Example | Purpose |
|-------------|----------|---------|
| `duration` | 245.5 | Task duration in seconds |
| `token_usage` | 8450 | Total tokens consumed |
| `success` | 1 or 0 | Task completion status |
| `error_rate` | 0.33 | Failed iterations / total |
| `memory_hit_rate` | 0.8 | Patterns found / queries |
| `safety_violations` | 2 | Blocked operations |

**Dashboard Queries**:
- Success rate by task type
- Average iterations per task
- Token usage per month
- Most common error types
- Top patterns by usage

### State Persistence

**Checkpoints**: Every 5 iterations
- Store in `iterations` table
- Code snapshot, test results, reflection, hypothesis
- Enables resume after crash/interruption

**Resuming**:
```bash
python -m src.main --resume <task_id>
# Loads last checkpoint
# Continues from appropriate state
```

---

**Last Updated**: 2025-01-21
**Purpose**: System behavior documentation for developers and AI agents
