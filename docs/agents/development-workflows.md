# Development Workflows

Common implementation tasks and workflows for working on the autonomous coding agent.

---

## Adding a New Tool

**Example**: Add `delete_file` tool for Coder agent

### 1. Define Tool Schema

In `src/llm/tools.py`:

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
                    "description": "Path to file relative to workspace"
                }
            },
            "required": ["path"]
        }
    }
}

# Add to CODER_TOOLS list
CODER_TOOLS = [CREATE_FILE_TOOL, READ_FILE_TOOL, LIST_FILES_TOOL, DELETE_FILE_TOOL]
```

### 2. Implement Handler

In `src/agents/coder.py`:

```python
def _handle_tool_call(self, tool_call: dict, workspace: Path) -> dict:
    tool_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    if tool_name == "delete_file":
        return self._delete_file(args["path"], workspace)
    # ... other tools ...

def _delete_file(self, path: str, workspace: Path) -> dict:
    """Delete a file from the workspace.
    
    Args:
        path: Path to file relative to workspace
        workspace: Workspace root directory
        
    Returns:
        dict: Success/error result
    """
    file_path = workspace / path
    
    # Safety: must be within workspace
    if not file_path.resolve().is_relative_to(workspace.resolve()):
        return {"error": "Path must be within workspace"}
    
    if not file_path.exists():
        return {"error": f"File not found: {path}"}
    
    file_path.unlink()
    return {"success": True, "message": f"Deleted {path}"}
```

### 3. Add Tests

In `tests/agents/test_coder.py`:

```python
@pytest.mark.asyncio
async def test_delete_file_success(coder_agent, tmp_workspace):
    """Test deleting a file successfully."""
    # Setup
    test_file = tmp_workspace / "test.txt"
    test_file.write_text("content")
    
    # Execute
    result = coder_agent._delete_file("test.txt", tmp_workspace)
    
    # Assert
    assert result["success"] is True
    assert not test_file.exists()

@pytest.mark.asyncio
async def test_delete_file_path_traversal(coder_agent, tmp_workspace):
    """Test deleting a file outside workspace is blocked."""
    result = coder_agent._delete_file("../../etc/passwd", tmp_workspace)
    
    assert "error" in result
    assert "within workspace" in result["error"]
```

### 4. Update Documentation

- Update tool list in this file
- Update `FUNCTIONALITY.md` if behavior changes
- Add to agent behaviors documentation if needed

---

## Adding a New State

**Example**: Add `VALIDATING` state for syntax checking

### 1. Add to OrchestrationState Enum

In `src/orchestrator.py`:

```python
class OrchestrationState(Enum):
    INIT = "init"
    PLANNING = "planning"
    CODING = "coding"
    VALIDATING = "validating"  # New state
    TESTING = "testing"
    REFLECTING = "reflecting"
    SUCCESS = "success"
    FAILED = "failed"
```

### 2. Implement State Handler

In `src/orchestrator.py`:

```python
async def _run_validating_state(self) -> OrchestrationState:
    """Validate generated code syntax and imports.
    
    Returns:
        Next state (TESTING if valid, REFLECTING if invalid)
    """
    self.logger.info("state_validating", iteration=self.iteration)
    
    # Get code files from context
    code_files = self.context.get("code_files", [])
    
    # Run syntax validation
    validator = SyntaxValidator()
    validation_results = await validator.validate_files(code_files)
    
    # Store results in context
    self.context["validation_results"] = validation_results
    
    if validation_results["valid"]:
        return OrchestrationState.TESTING
    else:
        # Add validation errors to context for reflector
        self.context["validation_errors"] = validation_results["errors"]
        return OrchestrationState.REFLECTING
```

### 3. Update State Handlers Dictionary

In `src/orchestrator.py`:

```python
def __init__(self, ...):
    self.state_handlers = {
        OrchestrationState.INIT: self._run_init_state,
        OrchestrationState.PLANNING: self._run_planning_state,
        OrchestrationState.CODING: self._run_coding_state,
        OrchestrationState.VALIDATING: self._run_validating_state,  # Add here
        OrchestrationState.TESTING: self._run_testing_state,
        OrchestrationState.REFLECTING: self._run_reflecting_state,
    }
```

### 4. Update State Transitions

Modify the state that should transition to the new state:

```python
async def _run_coding_state(self) -> OrchestrationState:
    # ... existing code ...
    
    # Instead of going directly to TESTING:
    # return OrchestrationState.TESTING
    
    # Go to VALIDATING first:
    return OrchestrationState.VALIDATING
```

### 5. Add Tests

In `tests/test_orchestrator.py`:

```python
@pytest.mark.asyncio
async def test_validating_state_success(orchestrator, mock_validator):
    """Test VALIDATING state with valid code."""
    orchestrator.context = {"code_files": ["app.py"]}
    mock_validator.validate_files.return_value = {"valid": True}
    
    next_state = await orchestrator._run_validating_state()
    
    assert next_state == OrchestrationState.TESTING

@pytest.mark.asyncio
async def test_validating_state_failure(orchestrator, mock_validator):
    """Test VALIDATING state with invalid code."""
    orchestrator.context = {"code_files": ["app.py"]}
    mock_validator.validate_files.return_value = {
        "valid": False,
        "errors": ["SyntaxError: invalid syntax"]
    }
    
    next_state = await orchestrator._run_validating_state()
    
    assert next_state == OrchestrationState.REFLECTING
    assert "validation_errors" in orchestrator.context
```

---

## Bug Fix Workflow

### 1. Reproduce the Issue

```bash
# Run the failing task/test
pytest tests/test_specific_issue.py -v

# Or run the system
python -m src.main run --task "..." --language python

# Check logs
tail -f logs/autonomous_agent.log
```

### 2. Identify Root Cause

- Read relevant code files
- Check stack trace
- Review recent changes (`git log`, `git diff`)
- Check related tests

### 3. Make Minimal Fix

Focus on the root cause. Avoid refactoring unless necessary.

**Example**: Fix vector search threshold too strict

In `src/memory/vector_store.py`:

```python
# Before
async def search_similar_failures(self, query: str, threshold: float = 0.9) -> List[dict]:

# After
async def search_similar_failures(self, query: str, threshold: float = 0.6) -> List[dict]:
```

### 4. Add Tests

Always add a test that would have caught the bug:

```python
@pytest.mark.asyncio
async def test_vector_search_finds_similar_failures(vector_store):
    """Test that similar failures are found with reasonable threshold."""
    # Setup
    await vector_store.store_failure("ImportError: module 'flask'", "...")
    
    # Execute with similar error
    results = await vector_store.search_similar_failures("ImportError: module 'flask-sqlalchemy'")
    
    # Should find at least one similar result
    assert len(results) > 0
```

### 5. Verify No Regressions

```bash
# Run full test suite
pytest tests/ -v

# Run specific affected areas
pytest tests/memory/ -v
pytest tests/integration/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Adding Safety Rules

**Example**: Block `socket` module

### 1. Update Safety Checker

In `src/sandbox/safety_checker.py`:

```python
DANGEROUS_IMPORTS = [
    "os",
    "subprocess",
    "pty",
    "socket",  # Add here
    "sys",
    # ...
]
```

### 2. Update Configuration

In `config/safety_rules.yaml`:

```yaml
blocked_imports:
  - os
  - subprocess
  - pty
  - socket  # Add here
  - sys

blocked_functions:
  - eval
  - exec
  - compile
  - socket.socket  # Add specific functions too
```

### 3. Add Tests

In `tests/sandbox/test_safety_checker.py`:

```python
def test_blocks_socket_import():
    """Test that socket imports are blocked."""
    code = """
import socket

sock = socket.socket()
"""
    checker = SafetyChecker()
    violations = checker.check_code(code)
    
    assert len(violations) > 0
    assert any("socket" in v for v in violations)
```

---

## Adding Configuration

**Example**: Add timeout configuration for Docker

### 1. Add to YAML

In `config/settings.yaml`:

```yaml
sandbox:
  timeout_seconds: 300  # 5 minutes
  memory_limit_mb: 1024  # 1GB
  cpu_limit: 1.0
```

### 2. Load in ConfigLoader

In `src/config_loader.py`:

```python
@dataclass
class SandboxConfig:
    timeout_seconds: int = 300
    memory_limit_mb: int = 1024
    cpu_limit: float = 1.0

@dataclass
class Config:
    # ... other config sections ...
    sandbox: SandboxConfig
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(
            # ... other sections ...
            sandbox=SandboxConfig(**data.get("sandbox", {}))
        )
```

### 3. Use in Code

In `src/sandbox/docker_executor.py`:

```python
class DockerExecutor:
    def __init__(self, config: Config):
        self.config = config
    
    async def execute(self, code: str) -> dict:
        # Use config instead of hardcoded values
        timeout = self.config.sandbox.timeout_seconds
        memory_limit = f"{self.config.sandbox.memory_limit_mb}m"
        cpu_limit = self.config.sandbox.cpu_limit
        
        # ... execute with these limits ...
```

### 4. Validate Configuration

Add validation in `ConfigLoader`:

```python
def validate(self):
    """Validate configuration values."""
    if self.sandbox.timeout_seconds <= 0:
        raise ValueError("sandbox.timeout_seconds must be positive")
    
    if self.sandbox.memory_limit_mb < 128:
        raise ValueError("sandbox.memory_limit_mb must be at least 128")
    
    if not 0 < self.sandbox.cpu_limit <= 8:
        raise ValueError("sandbox.cpu_limit must be between 0 and 8")
```

---

## Performance Optimization

### Identifying Bottlenecks

```python
# Add timing to operations
import time
from structlog import get_logger

logger = get_logger()

start = time.time()
result = await slow_operation()
duration = time.time() - start

logger.info("operation_completed", 
           operation="slow_operation",
           duration_seconds=duration)
```

### Common Optimizations

**1. Cache Vector Embeddings**:
```python
# Before: Generate embedding every time
embedding = await self.llm_client.get_embedding(text)

# After: Cache embeddings
@lru_cache(maxsize=1000)
async def get_cached_embedding(self, text: str):
    return await self.llm_client.get_embedding(text)
```

**2. Batch LLM Calls**:
```python
# Before: Multiple sequential calls
for item in items:
    result = await llm_client.process(item)

# After: Batch where possible
results = await llm_client.process_batch(items)
```

**3. Optimize Database Queries**:
```python
# Before: N+1 queries
for task_id in task_ids:
    task = await db.get_task(task_id)

# After: Single query
tasks = await db.get_tasks_batch(task_ids)
```

---

## Pre-Commit Checklist

Before committing code:

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/`
- [ ] Imports sorted: `isort src/ tests/`
- [ ] Type hints correct: `mypy src/`
- [ ] Linting clean: `flake8 src/ tests/`
- [ ] New features have tests
- [ ] Configuration updated if needed
- [ ] Documentation updated if behavior changed
- [ ] Database migration included if schema changed

---

## For More Information

- **Code patterns**: See [Code Conventions](code-conventions.md)
- **Architecture**: See [Architecture](architecture.md)
- **Testing**: See [Testing Strategy](testing-strategy.md)
