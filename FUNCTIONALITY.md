# FUNCTIONALITY.md

> **Purpose**: Comprehensive documentation of how the Autonomous Coding Agent system functions, including operational flows, behaviors, and edge case handling.

---

## 📑 Table of Contents

1. [Core Functionality](#core-functionality)
2. [Iteration Loop Behavior](#iteration-loop-behavior)
3. [Agent Behaviors](#agent-behaviors)
4. [Tool Use Mechanics](#tool-use-mechanics)
5. [Memory and Learning](#memory-and-learning)
6. [Safety Mechanisms](#safety-mechanisms)
7. [Error Handling](#error-handling)
8. [User Interactions](#user-interactions)
9. [Edge Cases and Limitations](#edge-cases-and-limitations)
10. [Observability](#observability)

---

## 1. Core Functionality

### 1.1 What the System Does

The Autonomous Coding Agent accepts a high-level coding task and **autonomously** generates working code through iterative refinement:

1. **Understands the task**: Breaks down requirements into actionable subtasks
2. **Generates code**: Creates files using LLM-powered code generation
3. **Tests itself**: Generates and runs tests to validate correctness
4. **Learns from failures**: Analyzes errors and searches for similar past solutions
5. **Iterates until success**: Continues the loop up to 15 times or until tests pass

**Key Differentiator**: This is **not** a code completion tool or chatbot. It's an autonomous agent that runs in a loop until the goal is achieved.

### 1.2 Input and Output

**Input**:
```bash
python -m src.main run \
    --task "Build a REST API with endpoints for creating and listing todos" \
    --language python
```

**Output** (in workspace):
```
workspace_<task_id>/
├── main.py           # Generated code
├── requirements.txt  # Dependencies
├── tests/
│   ├── test_api.py   # Generated tests
│   └── test_todos.py
└── README.md         # Auto-generated documentation (optional)
```

**Terminal Output** (Rich UI):
```
╭─────────────────────────────────────────────────────────╮
│ Task: Build a REST API for todos                        │
│ Status: ● Running (Iteration 3/15)                      │
╰─────────────────────────────────────────────────────────╯

  ✓ Planning complete (2 subtasks identified)
  ✓ Code generated (2 files created)
  ⚠ Tests failed (3 passed, 2 failed)
  ◆ Reflecting on failures...

  Found similar failure: "KeyError when accessing todo item"
  Fix hypothesis: Add validation for missing keys

  ► Retrying with fixes...
```

---

## 2. Iteration Loop Behavior

### 2.1 The Autonomous Loop

```
Iteration 1:  PLANNING → CODING → TESTING (failed) → REFLECTING
Iteration 2:                       CODING → TESTING (failed) → REFLECTING
Iteration 3:                       CODING → TESTING (failed) → REFLECTING
...
Iteration N:                       CODING → TESTING (passed!) → SUCCESS ✅
```

**Key Characteristics**:
- **Planning happens once** (iteration 1 only)
- **Coding, Testing, Reflecting repeat** until success or max iterations
- **Context accumulates**: Each iteration has access to all previous feedback
- **Circuit breaker**: Warning at iteration 12, hard stop at iteration 15

### 2.2 State Transitions in Detail

#### INIT State

**Purpose**: Set up environment for task execution

**Operations**:
1. Create unique workspace directory: `workspace_<task_id>/`
2. Load configuration from YAML files
3. Initialize LLM client with retry logic
4. Create database record for task (status='running')
5. Initialize context dictionary
6. Set up logging (task-specific log file)

**Next State**: Always transitions to PLANNING

**Duration**: <1 second

#### PLANNING State

**Purpose**: Decompose task into actionable subtasks

**Operations**:
1. **Embed task description** using OpenAI embeddings
2. **Query vector DB** for similar successful patterns (similarity > 0.7)
3. **Build LLM prompt** with:
   - Task description
   - Language (Python/Node.js)
   - Similar patterns from memory (if any)
   - System prompt: "You are an expert architect..."
4. **Call OpenAI API** (model: gpt-4-turbo-preview)
5. **Parse response**:
   - List of subtasks
   - Expected challenges
   - Testing strategy
6. **Store plan in context**
7. **Log to database** (iterations table)

**Next State**: Always transitions to CODING

**Duration**: 5-10 seconds (depends on LLM latency)

**Example Plan Output**:
```json
{
  "subtasks": [
    "Create Flask app with route definitions",
    "Implement todo CRUD operations",
    "Add input validation",
    "Set up in-memory storage"
  ],
  "expected_challenges": [
    "Handling concurrent access to shared data",
    "Input validation for missing fields"
  ],
  "testing_strategy": "Unit tests for each endpoint, integration tests for full flow"
}
```

#### CODING State

**Purpose**: Generate code based on plan and feedback

**Operations**:
1. **Build LLM prompt** with:
   - Original task
   - Implementation plan (from PLANNING)
   - Previous iteration feedback (if any):
     - Failed tests
     - Error messages
     - Fix hypothesis from REFLECTING
   - System prompt: "You are an expert software engineer..."
   - Available tools: create_file, read_file, list_files
2. **Call OpenAI API with function calling**
3. **Process tool calls** (LLM decides which files to create):
   ```python
   # Example tool calls from LLM:
   create_file(path="main.py", content="from flask import Flask...")
   create_file(path="tests/test_api.py", content="import pytest...")
   ```
4. **Write files to workspace**
5. **Store code in context**:
   - File paths
   - File contents (for analysis)
6. **Log iteration to database**

**Next State**: Always transitions to TESTING

**Duration**: 10-20 seconds (depends on code complexity)

**Iteration Behavior**:
- **First iteration**: Generates code from scratch based on plan
- **Subsequent iterations**: Reads existing code and makes targeted fixes based on reflection

#### TESTING State

**Purpose**: Validate generated code

**Operations**:
1. **Generate tests** (if not already generated):
   - Build LLM prompt with code files
   - System prompt: "Generate comprehensive pytest tests..."
   - Include property-based tests (hypothesis library)
2. **Write test files** to workspace
3. **AST scan all code** for dangerous operations:
   - Check for blocked imports (os, subprocess, etc.)
   - Check for blocked function calls (eval, exec, etc.)
   - Check file paths are within workspace
4. **Bandit security scan** (SAST):
   - Scan for SQL injection, hardcoded secrets, etc.
   - Generate severity scores
5. **Prompt user for approval** (if needed):
   - Network access requests
   - Subprocess calls
   - Dependency installations
6. **Create Docker container**:
   - Image: Python 3.11 or Node.js (based on language)
   - Resource limits: 1 CPU, 1GB RAM, 5min timeout
   - Network: Disabled (unless approved)
   - Mount workspace as /workspace
7. **Run tests in container**:
   - Command: `pytest tests/ -v --json=results.json`
   - Capture: stdout, stderr, exit code
8. **Parse test results**:
   - Extract passed/failed counts
   - Extract error messages and stack traces
   - Calculate coverage (if pytest-cov installed)
9. **Store results in context**

**Next State**:
- If **all tests passed** (pass_rate = 100%): Transition to SUCCESS
- If **any tests failed**: Transition to REFLECTING

**Duration**: 10-30 seconds (depends on test execution time)

**Example Test Results**:
```json
{
  "total": 10,
  "passed": 7,
  "failed": 3,
  "errors": [
    {
      "test": "test_create_todo",
      "error_type": "KeyError",
      "message": "'title'",
      "traceback": "File \"test_api.py\", line 15, in test_create_todo\n    assert response.json()['title'] == 'Buy milk'\nKeyError: 'title'"
    }
  ],
  "coverage": 78.5
}
```

#### REFLECTING State

**Purpose**: Analyze failures and plan fixes

**Operations**:
1. **Extract failure context**:
   - Error messages
   - Stack traces
   - Failing test names
   - Relevant code snippets (from traceback)
2. **Embed error context** using OpenAI embeddings
3. **Query vector DB** for similar past failures (similarity > 0.6)
4. **Build LLM prompt** with:
   - Test failures
   - Code that failed
   - Similar past failures and their solutions (from memory)
   - System prompt: "You are an expert debugger..."
5. **Call OpenAI API**
6. **Parse analysis**:
   - Root cause identification
   - Fix hypothesis (specific, actionable)
   - Confidence level (high/medium/low)
7. **Store failure in vector DB** (for future learning):
   - Error message + embedding
   - Solution (filled in later if fixed)
8. **Store analysis in context**
9. **Increment iteration counter**
10. **Check circuit breaker**:
    - If iteration == 12: Log warning ("approaching max iterations")
    - If iteration >= 15: Transition to FAILED
11. **Log iteration to database**

**Next State**:
- If **iteration < 15**: Transition to CODING (with fix hypothesis)
- If **iteration >= 15**: Transition to FAILED

**Duration**: 5-10 seconds

**Example Analysis Output**:
```json
{
  "root_cause": "The API endpoint returns a JSON object with key 'name' but the test expects 'title'",
  "similar_failures": [
    {
      "task": "REST API for books",
      "error": "KeyError: 'author'",
      "solution": "Renamed database column from 'writer' to 'author'",
      "similarity": 0.85
    }
  ],
  "fix_hypothesis": "Change the response key from 'name' to 'title' in main.py line 42, or update the test to expect 'name' instead of 'title'",
  "confidence": "high"
}
```

#### SUCCESS State

**Purpose**: Task completed successfully

**Operations**:
1. **Update database**: Set task status = 'success'
2. **Store solution as pattern** in vector DB:
   - Embed task description + code
   - Store in patterns table for future retrieval
3. **Log final metrics**:
   - Total iterations
   - Total tokens used
   - Total cost estimate
   - Total duration
4. **Display results to user**:
   - Success message
   - Files created
   - Metrics
5. **Clean up** (optional):
   - Keep workspace for inspection
   - Archive logs

**Next State**: Terminal state (no transition)

**Duration**: <1 second

#### FAILED State

**Purpose**: Task failed (max iterations reached)

**Operations**:
1. **Update database**: Set task status = 'failed'
2. **Log failure reason**: "Max iterations reached"
3. **Store partial solution** (if useful):
   - Even failed attempts can be learning opportunities
4. **Display failure summary**:
   - Last error message
   - Iteration count
   - Suggestion: "Try breaking down the task further"
5. **Checkpoint state** (for resume)

**Next State**: Terminal state (no transition)

**Duration**: <1 second

**User Options**:
- Inspect workspace to see what was generated
- Resume with `python -m src.main resume <task_id>` (gives 15 more iterations)
- Manually fix code and re-run tests

#### PAUSED State

**Purpose**: User interrupted execution (Ctrl+C)

**Operations**:
1. **Graceful shutdown**:
   - Wait for current LLM call to finish
   - Save checkpoint state
2. **Update database**: Set task status = 'paused'
3. **Display pause message**:
   - "Task paused. Resume with: python -m src.main resume <task_id>"

**Next State**: Can transition to any state on resume

**Duration**: Immediate

### 2.3 Iteration Metrics

**Tracked per iteration**:
- State entered/exited
- Duration (seconds)
- Tokens used (prompt + completion)
- Files created/modified
- Tests passed/failed
- Error messages (if any)

**Aggregated per task**:
- Total iterations
- Total duration
- Total tokens
- Success rate
- Cost estimate

---

## 3. Agent Behaviors

### 3.1 PlannerAgent

**Invoked**: Once at the start (PLANNING state)

**Behavior**:
- Reads task description
- Breaks down into 2-5 subtasks
- Prioritizes subtasks by dependency
- Identifies edge cases and challenges
- Suggests testing approach

**Prompt Engineering**:
- Temperature: 0.3 (slightly creative for planning)
- Max tokens: 2048 (plans are concise)
- System prompt emphasizes: "Break down into concrete, testable subtasks"

**Output Quality Factors**:
- ✅ Good: Clear, specific subtasks ("Implement POST /todos endpoint")
- ❌ Bad: Vague subtasks ("Make it work", "Add features")

**Example**:

**Input**: "Build a CLI tool that converts CSV to JSON"

**Output**:
```json
{
  "subtasks": [
    "Parse command-line arguments (input file, output file)",
    "Read CSV file and validate format",
    "Convert CSV rows to JSON objects",
    "Write JSON to output file",
    "Handle errors (file not found, invalid CSV)"
  ],
  "dependencies": {
    "subtask_2": ["subtask_1"],
    "subtask_3": ["subtask_2"]
  },
  "expected_challenges": [
    "Handling CSV files with quotes and commas in values",
    "Memory efficiency for large files"
  ]
}
```

### 3.2 CoderAgent

**Invoked**: Every iteration in CODING state

**Behavior**:
- Reads plan and previous feedback
- Decides which files to create/modify
- Uses function calling to interact with workspace
- Follows language-specific conventions
- Includes error handling and edge case logic

**Tool Decision Process**:
1. **First iteration**: Use `list_files()` to check workspace (empty)
2. **Decide**: Need to create `main.py`
3. **Call**: `create_file(path="main.py", content="...")`
4. **Decide**: Need to create `tests/test_main.py`
5. **Call**: `create_file(path="tests/test_main.py", content="...")`
6. **Finish**: Return control to orchestrator

**Subsequent iterations**:
1. **Read feedback**: "KeyError: 'title' at line 42"
2. **Call**: `read_file(path="main.py")` to see current code
3. **Decide**: Need to fix line 42
4. **Call**: `create_file(path="main.py", content="...")` (overwrites)
5. **Finish**: Return control to orchestrator

**Prompt Engineering**:
- Temperature: 0.2 (deterministic code generation)
- Max tokens: 4096 (sufficient for most code files)
- System prompt emphasizes: "Clean, well-documented, production-quality code"

**Output Quality Factors**:
- ✅ Good: Type hints, docstrings, error handling, clear variable names
- ❌ Bad: No error handling, unclear names, missing edge cases

### 3.3 TesterAgent

**Invoked**: Every iteration in TESTING state

**Behavior**:
- Reads generated code
- Generates comprehensive tests:
  - Happy path tests
  - Edge case tests (empty input, invalid input)
  - Error handling tests
  - Property-based tests (hypothesis)
- Executes tests in Docker sandbox
- Parses test output

**Test Generation Strategy**:

For a function like:
```python
def add(a: int, b: int) -> int:
    return a + b
```

Generated tests:
```python
def test_add_positive_numbers():
    assert add(2, 3) == 5

def test_add_negative_numbers():
    assert add(-2, -3) == -5

def test_add_zero():
    assert add(0, 0) == 0

@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    """Property: addition is commutative"""
    assert add(a, b) == add(b, a)
```

**Prompt Engineering**:
- Temperature: 0.3 (creative test cases)
- Max tokens: 4096
- System prompt emphasizes: "Comprehensive tests including edge cases and property-based tests"

**Test Execution**:
```bash
# Inside Docker container
pytest tests/ -v --json=results.json --cov=src --cov-report=json
```

**Output Parsing**:
- Extracts passed/failed counts from pytest JSON
- Extracts error messages and tracebacks
- Extracts coverage percentage from coverage.json

### 3.4 ReflectorAgent

**Invoked**: Every iteration in REFLECTING state (only if tests failed)

**Behavior**:
- Reads test failures
- Identifies root cause (not just symptom)
- Queries vector DB for similar past failures
- Generates specific, actionable fix hypothesis

**Analysis Process**:

**Input**: Test failure
```
test_create_todo FAILED
KeyError: 'title'
  File "test_api.py", line 15
    assert response.json()['title'] == 'Buy milk'
```

**Root Cause Analysis**:
1. **Symptom**: KeyError when accessing 'title' key
2. **Proximate cause**: Response JSON doesn't have 'title' key
3. **Root cause**: Code returns 'name' key instead of 'title' key
4. **Why**: Likely mismatch between API contract and test expectations

**Memory Search**:
- Embed: "KeyError accessing JSON response key in REST API"
- Find similar failures: 3 matches with similarity > 0.6
- Best match: "KeyError: 'author' - Fixed by renaming response key" (similarity: 0.85)

**Fix Hypothesis**:
"The API endpoint returns a JSON object with key 'name' but the test expects 'title'. Solution: Change response key from 'name' to 'title' in main.py at line 42."

**Confidence**: High (similar past failure was fixed this way)

**Prompt Engineering**:
- Temperature: 0.2 (precise analysis)
- Max tokens: 2048
- System prompt emphasizes: "Identify root cause, not symptoms. Be specific."

---

## 4. Tool Use Mechanics

### 4.1 Function Calling Flow

```
[CoderAgent]
  │
  ├─> Build prompt with task + tools
  │
  ▼
[OpenAI API]
  │
  ├─> LLM decides to call function
  ├─> Returns: function_call object
  │   {
  │     "name": "create_file",
  │     "arguments": "{\"path\": \"main.py\", \"content\": \"...\"}"
  │   }
  │
  ▼
[CoderAgent._handle_tool_call()]
  │
  ├─> Parse arguments (JSON)
  ├─> Validate (path must be in workspace)
  ├─> Execute (write file to disk)
  ├─> Return result: {"success": true, "path": "main.py"}
  │
  ▼
[CoderAgent sends result back to LLM]
  │
  ├─> LLM sees: "File created successfully"
  ├─> LLM decides: Call another function or finish
  │
  └─> [Loop until LLM says "finish"]
```

### 4.2 Available Tools

#### create_file

**Purpose**: Create a new file with content (overwrites if exists)

**Parameters**:
- `path` (string, required): File path relative to workspace
- `content` (string, required): File content

**Validation**:
- Path must not contain `..` (prevent directory traversal)
- Path must be within workspace
- Content must be valid UTF-8

**Returns**:
```json
{
  "success": true,
  "path": "main.py",
  "bytes_written": 1234
}
```

**Error Cases**:
- Invalid path: Returns `{"error": "Path must be within workspace"}`
- Encoding error: Returns `{"error": "Content must be valid UTF-8"}`

#### read_file

**Purpose**: Read an existing file from workspace

**Parameters**:
- `path` (string, required): File path relative to workspace

**Validation**:
- Path must exist
- Path must be within workspace
- File must be readable (not binary)

**Returns**:
```json
{
  "success": true,
  "path": "main.py",
  "content": "from flask import Flask...",
  "size_bytes": 1234
}
```

**Error Cases**:
- File not found: Returns `{"error": "File not found: main.py"}`
- Binary file: Returns `{"error": "Cannot read binary file"}`

#### list_files

**Purpose**: List all files in workspace

**Parameters**: None

**Returns**:
```json
{
  "success": true,
  "files": [
    {"path": "main.py", "size": 1234, "modified": "2026-01-16T10:30:00Z"},
    {"path": "tests/test_main.py", "size": 567, "modified": "2026-01-16T10:30:05Z"}
  ],
  "total_files": 2
}
```

### 4.3 Tool Usage Patterns

**Pattern 1: Create from scratch** (first iteration)
```
list_files()  → []
create_file(path="main.py", content="...")
create_file(path="tests/test_main.py", content="...")
```

**Pattern 2: Fix existing code** (subsequent iterations)
```
list_files()  → ["main.py", "tests/test_main.py"]
read_file(path="main.py")  → "Current code..."
create_file(path="main.py", content="Fixed code...")  # Overwrite
```

**Pattern 3: Incremental development**
```
list_files()  → ["main.py"]
read_file(path="main.py")
create_file(path="utils.py", content="...")  # Add new file
create_file(path="main.py", content="... import utils ...")  # Update existing
```

---

## 5. Memory and Learning

### 5.1 What Gets Stored

**Failures** (in `failures` table):
- Error type (KeyError, TypeError, etc.)
- Error message
- Stack trace
- Failing code snippet
- Solution (filled in if fixed)
- Embedding (1536-dim vector)

**Patterns** (in `patterns` table):
- Task type ("REST API", "CLI tool", "data processing")
- Task description
- Solution code (all files as JSON)
- Implementation notes
- Language
- Embedding (1536-dim vector)
- Success rate (how often this pattern worked)
- Times used (retrieval counter)

**Example**:

After successfully building a REST API:
```sql
INSERT INTO patterns (
    task_type,
    task_description,
    solution_code,
    language,
    embedding
) VALUES (
    'rest_api',
    'REST API with CRUD operations for todos',
    '{"main.py": "from flask import Flask...", "tests/test_api.py": "..."}',
    'python',
    [0.123, -0.456, ...]  -- 1536-dimensional vector
);
```

### 5.2 When Memory is Queried

**PlannerAgent** (PLANNING state):
- Query: Task description embedding
- Search: patterns table
- Threshold: similarity > 0.7
- Purpose: Find similar successful implementations
- Result: Top 3 patterns included in planning prompt

**ReflectorAgent** (REFLECTING state):
- Query: Error message + stack trace embedding
- Search: failures table
- Threshold: similarity > 0.6
- Purpose: Find similar past errors and their solutions
- Result: Top 5 failures included in reflection prompt

### 5.3 Embedding Strategy

**What gets embedded**:

| Content Type | Embedding Input | Purpose |
|-------------|----------------|---------|
| Task description | Full task text | Pattern matching |
| Error context | Error type + message + relevant code | Failure matching |
| Solution pattern | Task description + code summary | Pattern retrieval |

**Embedding Model**: `text-embedding-3-large`
- Dimensions: 1536
- Cost: $0.00013 per 1K tokens
- Quality: High (better than text-embedding-ada-002)

**Optimization**: Cache embeddings for identical text
```python
# Before
for each query:
    embedding = openai.embed(query)  # API call every time

# After
@lru_cache(maxsize=1000)
def embed_cached(text: str) -> tuple:
    return tuple(openai.embed(text))  # Cached for identical text
```

### 5.4 Retrieval Quality

**Factors affecting retrieval quality**:
1. **Similarity threshold**:
   - Too high (>0.9): Miss relevant results
   - Too low (<0.5): Get irrelevant results
   - Sweet spot: 0.6-0.7
2. **Embedding quality**:
   - More detailed context = better embeddings
   - "KeyError" (bad) vs "KeyError when accessing JSON key in REST API" (good)
3. **Result ranking**:
   - Primary: Similarity score
   - Secondary: Recency (newer = better)
   - Tertiary: Success rate (for patterns)

**Example Query**:

Task: "Build a CLI tool for CSV to JSON conversion"

Embedded as: `[0.123, -0.456, ...]` (1536 dimensions)

Search patterns table:
```sql
SELECT
    task_description,
    solution_code,
    1 - (embedding <=> $1::vector) AS similarity
FROM patterns
WHERE 1 - (embedding <=> $1::vector) > 0.7
ORDER BY similarity DESC, created_at DESC
LIMIT 3;
```

Results:
1. "CLI tool for JSON to CSV conversion" (similarity: 0.89) ← Very similar!
2. "CLI argument parser with file I/O" (similarity: 0.76)
3. "CSV parser with validation" (similarity: 0.72)

These 3 patterns are included in the planning prompt.

---

## 6. Safety Mechanisms

### 6.1 Layer 1: AST Scanning

**Performed**: Before Docker execution (in TESTING state)

**Scans for**:
- Blocked imports: os, subprocess, socket, pty, __import__, eval, exec
- Blocked function calls: eval(), exec(), compile(), open() outside workspace
- Dangerous operations: ctypes, pickle

**Implementation**:
```python
import ast

tree = ast.parse(code)

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name in DANGEROUS_IMPORTS:
                raise SecurityViolation(f"Blocked import: {alias.name}")

    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in DANGEROUS_CALLS:
                raise SecurityViolation(f"Blocked call: {node.func.id}()")
```

**Action on violation**: Block execution, log, transition to REFLECTING

### 6.2 Layer 2: Bandit Scanning

**Performed**: Before Docker execution (in TESTING state)

**Scans for**:
- SQL injection vulnerabilities
- Hardcoded passwords/secrets
- Use of insecure functions (md5, random instead of secrets)
- Shell injection (subprocess with shell=True)

**Implementation**:
```bash
bandit -r workspace/ -f json -o bandit_results.json
```

**Severity levels**:
- **Low**: Warning, allow execution
- **Medium**: Require user approval
- **High**: Block execution

**Action on high severity**: Block execution, log, display warning to user

### 6.3 Layer 3: User Approval

**Triggered by**:
- Network access requests (import requests, socket, urllib)
- Subprocess calls (subprocess.run, os.system)
- Installing dependencies (pip install, npm install)

**Approval Prompt**:
```
╭─────────────────────────────────────────────────────────╮
│ ⚠️  Approval Required                                    │
├─────────────────────────────────────────────────────────┤
│ Operation: Network access                               │
│ Details: Code attempts to import 'requests' library     │
│ Risk Level: Medium                                      │
│                                                          │
│ Code snippet:                                           │
│   import requests                                       │
│   response = requests.get('https://api.example.com')   │
│                                                          │
│ Allow this operation? (Y/n)                             │
╰─────────────────────────────────────────────────────────╯
```

**User Options**:
- **Yes**: Allow and continue execution
- **No**: Block and transition to REFLECTING (agent must find alternative approach)
- **Always for this task**: Allow for all iterations of this task

**Logged**: All approval decisions stored in `approvals` table for audit

### 6.4 Layer 4: Docker Sandboxing

**Isolation**:
- **Filesystem**: Only `/workspace` is writable (bind mount)
- **Network**: Disabled by default (requires approval to enable)
- **User**: Non-root (UID 1000, username: sandbox_user)
- **Host access**: None (container can't see host filesystem or processes)

**Resource Limits**:
```python
container = docker.run(
    cpus=1.0,              # Max 1 CPU core
    mem_limit="1g",        # Max 1GB RAM
    pids_limit=100,        # Max 100 processes
    timeout=300,           # Max 5 minutes
    network_mode="none"    # No network
)
```

**What happens on limit breach**:
- **CPU/RAM**: Container throttled (slowed down)
- **Timeout**: Container killed, execution marked as failed
- **Process limit**: New processes fail to spawn

**Security Trade-offs**:
- ✅ Good enough for educational/development use
- ❌ Not suitable for production/untrusted code (shared kernel)
- 🔐 For stronger isolation: Use Firecracker microVMs

---

## 7. Error Handling

### 7.1 Error Categories

**1. User Errors** (invalid input)
- Invalid task description (empty string)
- Invalid language choice (not "python" or "node")
- Task too vague ("make something cool")

**Handling**: Reject early with helpful error message

**2. LLM Errors** (API failures)
- Rate limit exceeded (429)
- Invalid API key (401)
- Service unavailable (503)
- Token limit exceeded (400)

**Handling**: Retry with exponential backoff (3 attempts), then fail gracefully

**3. Code Generation Errors** (agent generated bad code)
- Syntax errors in generated code
- Import errors (missing dependencies)
- Logic errors (tests fail)

**Handling**: Iteration loop (REFLECTING state analyzes and retries)

**4. Execution Errors** (sandbox failures)
- Docker daemon not running
- Out of memory in container
- Timeout (execution > 5 minutes)

**Handling**: Log error, notify user, offer to retry with more resources

**5. System Errors** (infrastructure failures)
- Database connection lost
- Disk full (can't write workspace files)
- Out of memory (host system)

**Handling**: Checkpoint state, fail gracefully, allow resume

### 7.2 Retry Strategies

**LLM API Calls** (exponential backoff):
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def call_openai(prompt):
    return await openai.chat.completions.create(...)

# Attempt 1: Immediate
# Attempt 2: Wait 2 seconds
# Attempt 3: Wait 4 seconds
# Give up: Raise exception
```

**Database Queries** (immediate retry):
```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(OperationalError)
)
async def execute_query(query):
    return await db.execute(query)

# Attempt 1: Immediate
# Attempt 2: Wait 1 second
# Give up: Raise exception
```

**Docker Operations** (no retry):
- Docker failures are usually deterministic (e.g., image not found)
- Retrying won't help
- Fail fast and show clear error message

### 7.3 Graceful Degradation

**Scenario**: Vector DB is slow or unavailable

**Without degradation**:
```python
patterns = await vector_store.search_similar(task)  # Hangs for 30s or fails
# Entire system blocked
```

**With degradation**:
```python
try:
    patterns = await asyncio.wait_for(
        vector_store.search_similar(task),
        timeout=5.0
    )
except asyncio.TimeoutError:
    logger.warning("Vector search timed out, continuing without similar patterns")
    patterns = []  # Empty results, but system continues

# Planner still works, just without memory context
```

**Scenario**: LLM is temporarily unavailable

**Without degradation**: System crashes

**With degradation**:
```python
# Try primary model
try:
    response = await openai.call(model="gpt-4-turbo")
except ServiceUnavailableError:
    # Try fallback model
    logger.warning("GPT-4 unavailable, falling back to GPT-3.5")
    response = await openai.call(model="gpt-3.5-turbo")

# Quality may be lower, but task can complete
```

---

## 8. User Interactions

### 8.1 Starting a Task

**Command**:
```bash
python -m src.main run --task "Build a REST API for todos" --language python
```

**Interactive Mode** (no --task flag):
```bash
python -m src.main run

╭─────────────────────────────────────────────────────────╮
│ Autonomous Coding Agent                                  │
╰─────────────────────────────────────────────────────────╯

Enter your coding task:
> Build a REST API for managing a todo list

Select language (python/node): python

Starting task...
```

**Validation**:
- Task description: Min 10 characters, max 500 characters
- Language: Must be "python" or "node"

**Confirmation**:
```
╭─────────────────────────────────────────────────────────╮
│ Task Summary                                             │
├─────────────────────────────────────────────────────────┤
│ Task: Build a REST API for managing a todo list         │
│ Language: Python                                         │
│ Max Iterations: 15                                       │
│ Estimated Cost: $0.50 - $2.00 (based on past tasks)     │
│                                                          │
│ Proceed? (Y/n)                                           │
╰─────────────────────────────────────────────────────────╯
```

### 8.2 Monitoring Progress

**Real-time UI** (using Rich library):

```
╭────────────────────────────────────────────────────────────────╮
│ 🤖 Autonomous Coding Agent                                     │
│ Task: Build a REST API for todos                               │
│ Status: ● Running                                              │
╰────────────────────────────────────────────────────────────────╯

 Iteration 3 of 15  ████████░░░░░░░░░░  20%

 ✓ Planning      Complete (2 subtasks identified)
 ✓ Coding        Complete (3 files created)
 ✗ Testing       Failed (7 passed, 3 failed)
 ◆ Reflecting    In progress...

Recent Events:
 [10:30:15] Code generated: main.py, tests/test_api.py
 [10:30:22] Tests executed: 7/10 passed
 [10:30:23] Error: KeyError at line 42 in main.py
 [10:30:25] Found similar failure (similarity: 0.85)
 [10:30:27] Generating fix hypothesis...

Logs: /path/to/logs/task_abc123.log
Workspace: /path/to/workspace_abc123/
```

**Keyboard Controls**:
- `Ctrl+C`: Pause task (checkpoint and exit)
- `Ctrl+\`: Force quit (no checkpoint, not recommended)

### 8.3 Viewing Results

**On Success**:
```
╭────────────────────────────────────────────────────────────────╮
│ ✅ Task Completed Successfully!                                │
├────────────────────────────────────────────────────────────────┤
│ Iterations: 5 of 15                                            │
│ Duration: 2m 34s                                               │
│ Files Created: 4                                               │
│ Tests Passed: 12/12                                            │
│ Estimated Cost: $1.23                                          │
╰────────────────────────────────────────────────────────────────╯

Files Generated:
  ✓ main.py (234 lines)
  ✓ requirements.txt (5 packages)
  ✓ tests/test_api.py (89 lines)
  ✓ README.md (auto-generated)

Workspace: /home/user/workspace_abc123/

Next Steps:
  1. cd /home/user/workspace_abc123/
  2. pip install -r requirements.txt
  3. python main.py
  4. Visit http://localhost:5000
```

**On Failure**:
```
╭────────────────────────────────────────────────────────────────╮
│ ❌ Task Failed (Max Iterations Reached)                        │
├────────────────────────────────────────────────────────────────┤
│ Iterations: 15 of 15                                           │
│ Duration: 8m 12s                                               │
│ Last Error: TypeError at line 67                               │
╰────────────────────────────────────────────────────────────────╯

The agent couldn't complete the task. Last known issue:
  TypeError: unsupported operand type(s) for +: 'int' and 'str'
  File: main.py, Line: 67

Suggestions:
  • Task may be too complex. Try breaking it down further.
  • Review generated code in /home/user/workspace_abc123/
  • Resume with more iterations: python -m src.main resume abc123

Would you like to view the workspace? (Y/n)
```

### 8.4 Resuming a Task

**Command**:
```bash
python -m src.main resume abc123
```

**Behavior**:
- Loads checkpoint from database
- Restores context (code files, feedback, etc.)
- Continues from last state
- Gets 15 more iterations

**Use Cases**:
- User paused with Ctrl+C
- Max iterations reached but progress was made
- System crashed (checkpoint saved)

---

## 9. Edge Cases and Limitations

### 9.1 Known Limitations

**1. Single-file focus**
- **Issue**: Agent tends to put all code in one file (e.g., main.py)
- **Workaround**: Explicitly mention in task: "Use separate modules for X, Y, Z"

**2. Test generation quality**
- **Issue**: Tests may not cover all edge cases
- **Workaround**: Agent iterates and improves tests if they're insufficient

**3. Dependency management**
- **Issue**: Agent can't auto-install packages (requires user approval)
- **Workaround**: Approve dependencies when prompted, or pre-install

**4. Non-determinism**
- **Issue**: LLM may generate slightly different code each time
- **Workaround**: Set temperature to 0.0 for maximum determinism (but less creative)

**5. Complex refactoring**
- **Issue**: Agent struggles with large-scale refactoring (>5 files)
- **Workaround**: Break task into smaller refactoring steps

### 9.2 Edge Case Handling

**Edge Case 1: Empty workspace (first iteration)**

**Behavior**:
- CoderAgent calls `list_files()` → returns []
- CoderAgent creates all files from scratch
- No issues

**Edge Case 2: Workspace has existing files (user modified code)**

**Behavior**:
- CoderAgent calls `list_files()` → returns user files
- CoderAgent calls `read_file()` to see changes
- CoderAgent respects user changes (doesn't overwrite without reason)

**Edge Case 3: Tests pass immediately (iteration 1)**

**Behavior**:
- TESTING state: All tests pass
- Transition to SUCCESS (no reflection needed)
- Total iterations: 1 (optimal!)

**Edge Case 4: Tests never pass (all 15 iterations fail)**

**Behavior**:
- REFLECTING state (iteration 15): Identifies issue
- Orchestrator: iteration >= max_iterations
- Transition to FAILED
- User can resume for 15 more iterations

**Edge Case 5: Circular logic error (same error every iteration)**

**Detection**:
```python
# Track error history
error_history = context.get("error_history", [])
current_error = extract_error_signature(test_results)

if error_history.count(current_error) >= 3:
    logger.warning("Same error repeated 3 times, agent may be stuck")
    # Possible actions:
    # - Try fallback model (GPT-3.5 instead of GPT-4)
    # - Simplify task (ask user to break down)
    # - Skip to FAILED state early
```

**Edge Case 6: User denies required approval (e.g., network access)**

**Behavior**:
- Agent blocked from using network
- Reflection: "User denied network access"
- Agent must find alternative (e.g., mock data instead of API calls)
- If no alternative exists, task may fail

---

## 10. Observability

### 10.1 Logging

**Log Levels**:
- **DEBUG**: Detailed internals (AST parsing, DB queries)
- **INFO**: Major events (state transitions, LLM calls)
- **WARNING**: Potential issues (nearing max iterations, slow queries)
- **ERROR**: Failures (LLM errors, execution failures)

**Log Format** (structured JSON):
```json
{
  "timestamp": "2026-01-16T10:30:15.123Z",
  "level": "INFO",
  "event": "state_transition",
  "task_id": "abc123",
  "iteration": 3,
  "from_state": "CODING",
  "to_state": "TESTING",
  "duration_seconds": 12.5,
  "tokens_used": 1234
}
```

**Log Locations**:
- **Console**: Colored, human-readable (via Rich)
- **File**: JSON format in `logs/autonomous_agent.log`
- **Database**: Key events in `iterations` table

### 10.2 Metrics

**Collected Metrics**:

| Metric | Unit | Purpose |
|--------|------|---------|
| Iterations to success | Count | Track agent efficiency |
| Duration per iteration | Seconds | Identify slow operations |
| Tokens per iteration | Count | Track LLM usage/cost |
| Pass rate per iteration | % | Measure test quality |
| Memory hit rate | % | Measure learning effectiveness |
| Approval prompts per task | Count | Measure safety overhead |

**Storage**: `metrics` table in database

**Querying**:
```sql
-- Average iterations to success by language
SELECT
    language,
    AVG(current_iteration) AS avg_iterations,
    STDDEV(current_iteration) AS stddev_iterations
FROM tasks
WHERE status = 'success'
GROUP BY language;

-- Cost per task
SELECT
    task_id,
    SUM(metric_value) AS total_tokens,
    SUM(metric_value) * 0.00001 AS estimated_cost_usd
FROM metrics
WHERE metric_name = 'tokens_used'
GROUP BY task_id;
```

### 10.3 Debugging

**Debugging Tools**:

1. **Task ID**: Every task has a unique UUID for tracking
2. **Workspace inspection**: Generated code is saved, can be inspected manually
3. **Logs**: Detailed JSON logs in `logs/` directory
4. **Database queries**: Full audit trail in `iterations` table
5. **Checkpoint files**: State snapshots for post-mortem analysis

**Common Debugging Workflows**:

**Issue**: "Why did the task fail?"
```bash
# 1. Find task ID
python -m src.main history | grep "failed"

# 2. View logs
cat logs/autonomous_agent.log | jq 'select(.task_id == "abc123")'

# 3. Query database
psql -c "SELECT * FROM iterations WHERE task_id = 'abc123' ORDER BY iteration_num;"

# 4. Inspect workspace
cd workspace_abc123/
cat main.py  # See what was generated
```

**Issue**: "Why is the agent stuck in a loop?"
```bash
# Check error history
psql -c "SELECT iteration_num, state, error_messages FROM iterations WHERE task_id = 'abc123';"

# Look for repeating patterns
# If same error 3+ times → agent is stuck
```

---

**Last Updated**: 2026-01-16
**Maintained By**: System Engineers
**Related Documents**: `AGENT-PLANNING.md`, `AGENT-EXECUTION.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`
