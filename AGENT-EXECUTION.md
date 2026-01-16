# AGENT-EXECUTION.md

> **Purpose**: This document is for AI execution/worker agents implementing features, fixing bugs, and executing tactical tasks for the Autonomous Coding Agent project.

---

## 🎯 Quick Context

**Project**: Miracle - Autonomous Coding Agent
**Your Role**: Implementation, bug fixes, testing, refactoring
**Working Language**: Python 3.11+
**Main Entry Point**: `/home/user/Miracle/autonomous_agent/src/main.py`
**Test Framework**: pytest + hypothesis
**Code Style**: PEP 8, type hints required

---

## 🚀 Getting Started (First Time Setup)

### 1. Environment Setup

```bash
# Navigate to project
cd /home/user/Miracle/autonomous_agent

# Create virtual environment (recommended)
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add:
#   OPENAI_API_KEY=your_key_here
#   DB_PASSWORD=your_password_here
```

### 2. Database Setup

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Initialize schema
python scripts/setup_db.py

# Verify connection
python -c "from src.memory.db_manager import DatabaseManager; print('DB OK')"
```

### 3. Run Tests

```bash
# Run existing tests
pytest tests/ -v

# Check test coverage
pytest tests/ --cov=src --cov-report=html
```

### 4. Test the System

```bash
# Interactive mode
python -m src.main run

# Direct task (for testing)
python -m src.main run --task "Write a function to calculate fibonacci" --language python
```

---

## 📂 Project Structure

```
autonomous_agent/
├── src/
│   ├── main.py                  # CLI entry point ⭐ START HERE
│   ├── orchestrator.py          # State machine controller
│   ├── config_loader.py         # Configuration management
│   │
│   ├── agents/                  # AI agents (implement BaseAgent)
│   │   ├── base_agent.py        # Abstract base class
│   │   ├── planner.py           # Task planning
│   │   ├── coder.py             # Code generation
│   │   ├── tester.py            # Test generation + execution
│   │   └── reflector.py         # Error analysis
│   │
│   ├── llm/                     # LLM interface
│   │   ├── openai_client.py     # OpenAI API wrapper
│   │   ├── tools.py             # Function calling definitions
│   │   ├── prompts.py           # Prompt templates
│   │   └── token_counter.py     # Token usage tracking
│   │
│   ├── memory/                  # Learning system
│   │   ├── db_manager.py        # PostgreSQL operations
│   │   ├── vector_store.py      # Embedding + similarity search
│   │   ├── pattern_matcher.py   # Pattern retrieval
│   │   └── failure_analyzer.py  # Error pattern analysis
│   │
│   ├── sandbox/                 # Code execution safety
│   │   ├── docker_executor.py   # Docker container management
│   │   ├── safety_checker.py    # AST + Bandit scanning
│   │   ├── resource_limits.py   # CPU/RAM/time limits
│   │   └── sandbox_manager.py   # Execution coordinator
│   │
│   ├── testing/                 # Test management
│   │   ├── test_generator.py    # pytest generation
│   │   ├── test_runner.py       # Test execution
│   │   └── coverage_analyzer.py # Coverage checking
│   │
│   ├── projects/                # Project scaffolding
│   │   └── scaffolder.py        # Language-specific setup
│   │
│   ├── ui/                      # User interface
│   │   ├── cli.py               # Rich terminal UI
│   │   ├── logger.py            # Structured logging
│   │   ├── progress.py          # Progress bars
│   │   └── approval_prompt.py   # Interactive prompts
│   │
│   └── utils/                   # Utilities
│       ├── circuit_breaker.py   # Loop prevention
│       ├── state_saver.py       # Checkpoint/resume
│       └── metrics_collector.py # Performance tracking
│
├── config/                      # YAML configuration ⚙️
├── scripts/                     # Database setup scripts
├── tests/                       # Unit tests 🧪
├── sandbox/workspace/           # Code execution area
└── logs/                        # Structured logs
```

---

## 🛠️ Common Implementation Tasks

### Task 1: Adding a New Tool for Coder Agent

**Example**: Add `delete_file` tool

1. **Define the tool** (`src/llm/tools.py`):

```python
DELETE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file from the workspace",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to file to delete (relative to workspace)"
                }
            },
            "required": ["path"]
        }
    }
}

# Add to CODER_TOOLS list
CODER_TOOLS = [
    CREATE_FILE_TOOL,
    READ_FILE_TOOL,
    LIST_FILES_TOOL,
    DELETE_FILE_TOOL  # NEW
]
```

2. **Implement the handler** (`src/agents/coder.py`):

```python
def _handle_tool_call(self, tool_call: dict, workspace: Path) -> dict:
    tool_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if tool_name == "delete_file":
        return self._delete_file(args["path"], workspace)
    # ... existing handlers

def _delete_file(self, path: str, workspace: Path) -> dict:
    """Delete a file from the workspace"""
    file_path = workspace / path

    # Safety check: must be within workspace
    if not file_path.resolve().is_relative_to(workspace.resolve()):
        return {"error": "Path must be within workspace"}

    if not file_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        file_path.unlink()
        return {"success": True, "message": f"Deleted {path}"}
    except Exception as e:
        return {"error": str(e)}
```

3. **Add tests** (`tests/agents/test_coder.py`):

```python
def test_delete_file_tool(tmp_path):
    """Test that delete_file removes files correctly"""
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    coder = CoderAgent(mock_llm_client, config)
    result = coder._delete_file("test.py", tmp_path)

    assert result["success"] is True
    assert not test_file.exists()

def test_delete_file_outside_workspace(tmp_path):
    """Test that delete_file blocks access outside workspace"""
    coder = CoderAgent(mock_llm_client, config)
    result = coder._delete_file("../../etc/passwd", tmp_path)

    assert "error" in result
    assert "workspace" in result["error"].lower()
```

4. **Update documentation**:
   - Add to `FUNCTIONALITY.md` under "Tool Use Pattern"
   - Update `ARCHITECTURE.md` with tool diagram

---

### Task 2: Adding a New Safety Rule

**Example**: Block `socket` module usage

1. **Add to AST scanner** (`src/sandbox/safety_checker.py`):

```python
class SafetyChecker:
    DANGEROUS_IMPORTS = [
        "os",
        "subprocess",
        "pty",
        "socket",     # NEW: Block socket usage
        "__builtin__",
        "__import__",
    ]

    def check_imports(self, tree: ast.AST) -> list[str]:
        """Scan AST for dangerous imports"""
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_IMPORTS:
                        violations.append(
                            f"Blocked import: {alias.name} at line {node.lineno}"
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module in self.DANGEROUS_IMPORTS:
                    violations.append(
                        f"Blocked import from: {node.module} at line {node.lineno}"
                    )

        return violations
```

2. **Add to config** (`config/safety_rules.yaml`):

```yaml
blocked_imports:
  - os
  - subprocess
  - pty
  - socket         # NEW
  - __builtin__
  - __import__

blocked_functions:
  - eval
  - exec
  - compile
  - socket.socket  # NEW: Block socket creation

approval_required:
  - requests       # Network access requires approval
  - urllib
  - httpx
```

3. **Add tests** (`tests/sandbox/test_safety_checker.py`):

```python
def test_blocks_socket_import():
    """Test that socket imports are blocked"""
    code = """
import socket
s = socket.socket()
"""
    checker = SafetyChecker()
    tree = ast.parse(code)
    violations = checker.check_imports(tree)

    assert len(violations) > 0
    assert "socket" in violations[0]

def test_allows_safe_imports():
    """Test that safe imports pass"""
    code = """
import json
import math
from typing import List
"""
    checker = SafetyChecker()
    tree = ast.parse(code)
    violations = checker.check_imports(tree)

    assert len(violations) == 0
```

---

### Task 3: Adding a New State to Orchestrator

**Example**: Add `VALIDATING` state for syntax checking

1. **Add to enum** (`src/orchestrator.py`):

```python
class OrchestrationState(Enum):
    INIT = "init"
    PLANNING = "planning"
    CODING = "coding"
    VALIDATING = "validating"  # NEW: Syntax check before testing
    TESTING = "testing"
    REFLECTING = "reflecting"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"
```

2. **Implement state handler**:

```python
async def _run_validating_state(self) -> OrchestrationState:
    """Validate generated code for syntax errors"""
    self.logger.info("Validating code syntax...")

    code_files = self.context.get("code_files", [])
    validation_errors = []

    for file_path in code_files:
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            # Python syntax check
            if file_path.endswith('.py'):
                compile(code, file_path, 'exec')

            # Node.js syntax check
            elif file_path.endswith('.js'):
                result = subprocess.run(
                    ['node', '--check', file_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    validation_errors.append(result.stderr)

        except SyntaxError as e:
            validation_errors.append(f"{file_path}: {str(e)}")

    # Store results in context
    self.context["validation_errors"] = validation_errors

    # Transition logic
    if validation_errors:
        self.logger.warning(f"Found {len(validation_errors)} validation errors")
        return OrchestrationState.REFLECTING  # Skip testing, go back to fix
    else:
        self.logger.info("Code validation passed")
        return OrchestrationState.TESTING  # Proceed to testing
```

3. **Update state transition map**:

```python
async def run(self) -> dict:
    """Main orchestration loop"""
    state_handlers = {
        OrchestrationState.INIT: self._run_init_state,
        OrchestrationState.PLANNING: self._run_planning_state,
        OrchestrationState.CODING: self._run_coding_state,
        OrchestrationState.VALIDATING: self._run_validating_state,  # NEW
        OrchestrationState.TESTING: self._run_testing_state,
        OrchestrationState.REFLECTING: self._run_reflecting_state,
    }

    # ... loop logic
```

4. **Update transitions**:

```python
async def _run_coding_state(self) -> OrchestrationState:
    # ... generate code ...

    # OLD: return OrchestrationState.TESTING
    # NEW: return OrchestrationState.VALIDATING
    return OrchestrationState.VALIDATING
```

5. **Add tests**:

```python
def test_validating_state_with_syntax_error():
    """Test that VALIDATING catches syntax errors"""
    orchestrator = Orchestrator(config)
    orchestrator.context = {
        "code_files": ["test_invalid.py"]
    }

    # Create invalid Python file
    with open("test_invalid.py", 'w') as f:
        f.write("def foo(\n")  # Missing closing parenthesis

    next_state = await orchestrator._run_validating_state()

    assert next_state == OrchestrationState.REFLECTING
    assert len(orchestrator.context["validation_errors"]) > 0
```

---

### Task 4: Implementing a Bug Fix

**Example**: Fix reflector agent not retrieving similar failures

**Steps**:

1. **Reproduce the bug**:
```bash
# Run a task that should trigger memory retrieval
python -m src.main run --task "Parse JSON with error handling"

# Check logs
tail -f logs/autonomous_agent.log | grep "vector_search"
# Observe: No similar failures retrieved
```

2. **Identify the root cause** (`src/memory/vector_store.py`):
```python
# Bug: Similarity threshold too high (0.9)
async def search_similar_failures(self, error_message: str, limit: int = 5):
    embedding = await self._generate_embedding(error_message)

    query = """
        SELECT id, error_message, solution, similarity
        FROM (
            SELECT id, error_message, solution,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM failures
        ) AS subquery
        WHERE similarity > 0.9  -- BUG: Too strict!
        ORDER BY similarity DESC
        LIMIT %s
    """
```

3. **Fix the bug**:
```python
# Fix: Lower threshold to 0.6 (configurable)
async def search_similar_failures(
    self,
    error_message: str,
    limit: int = 5,
    threshold: float = 0.6  # NEW: Configurable threshold
):
    embedding = await self._generate_embedding(error_message)

    query = """
        SELECT id, error_message, solution, similarity
        FROM (
            SELECT id, error_message, solution,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM failures
        ) AS subquery
        WHERE similarity > %s  -- Use parameter
        ORDER BY similarity DESC
        LIMIT %s
    """

    async with self.db_manager.get_connection() as conn:
        cursor = await conn.execute(query, (embedding, threshold, limit))
        return await cursor.fetchall()
```

4. **Add configuration** (`config/settings.yaml`):
```yaml
memory:
  similarity_threshold: 0.6  # Default threshold
  max_similar_failures: 5
```

5. **Write regression test** (`tests/memory/test_vector_store.py`):
```python
@pytest.mark.asyncio
async def test_search_similar_failures_with_threshold():
    """Test that similarity search respects threshold parameter"""
    vector_store = VectorStore(db_manager)

    # Insert test failure
    await vector_store.store_failure(
        error_message="KeyError: 'name'",
        solution="Check if key exists before access"
    )

    # Search with high threshold (should find nothing)
    results_high = await vector_store.search_similar_failures(
        "KeyError: 'age'",
        threshold=0.95
    )
    assert len(results_high) == 0

    # Search with low threshold (should find similar error)
    results_low = await vector_store.search_similar_failures(
        "KeyError: 'age'",
        threshold=0.6
    )
    assert len(results_low) > 0
    assert "KeyError" in results_low[0].error_message
```

6. **Verify the fix**:
```bash
# Run the same task again
python -m src.main run --task "Parse JSON with error handling"

# Check logs
tail -f logs/autonomous_agent.log | grep "vector_search"
# Observe: Similar failures now retrieved
```

7. **Update documentation**:
   - Add to changelog or release notes
   - Update `FUNCTIONALITY.md` if behavior changed

---

### Task 5: Refactoring Without Breaking Changes

**Example**: Refactor `CoderAgent` to use async/await

**Steps**:

1. **Identify target** (`src/agents/coder.py`):
```python
# Before: Synchronous file operations
def execute(self, context: dict) -> dict:
    code = self._generate_code(context)
    self._write_files(code)  # Blocking I/O
    return {"code_files": self.files_created}
```

2. **Plan the refactor**:
   - Change `execute` to async
   - Use `aiofiles` for async file operations
   - Update all callers in orchestrator

3. **Install dependency**:
```bash
pip install aiofiles
# Add to requirements.txt: aiofiles==23.2.1
```

4. **Refactor the code**:
```python
# After: Asynchronous file operations
import aiofiles

async def execute(self, context: dict) -> dict:
    code = await self._generate_code_async(context)
    await self._write_files_async(code)  # Non-blocking I/O
    return {"code_files": self.files_created}

async def _write_files_async(self, code: dict):
    """Write files asynchronously"""
    for file_path, content in code.items():
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(content)
        self.files_created.append(file_path)
```

5. **Update callers** (`src/orchestrator.py`):
```python
# Before
def _run_coding_state(self):
    coder = CoderAgent(self.llm_client, self.config)
    result = coder.execute(self.context)  # Sync

# After
async def _run_coding_state(self):
    coder = CoderAgent(self.llm_client, self.config)
    result = await coder.execute(self.context)  # Async
```

6. **Run ALL tests**:
```bash
pytest tests/ -v
# Ensure no tests break from async changes
```

7. **Update base class** (`src/agents/base_agent.py`):
```python
class BaseAgent(ABC):
    @abstractmethod
    async def execute(self, context: dict) -> dict:  # Changed to async
        """Execute agent logic and return results"""
        pass
```

8. **Update documentation**:
   - Note in `ARCHITECTURE.md` that agents are now async
   - Update code examples in `FUNCTIONALITY.md`

---

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/agents/test_coder.py -v

# Run tests matching pattern
pytest tests/ -k "test_coder" -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run in parallel (faster)
pytest tests/ -n auto
```

### Writing Tests

**Structure**:
```
tests/
├── agents/
│   ├── test_planner.py
│   ├── test_coder.py
│   ├── test_tester.py
│   └── test_reflector.py
├── memory/
│   ├── test_db_manager.py
│   └── test_vector_store.py
├── sandbox/
│   ├── test_safety_checker.py
│   └── test_docker_executor.py
└── conftest.py  # Shared fixtures
```

**Test Template**:
```python
import pytest
from src.agents.coder import CoderAgent
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = Mock()
    client.chat_completion = AsyncMock(return_value={
        "choices": [{"message": {"content": "mocked response"}}]
    })
    return client

@pytest.fixture
def config():
    """Mock configuration"""
    return {
        "max_tokens": 4096,
        "temperature": 0.2
    }

@pytest.mark.asyncio
async def test_coder_generates_valid_python(mock_llm_client, config, tmp_path):
    """Test that CoderAgent generates syntactically valid Python"""
    coder = CoderAgent(mock_llm_client, config)
    context = {
        "task": "Write a function to add two numbers",
        "workspace": tmp_path
    }

    result = await coder.execute(context)

    # Check that files were created
    assert len(result["code_files"]) > 0

    # Check syntax validity
    for file_path in result["code_files"]:
        with open(file_path, 'r') as f:
            code = f.read()
        compile(code, file_path, 'exec')  # Should not raise SyntaxError
```

**Key Testing Principles**:
1. **Mock external dependencies** (LLM, database, Docker)
2. **Use `tmp_path` fixture** for file operations
3. **Test edge cases** (empty input, invalid input, errors)
4. **Test async functions** with `@pytest.mark.asyncio`
5. **Use property-based testing** for complex logic (hypothesis)

---

## 📝 Code Style Guidelines

### Python Style (PEP 8)

```python
# Good: Type hints, docstrings, clear names
async def generate_code(
    self,
    task_description: str,
    context: dict[str, Any]
) -> dict[str, str]:
    """
    Generate code based on task description.

    Args:
        task_description: The task to implement
        context: Additional context (past failures, patterns, etc.)

    Returns:
        Dictionary mapping file paths to code content

    Raises:
        CodeGenerationError: If code generation fails
    """
    prompt = self._build_prompt(task_description, context)
    response = await self.llm_client.chat_completion(messages=prompt)

    return self._parse_code_from_response(response)
```

**Key Rules**:
- **Type hints**: Required for all function parameters and returns
- **Docstrings**: Google-style docstrings for all public functions
- **Line length**: Max 100 characters (not strict 79)
- **Imports**: Grouped (stdlib, third-party, local) and sorted
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Logging

```python
# Use structured logging (structlog)
self.logger.info(
    "Code generation completed",
    task_id=self.task_id,
    files_created=len(result["code_files"]),
    duration_seconds=duration
)

# Log errors with context
self.logger.error(
    "Code generation failed",
    task_id=self.task_id,
    error=str(e),
    exc_info=True  # Include stack trace
)
```

### Error Handling

```python
# Good: Specific exceptions with context
class CodeGenerationError(Exception):
    """Raised when code generation fails"""
    def __init__(self, message: str, context: dict):
        super().__init__(message)
        self.context = context

try:
    code = await self._generate_code(task)
except OpenAIError as e:
    raise CodeGenerationError(
        "LLM API call failed",
        context={"task": task, "error": str(e)}
    ) from e
```

---

## 🔍 Debugging Tips

### 1. Check Logs

```bash
# Tail logs in real-time
tail -f logs/autonomous_agent.log

# Filter by component
tail -f logs/autonomous_agent.log | grep "orchestrator"

# Filter by task
tail -f logs/autonomous_agent.log | grep "task_id=abc123"
```

### 2. Enable Debug Mode

```yaml
# config/settings.yaml
logging:
  level: DEBUG  # Change from INFO to DEBUG
  include_llm_calls: true  # Log all LLM requests/responses
```

### 3. Inspect Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d autonomous_agent

# Check task status
SELECT id, description, status, current_iteration, max_iterations
FROM tasks
ORDER BY created_at DESC
LIMIT 10;

# Check recent failures
SELECT task_id, error_message, created_at
FROM failures
ORDER BY created_at DESC
LIMIT 5;

# Check iteration history
SELECT iteration_num, state, tests_passed, tests_failed
FROM iterations
WHERE task_id = 'your-task-id'
ORDER BY iteration_num;
```

### 4. Use IPython for REPL Debugging

```python
# Add to any file for debugging
import IPython; IPython.embed()

# Example: Debug CoderAgent
from src.agents.coder import CoderAgent
from src.llm.openai_client import OpenAIClient

client = OpenAIClient(api_key="...")
coder = CoderAgent(client, config)

# Manually test methods
context = {"task": "Write a hello world function"}
result = await coder.execute(context)
print(result)
```

### 5. Test Individual Components

```bash
# Test just the safety checker
python -c "
from src.sandbox.safety_checker import SafetyChecker
import ast

code = 'import os; os.system(\"ls\")'
tree = ast.parse(code)
checker = SafetyChecker()
print(checker.check_imports(tree))
"

# Test vector search
python -c "
from src.memory.vector_store import VectorStore
import asyncio

async def test():
    vs = VectorStore(db_manager)
    results = await vs.search_similar_failures('KeyError')
    print(results)

asyncio.run(test())
"
```

---

## 🚨 Common Pitfalls

### 1. Forgetting to await async functions

```python
# ❌ Bad: Missing await
result = coder.execute(context)  # Returns coroutine, not result

# ✅ Good: Properly awaited
result = await coder.execute(context)
```

### 2. Modifying state directly

```python
# ❌ Bad: Mutating shared state
self.context["iteration"] += 1  # Race condition risk

# ✅ Good: Use orchestrator methods
self.increment_iteration()
```

### 3. Hardcoding configuration

```python
# ❌ Bad: Hardcoded values
max_iterations = 15

# ✅ Good: Use config
max_iterations = self.config.orchestrator.max_iterations
```

### 4. Not handling LLM failures

```python
# ❌ Bad: Assuming LLM always succeeds
response = await self.llm_client.chat_completion(messages)
code = response.choices[0].message.content

# ✅ Good: Handle rate limits, errors
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _call_llm_with_retry(self, messages):
    try:
        response = await self.llm_client.chat_completion(messages)
        return response.choices[0].message.content
    except OpenAIError as e:
        self.logger.warning(f"LLM call failed: {e}")
        raise
```

### 5. Forgetting to close database connections

```python
# ❌ Bad: Manual connection management
conn = await self.db_manager.get_connection()
await conn.execute(query)
# Forgot to close!

# ✅ Good: Use context manager
async with self.db_manager.get_connection() as conn:
    await conn.execute(query)
# Automatically closed
```

---

## 🔐 Security Checklist

When implementing features that execute code:

- [ ] **AST scanning** for dangerous operations (eval, exec, __import__)
- [ ] **Bandit scanning** for security vulnerabilities
- [ ] **User approval** for network access and subprocess calls
- [ ] **Docker sandboxing** with resource limits
- [ ] **Path validation** (prevent directory traversal attacks)
- [ ] **Input sanitization** (especially for file paths and commands)
- [ ] **Secrets handling** (never log API keys or passwords)
- [ ] **Allowlist approach** for dependencies (not denylist)

---

## 📋 Pre-Commit Checklist

Before committing code:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code is formatted: `black src/ tests/`
- [ ] Imports are sorted: `isort src/ tests/`
- [ ] Type hints are correct: `mypy src/`
- [ ] No linting errors: `flake8 src/ tests/`
- [ ] Docstrings are complete (all public functions)
- [ ] Configuration is updated if needed
- [ ] Tests are added for new features
- [ ] Logs are at appropriate levels (not too verbose)
- [ ] No debug print statements or IPython embeds
- [ ] Database migrations are included if schema changed

---

## 🤝 Collaborating with Planning Agents

### Receiving a Plan

When a planning agent provides an implementation plan:

1. **Read the full plan** before starting
2. **Clarify ambiguities** by asking questions
3. **Report blockers early** (missing dependencies, unclear requirements)
4. **Follow the architecture** (don't deviate without discussing)
5. **Document deviations** if necessary (with rationale)

### Reporting Progress

Update the planning agent on:

- **Completion status** of each task
- **Unexpected challenges** encountered
- **Technical decisions** made during implementation
- **New edge cases** discovered
- **Performance observations** (if relevant)

### Handoff Format

```markdown
## Implementation Status: [Feature Name]

### Completed
- ✅ Task 1: Description (commit: abc123)
- ✅ Task 2: Description (commit: def456)

### In Progress
- 🔄 Task 3: Description (80% complete)
  - Blocker: Need clarification on error handling strategy

### Not Started
- ⏳ Task 4: Description
- ⏳ Task 5: Description

### Deviations from Plan
- Changed approach for Task 2 because [rationale]

### Questions for Planning Agent
1. Should we handle edge case X?
2. Performance concern: Y is slow, optimize now or later?
```

---

## 📚 Key Files to Understand

Must-read files for execution agents:

1. **`src/orchestrator.py`** - State machine logic (450 lines)
2. **`src/agents/base_agent.py`** - Agent interface
3. **`src/llm/tools.py`** - Available tools for agents
4. **`config/settings.yaml`** - System configuration
5. **`scripts/init_db.sql`** - Database schema (202 lines)

Reference documentation:

- **`ARCHITECTURE.md`** - Deep technical architecture
- **`FUNCTIONALITY.md`** - System behavior and flows
- **`DEPENDENCIES.md`** - Setup and dependency management
- **`autonomous_coding_agent_handoff.md`** - Comprehensive specification (1,516 lines)

---

## ✅ Execution Agent Success Criteria

An execution agent has succeeded when:

1. ✅ All tests pass (unit + integration)
2. ✅ Code follows style guidelines (PEP 8, type hints, docstrings)
3. ✅ No regressions (existing functionality still works)
4. ✅ Performance is acceptable (no major slowdowns)
5. ✅ Security is maintained (no new vulnerabilities)
6. ✅ Documentation is updated (if behavior changed)
7. ✅ Configuration is backward compatible (or migration provided)
8. ✅ Logs are informative (can debug issues from logs)
9. ✅ Error handling is robust (no unhandled exceptions)

---

**Last Updated**: 2026-01-16
**Maintained By**: AI Execution Agents
**Related Documents**: `AGENT-PLANNING.md`, `ARCHITECTURE.md`, `FUNCTIONALITY.md`, `DEPENDENCIES.md`
