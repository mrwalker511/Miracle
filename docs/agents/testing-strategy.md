# Testing Strategy

Testing approach for the Miracle autonomous coding agent system.

---

## Testing Philosophy

**Goal**: Ensure the system reliably generates working code while maintaining safety and correctness.

**Challenges**:
- Non-deterministic LLM outputs
- Complex state machine interactions
- Expensive API calls
- Docker container management (optional)

---

## Test Structure

```
tests/
├── unit/                           # Fast, isolated tests
│   ├── agents/
│   │   ├── test_planner.py
│   │   ├── test_coder.py
│   │   ├── test_tester.py
│   │   └── test_reflector.py
│   ├── llm/
│   │   ├── test_openai_client.py
│   │   └── test_tools.py
│   ├── memory/
│   │   ├── test_pattern_matcher.py
│   │   └── test_failure_analyzer.py
│   ├── sandbox/
│   │   ├── test_safety_checker.py
│   │   └── test_docker_executor.py
│   └── test_orchestrator.py
├── integration/                    # Multi-component tests
│   ├── test_full_loop.py          # CODING → TESTING → REFLECTING
│   ├── test_memory_retrieval.py
│   └── test_approval_flow.py
└── e2e/                            # End-to-end scenarios
    ├── test_simple_task.py        # "Write a function to add"
    ├── test_api_task.py           # "Build a REST API"
    └── test_failure_recovery.py   # Test iteration loop
```

---

## Unit Testing

### Mocking LLM Calls

Always mock LLM calls in unit tests (expensive, non-deterministic).

**File**: `tests/conftest.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    
    # Mock chat completion
    client.chat_completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="Generated response",
                    tool_calls=[]
                )
            )
        ]
    )
    
    # Mock embedding
    client.create_embedding.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    
    return client
```

### Testing Agents

**Example**: Test Coder agent file creation

```python
# tests/unit/agents/test_coder.py
import pytest
from pathlib import Path
from src.agents.coder import CoderAgent

@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace

@pytest.mark.asyncio
async def test_coder_creates_file(mock_llm_client, tmp_workspace):
    """Test that Coder agent can create a file."""
    # Setup
    config = MagicMock(
        openai=MagicMock(models=MagicMock(coder="gpt-4"))
    )
    coder = CoderAgent(mock_llm_client, config)
    
    # Mock LLM response with tool call
    mock_llm_client.chat_completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    tool_calls=[
                        MagicMock(
                            function=MagicMock(
                                name="create_file",
                                arguments='{"path": "app.py", "content": "print(\\"hello\\")"}'
                            )
                        )
                    ]
                )
            )
        ]
    )
    
    context = {
        "plan": {"subtasks": ["Create app.py"]},
        "workspace": tmp_workspace
    }
    
    # Execute
    result = await coder.execute(context)
    
    # Assert
    assert "files_created" in result
    assert "app.py" in result["files_created"]
    assert (tmp_workspace / "app.py").exists()
    assert (tmp_workspace / "app.py").read_text() == 'print("hello")'
```

### Testing State Machine

**Example**: Test orchestrator state transitions

```python
# tests/unit/test_orchestrator.py
import pytest
from src.orchestrator import Orchestrator, OrchestrationState

@pytest.mark.asyncio
async def test_orchestrator_planning_to_coding():
    """Test transition from PLANNING to CODING state."""
    # Setup
    orchestrator = Orchestrator(
        llm_client=mock_llm_client,
        db_manager=mock_db,
        config=mock_config
    )
    orchestrator.state = OrchestrationState.PLANNING
    
    # Mock planner result
    mock_planner = AsyncMock()
    mock_planner.execute.return_value = {
        "plan": {"subtasks": ["Task 1", "Task 2"]}
    }
    orchestrator.planner = mock_planner
    
    # Execute
    next_state = await orchestrator._run_planning_state()
    
    # Assert
    assert next_state == OrchestrationState.CODING
    assert "plan" in orchestrator.context

@pytest.mark.asyncio
async def test_orchestrator_circuit_breaker():
    """Test circuit breaker stops at max iterations."""
    orchestrator = Orchestrator(...)
    orchestrator.iteration = 15
    orchestrator.config.orchestrator.max_iterations = 15
    
    # Execute
    result = await orchestrator.run()
    
    # Assert
    assert result["status"] == "FAILED"
    assert "max iterations" in result["reason"].lower()
```

### Testing Safety Checker

Use property-based testing with Hypothesis.

```python
# tests/unit/sandbox/test_safety_checker.py
import pytest
from hypothesis import given, strategies as st
from src.sandbox.safety_checker import SafetyChecker

def test_blocks_eval():
    """Test that eval() is blocked."""
    code = """
x = eval("1 + 1")
"""
    checker = SafetyChecker()
    violations = checker.check_code(code)
    
    assert len(violations) > 0
    assert any("eval" in v for v in violations)

def test_blocks_dangerous_imports():
    """Test that dangerous imports are blocked."""
    code = """
import os
import subprocess

os.system("ls")
"""
    checker = SafetyChecker()
    violations = checker.check_code(code)
    
    assert len(violations) >= 2
    assert any("os" in v for v in violations)
    assert any("subprocess" in v for v in violations)

@given(st.text())
def test_safety_checker_does_not_crash(code):
    """Property test: safety checker should never crash, even on random input."""
    checker = SafetyChecker()
    
    # Should not raise exception
    try:
        violations = checker.check_code(code)
        assert isinstance(violations, list)
    except SyntaxError:
        # Syntax errors are acceptable
        pass
```

---

## Integration Testing

Test multiple components working together.

### Testing Full Loop

```python
# tests/integration/test_full_loop.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_coding_testing_reflecting_loop(
    mock_llm_client,
    mock_db,
    tmp_workspace
):
    """Test CODING → TESTING → REFLECTING loop."""
    # Setup orchestrator with all real components
    orchestrator = Orchestrator(
        llm_client=mock_llm_client,
        db_manager=mock_db,
        config=test_config
    )
    
    # Mock LLM responses
    mock_llm_client.chat_completion.side_effect = [
        # Coder: generates code with bug
        MagicMock(choices=[MagicMock(message=MagicMock(
            tool_calls=[MagicMock(function=MagicMock(
                name="create_file",
                arguments='{"path": "app.py", "content": "def add(a, b):\\n    return a - b"}'
            ))]
        ))]),
        
        # Tester: generates test
        MagicMock(choices=[MagicMock(message=MagicMock(
            tool_calls=[MagicMock(function=MagicMock(
                name="create_test_file",
                arguments='{"path": "test_app.py", "content": "def test_add():\\n    assert add(1, 2) == 3"}'
            ))]
        ))]),
        
        # Reflector: analyzes failure
        MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"hypothesis": "Change - to + in add function"}'
        ))]),
        
        # Coder: fixes bug
        MagicMock(choices=[MagicMock(message=MagicMock(
            tool_calls=[MagicMock(function=MagicMock(
                name="create_file",
                arguments='{"path": "app.py", "content": "def add(a, b):\\n    return a + b"}'
            ))]
        ))])
    ]
    
    # Execute
    orchestrator.state = OrchestrationState.CODING
    
    # First iteration: CODING → TESTING (fails) → REFLECTING
    state = await orchestrator._run_coding_state()
    assert state == OrchestrationState.TESTING
    
    state = await orchestrator._run_testing_state()
    assert state == OrchestrationState.REFLECTING
    
    state = await orchestrator._run_reflecting_state()
    assert state == OrchestrationState.CODING
    
    # Second iteration: CODING → TESTING (passes) → SUCCESS
    state = await orchestrator._run_coding_state()
    assert state == OrchestrationState.TESTING
    
    state = await orchestrator._run_testing_state()
    assert state == OrchestrationState.SUCCESS
```

### Testing Memory Retrieval

```python
# tests/integration/test_memory_retrieval.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_pattern_retrieval_improves_planning(
    real_vector_store,
    real_db
):
    """Test that stored patterns are retrieved during planning."""
    # Setup: Store a successful pattern
    pattern_matcher = PatternMatcher(real_vector_store, real_db)
    
    await pattern_matcher.store_pattern(
        problem_type="REST API",
        code="...",  # Flask REST API code
        tests="...", # Tests
        dependencies=["flask"]
    )
    
    # Execute: Search for similar pattern
    results = await pattern_matcher.search_patterns(
        "Build a REST API for user management"
    )
    
    # Assert
    assert len(results) > 0
    assert results[0]["problem_type"] == "REST API"
    assert results[0]["similarity"] > 0.7
```

---

## End-to-End Testing

Test complete task execution with real LLM calls.

**Note**: E2E tests are slow and expensive. Run sparingly (nightly builds, pre-release).

### Simple Task

```python
# tests/e2e/test_simple_task.py
import pytest

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_simple_function_task():
    """Test completing a simple function task end-to-end."""
    # Setup with real OpenAI client
    llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
    orchestrator = Orchestrator(llm_client, db_manager, config)
    
    # Execute
    result = await orchestrator.run(
        task_description="Write a Python function to calculate fibonacci numbers"
    )
    
    # Assert
    assert result["status"] == "SUCCESS"
    assert result["iterations"] <= 5  # Should complete quickly
    assert "fibonacci" in result["final_code"].lower()
    
    # Verify generated code works
    workspace = result["workspace"]
    exec(open(workspace / "solution.py").read())
    assert fibonacci(10) == 55  # Test actual execution
```

### API Task

```python
# tests/e2e/test_api_task.py
import pytest
import requests

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_rest_api_task():
    """Test building a REST API end-to-end."""
    orchestrator = Orchestrator(real_llm_client, db_manager, config)
    
    result = await orchestrator.run(
        task_description="Build a REST API with GET and POST endpoints for todos"
    )
    
    assert result["status"] == "SUCCESS"
    
    # Start the generated API
    workspace = result["workspace"]
    process = subprocess.Popen(
        ["python", "app.py"],
        cwd=workspace,
        stdout=subprocess.PIPE
    )
    time.sleep(2)  # Wait for startup
    
    try:
        # Test GET endpoint
        response = requests.get("http://localhost:5000/todos")
        assert response.status_code == 200
        
        # Test POST endpoint
        response = requests.post(
            "http://localhost:5000/todos",
            json={"title": "Test todo"}
        )
        assert response.status_code == 201
    finally:
        process.terminate()
```

---

## Coverage Targets

### Target Coverage by Module

| Module | Target | Notes |
|--------|--------|-------|
| `src/orchestrator.py` | 90%+ | Critical state machine logic |
| `src/agents/*.py` | 85%+ | Core agent behavior |
| `src/sandbox/safety_checker.py` | 95%+ | Security-critical |
| `src/memory/*.py` | 80%+ | Data operations |
| `src/llm/*.py` | 70%+ | Mostly integration |
| Overall | 80%+ | Minimum acceptable |

### Running Coverage

```bash
# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Fail if coverage below threshold
pytest tests/ --cov=src --cov-fail-under=80
```

---

## Test Fixtures

### Common Fixtures

**File**: `tests/conftest.py`

```python
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_config():
    """Mock configuration."""
    return MagicMock(
        orchestrator=MagicMock(
            max_iterations=15,
            checkpoint_frequency=5
        ),
        openai=MagicMock(
            models=MagicMock(
                planner="gpt-4",
                coder="gpt-4",
                tester="gpt-4",
                reflector="gpt-4"
            )
        ),
        sandbox=MagicMock(
            timeout_seconds=300,
            memory_limit_mb=1024
        )
    )

@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace

@pytest.fixture
async def mock_db():
    """Mock database manager."""
    db = AsyncMock()
    db.execute.return_value = "mock_id"
    db.fetch.return_value = []
    return db

@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    store = AsyncMock()
    store.generate_embedding.return_value = [0.1] * 1536
    store.search_patterns.return_value = []
    return store
```

---

## Test Organization

### Markers

Use pytest markers to categorize tests:

```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (multiple components)
    e2e: End-to-end tests (real LLM calls, slow)
    slow: Slow tests (skip in quick runs)
    requires_docker: Tests requiring Docker daemon
```

### Running Specific Tests

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only fast tests
pytest -m "not slow" -v

# Run specific module
pytest tests/unit/agents/ -v

# Run specific test
pytest tests/unit/agents/test_coder.py::test_coder_creates_file -v

# Run with specific markers
pytest -m integration -v
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - name: Run integration tests
        run: pytest tests/integration/ -v
        env:
          DB_PASSWORD: test
```

---

## Best Practices

### Do's ✅

- **Mock expensive operations** (LLM calls, database)
- **Test edge cases** (empty input, None, errors)
- **Test state transitions** exhaustively
- **Use fixtures** for common setup
- **Parametrize tests** for multiple inputs
- **Add docstrings** to tests explaining what they verify

### Don'ts ❌

- **Don't test implementation details** (test behavior)
- **Don't make real LLM calls** in unit tests
- **Don't leave commented-out tests**
- **Don't skip tests** without good reason
- **Don't write tests that depend on order**
- **Don't hardcode paths** (use fixtures)

---

## For More Information

- **Code conventions**: See [Code Conventions](code-conventions.md)
- **Architecture**: See [Architecture](architecture.md)
- **Development workflows**: See [Development Workflows](development-workflows.md)
