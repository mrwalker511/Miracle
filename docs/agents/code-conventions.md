# Code Conventions

Code patterns and best practices for the Miracle autonomous coding agent.

---

## Async/Await Pattern

All agent methods and LLM calls must be async.

### ✅ Correct

```python
# Agent methods
async def execute(self, context: dict) -> dict:
    result = await self.some_async_operation()
    return result

# LLM calls
response = await self.llm_client.chat_completion(messages)
result = await coder.execute(context)

# Multiple awaits
plan = await planner.execute(context)
code = await coder.execute(context)
```

### ❌ Incorrect

```python
# Missing await - returns coroutine object
result = coder.execute(context)  # BUG: coroutine not awaited

# Mixing sync and async
def execute(self, context):  # BUG: should be async
    result = await self.llm_client.chat_completion(messages)
```

---

## Database Operations

Always use async context managers to prevent connection leaks.

### ✅ Correct

```python
# Connection management
async with self.db_manager.get_connection() as conn:
    await conn.execute(query, params)
    result = await conn.fetchall()

# Transaction management
async with self.db_manager.transaction() as tx:
    await tx.execute(query1, params1)
    await tx.execute(query2, params2)
    # Auto-commit on success, rollback on exception
```

### ❌ Incorrect

```python
# Connection leak - no context manager
conn = await self.db_manager.get_connection()
await conn.execute(query)
# BUG: Connection never returned to pool

# Missing await
async with self.db_manager.get_connection() as conn:
    conn.execute(query)  # BUG: Missing await
```

---

## Configuration Access

Always read from config, never hardcode values.

### ✅ Correct

```python
# Access configuration
max_iterations = self.config.orchestrator.max_iterations
checkpoint_freq = self.config.orchestrator.checkpoint_frequency
model_name = self.config.openai.models.coder

# With defaults
timeout = self.config.sandbox.get("timeout_seconds", 300)
```

### ❌ Incorrect

```python
# Hardcoded values
max_iterations = 15  # BUG: Should be from config
model_name = "gpt-4-turbo-preview"  # BUG: Should be from config
```

---

## LLM Retry Logic

Use Tenacity for resilience against API failures.

### ✅ Correct

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _call_llm_with_retry(self, messages: List[dict]) -> str:
    """Call LLM with automatic retry on failures.
    
    Args:
        messages: Chat messages
        
    Returns:
        LLM response text
        
    Raises:
        Exception: After 3 failed attempts
    """
    response = await self.llm_client.chat_completion(messages)
    return response.choices[0].message.content
```

### With Fallback Models

```python
async def _call_llm_with_fallback(self, messages: List[dict]) -> str:
    """Call LLM with fallback to secondary models."""
    models = self.config.openai.fallback_sequence
    
    for model in models:
        try:
            response = await self.llm_client.chat_completion(
                messages, model=model
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.warning("llm_call_failed", model=model, error=str(e))
            continue
    
    raise Exception("All LLM models failed")
```

---

## Logging Patterns

Use structured logging with context.

### ✅ Correct

```python
from structlog import get_logger

logger = get_logger()

# Log with context
logger.info(
    "state_transition",
    from_state=current_state,
    to_state=next_state,
    iteration=self.iteration
)

# Log with timing
import time
start = time.time()
result = await operation()
duration = time.time() - start

logger.info(
    "operation_completed",
    operation="coding",
    duration_seconds=duration,
    tokens_used=result.get("tokens")
)

# Log errors with full context
try:
    result = await risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        operation="risky_operation",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True  # Include stack trace
    )
    raise
```

### ❌ Incorrect

```python
# Unstructured logging
print("State changed to CODING")  # BUG: Use logger

# Missing context
logger.info("Operation completed")  # BUG: No useful info

# String concatenation
logger.info(f"Iteration {iteration} failed")  # Bad: Use structured fields
```

---

## Error Handling

Handle errors at appropriate levels.

### ✅ Correct

```python
# Handle specific errors
try:
    result = await self.llm_client.chat_completion(messages)
except RateLimitError:
    logger.warning("rate_limit_hit", retry_after=60)
    await asyncio.sleep(60)
    result = await self.llm_client.chat_completion(messages)
except TimeoutError:
    logger.error("llm_timeout", timeout=30)
    raise
except Exception as e:
    logger.error("llm_call_failed", error=str(e))
    raise

# Return error results instead of raising
def _validate_path(self, path: str, workspace: Path) -> Optional[str]:
    """Validate path is within workspace.
    
    Returns:
        Error message if invalid, None if valid
    """
    file_path = workspace / path
    if not file_path.resolve().is_relative_to(workspace.resolve()):
        return "Path must be within workspace"
    return None
```

### ❌ Incorrect

```python
# Catching too broad
try:
    result = await operation()
except:  # BUG: Catches everything including KeyboardInterrupt
    pass

# Swallowing errors
try:
    result = await operation()
except Exception:
    pass  # BUG: Error lost, no logging

# Raising without context
raise Exception("Failed")  # BUG: No context about what failed
```

---

## Type Hints

Use type hints on all public functions and class attributes.

### ✅ Correct

```python
from typing import List, Dict, Optional, Union
from pathlib import Path

async def execute(
    self,
    context: Dict[str, any],
    workspace: Path,
    timeout: Optional[int] = None
) -> Dict[str, any]:
    """Execute agent logic.
    
    Args:
        context: Execution context
        workspace: Workspace directory
        timeout: Optional timeout in seconds
        
    Returns:
        Execution results with status and outputs
    """
    # Implementation
    return {"status": "success", "outputs": []}

# Class attributes
class Orchestrator:
    iteration: int
    context: Dict[str, any]
    state: OrchestrationState
```

### ❌ Incorrect

```python
# Missing type hints
async def execute(self, context, workspace):  # BUG: No types
    pass

# Incorrect types
def process(self, items: list):  # Bad: Use List[type]
    pass
```

---

## Docstrings

Use Google-style docstrings for all public functions.

### ✅ Correct

```python
async def search_similar_failures(
    self,
    error_message: str,
    threshold: float = 0.6,
    limit: int = 5
) -> List[Dict[str, any]]:
    """Search for similar past failures using vector similarity.
    
    Generates an embedding for the error message and queries the failures
    table for similar errors using cosine distance.
    
    Args:
        error_message: The error message to search for
        threshold: Similarity threshold (0-1, lower = more similar)
        limit: Maximum number of results to return
        
    Returns:
        List of similar failures, each containing:
            - id: Failure ID
            - error_signature: Normalized error pattern
            - solution: How it was fixed
            - similarity: Similarity score (0-1)
            
    Raises:
        DatabaseError: If database query fails
        EmbeddingError: If embedding generation fails
        
    Example:
        >>> results = await store.search_similar_failures(
        ...     "ImportError: No module named 'flask'",
        ...     threshold=0.6,
        ...     limit=3
        ... )
        >>> print(results[0]["solution"])
        "Add flask to requirements.txt"
    """
    # Implementation
```

### ❌ Incorrect

```python
# Missing docstring
async def search_similar_failures(self, error_message: str):
    pass

# Vague docstring
async def search_similar_failures(self, error_message: str):
    """Search for failures."""  # BUG: Not helpful
    pass
```

---

## Path Handling

Always use `pathlib.Path` for file operations.

### ✅ Correct

```python
from pathlib import Path

# Path construction
workspace = Path("/workspace/task_123")
code_file = workspace / "app.py"
test_dir = workspace / "tests"

# Path validation
if not code_file.exists():
    raise FileNotFoundError(f"File not found: {code_file}")

if not code_file.resolve().is_relative_to(workspace.resolve()):
    raise ValueError("Path outside workspace")

# Reading/writing
content = code_file.read_text()
code_file.write_text(new_content)
```

### ❌ Incorrect

```python
# String concatenation
workspace = "/workspace/task_123"
code_file = workspace + "/app.py"  # BUG: Use Path

# os.path (old style)
import os
code_file = os.path.join(workspace, "app.py")  # Bad: Use pathlib
```

---

## Tool Call Handling

Validate tool arguments before execution.

### ✅ Correct

```python
def _handle_tool_call(
    self,
    tool_call: dict,
    workspace: Path
) -> Dict[str, any]:
    """Handle tool call from LLM.
    
    Args:
        tool_call: OpenAI tool call object
        workspace: Workspace directory
        
    Returns:
        Tool execution result
    """
    tool_name = tool_call.function.name
    
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid tool arguments: {e}"}
    
    # Validate required arguments
    if tool_name == "create_file":
        if "path" not in args or "content" not in args:
            return {"error": "Missing required arguments: path, content"}
        
        # Validate path
        error = self._validate_path(args["path"], workspace)
        if error:
            return {"error": error}
        
        return self._create_file(args["path"], args["content"], workspace)
    
    return {"error": f"Unknown tool: {tool_name}"}
```

### ❌ Incorrect

```python
# No validation
def _handle_tool_call(self, tool_call, workspace):
    args = json.loads(tool_call.function.arguments)
    # BUG: No validation, direct execution
    return self._create_file(args["path"], args["content"], workspace)
```

---

## Testing Patterns

Write testable code with dependency injection.

### ✅ Correct

```python
class CoderAgent(BaseAgent):
    def __init__(
        self,
        llm_client: OpenAIClient,
        config: Config,
        file_system: Optional[FileSystem] = None
    ):
        """Initialize coder agent.
        
        Args:
            llm_client: LLM client for code generation
            config: System configuration
            file_system: Optional file system wrapper (for testing)
        """
        self.llm_client = llm_client
        self.config = config
        self.file_system = file_system or RealFileSystem()

# Easy to test
@pytest.mark.asyncio
async def test_coder_creates_file():
    mock_llm = MockLLMClient()
    mock_fs = MockFileSystem()
    config = Config.from_dict({"test": True})
    
    coder = CoderAgent(mock_llm, config, file_system=mock_fs)
    await coder.execute({"task": "create file"})
    
    assert mock_fs.files_created == ["app.py"]
```

### ❌ Incorrect

```python
# Hard to test - dependencies created internally
class CoderAgent:
    def __init__(self):
        self.llm_client = OpenAIClient()  # BUG: Hard to mock
        self.config = Config.load()  # BUG: Hard to test
```

---

## Common Pitfalls to Avoid

1. **Missing await on async functions** → Returns coroutine object
2. **Not using context managers for DB** → Connection leaks
3. **Hardcoding config values** → Not configurable
4. **Not handling LLM failures** → System crashes
5. **Broad exception catching** → Hides bugs
6. **Missing type hints** → Hard to maintain
7. **Vague error messages** → Hard to debug
8. **String path manipulation** → Cross-platform issues
9. **No input validation** → Security vulnerabilities
10. **Tightly coupled code** → Hard to test

---

## For More Information

- **Architecture patterns**: See [Architecture](architecture.md)
- **Development workflows**: See [Development Workflows](development-workflows.md)
- **Testing patterns**: See [Testing Strategy](testing-strategy.md)
