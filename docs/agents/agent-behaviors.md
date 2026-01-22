# Agent Behaviors

Detailed behavior specifications for each specialized agent in the system.

---

## Agent Overview

All agents inherit from `BaseAgent` and implement the `async execute(context: dict) -> dict` interface.

**Key Principle**: Agents are stateless. All state lives in the orchestrator or database.

| Agent | Responsibility | When It Runs |
|-------|----------------|--------------|
| **Planner** | Task decomposition | PLANNING state (once per task) |
| **Coder** | Code generation | CODING state (every iteration) |
| **Tester** | Test generation and execution | TESTING state (every iteration) |
| **Reflector** | Error analysis and fix generation | REFLECTING state (when tests fail) |

---

## Planner Agent

**File**: `src/agents/planner.py`  
**Goal**: Decompose complex tasks into actionable subtasks

### Process

1. Receive task description from user
2. Query memory for similar successful task patterns (vector search)
3. If patterns found, adapt them to current task
4. Decompose into 3-7 manageable subtasks
5. Identify required dependencies (packages, frameworks)
6. Return implementation plan with subtasks and approach

### Tools

- `search_success_patterns(problem_type)`: Vector similarity search in `patterns` table

### Input Context

```python
{
    "task_description": "Build a REST API for todo items",
    "language": "python",
    "task_type": "api"
}
```

### Output

```python
{
    "plan": {
        "subtasks": [
            "1. Create Flask app with basic structure",
            "2. Define Todo model with SQLAlchemy",
            "3. Implement GET /todos endpoint",
            "4. Implement POST /todos endpoint",
            "5. Add error handling and validation"
        ],
        "dependencies": ["flask", "flask-sqlalchemy"],
        "approach": "Use Flask with SQLAlchemy ORM for database operations",
        "similar_patterns_found": 2
    },
    "tokens_used": 450
}
```

### Configuration

**Model**: Configurable in `config/openai.yaml` (`models.planner`)  
**System Prompt**: Defined in `config/system_prompts.yaml` (`planner`)

### Behavior Notes

- Planner runs only once at the start of a task
- If similar patterns found (similarity > 0.7), adapts them rather than starting from scratch
- Keeps subtasks focused and testable
- Identifies dependencies early to avoid import errors later

---

## Coder Agent

**File**: `src/agents/coder.py`  
**Goal**: Generate clean, testable code

### Process

1. Receive plan from planner (first iteration) or reflection (subsequent iterations)
2. Read existing code files with `read_file` for context
3. Generate or update code files one at a time
4. Use `create_file` tool to write files to workspace
5. Follow code style: PEP 8, type hints, docstrings
6. Create `requirements.txt` with version-pinned dependencies
7. Return list of created/modified files

### Tools

- `create_file(path, content)`: Write file to workspace
- `read_file(path)`: Read existing file content
- `list_files(directory)`: List files in workspace
- `delete_file(path)`: Remove file (if implemented)

### Input Context

```python
{
    "plan": {
        "subtasks": [...],
        "dependencies": ["flask", "flask-sqlalchemy"]
    },
    "reflection": {  # Only present after first iteration
        "hypothesis": "Missing flask import in app.py",
        "similar_failures": [...]
    },
    "workspace": Path("/workspace/task_abc123")
}
```

### Output

```python
{
    "files_created": ["app.py", "models.py", "requirements.txt"],
    "files_modified": [],
    "tokens_used": 1200
}
```

### Configuration

**Model**: Configurable in `config/openai.yaml` (`models.coder`)  
**System Prompt**: Defined in `config/system_prompts.yaml` (`coder`)

### Code Generation Principles

- One file at a time (easier to track and debug)
- Type hints on all public functions
- Docstrings for all public functions
- No hardcoded credentials or secrets
- Version-pinned dependencies in `requirements.txt`
- Error handling for expected failure cases

### Safety Integration

Before writing files, code goes through:
1. **AST scanning** (blocks eval, exec, dangerous imports)
2. **Bandit SAST** (checks for security vulnerabilities)
3. **User approval** (if safety violations detected)

---

## Tester Agent

**File**: `src/agents/tester.py`  
**Goal**: Generate comprehensive tests and validate code

### Process

1. Receive list of code files from coder
2. Analyze code structure (functions, classes, imports)
3. Generate pytest tests for each function/class
4. Add hypothesis property-based tests for edge cases
5. Create test files using `create_test_file` tool
6. Execute tests in Docker sandbox using `run_tests` tool
7. Collect results: passed/failed, errors, coverage
8. Return test results in structured format

### Tools

- `create_test_file(path, content)`: Write test file
- `run_tests()`: Execute pytest in Docker sandbox
- `get_coverage()`: Get coverage report

### Input Context

```python
{
    "files_created": ["app.py", "models.py"],
    "workspace": Path("/workspace/task_abc123")
}
```

### Output (Success)

```python
{
    "test_results": {
        "status": "passed",
        "total": 10,
        "passed": 10,
        "failed": 0,
        "duration": 2.3,
        "coverage": 85.4
    },
    "test_files": ["tests/test_app.py", "tests/test_models.py"],
    "tokens_used": 800
}
```

### Output (Failure)

```python
{
    "test_results": {
        "status": "failed",
        "total": 10,
        "passed": 7,
        "failed": 3,
        "duration": 1.8,
        "errors": [
            {
                "test": "test_create_todo",
                "error_type": "ImportError",
                "error_message": "No module named 'flask'",
                "traceback": "..."
            },
            # ... more errors
        ]
    },
    "test_files": ["tests/test_app.py"],
    "tokens_used": 750
}
```

### Configuration

**Model**: Configurable in `config/openai.yaml` (`models.tester`)  
**System Prompt**: Defined in `config/system_prompts.yaml` (`tester`)  
**Sandbox Settings**: Defined in `config/settings.yaml` (`sandbox`)

### Test Generation Principles

- **Happy path testing**: Normal operation cases
- **Error handling testing**: Invalid inputs, edge cases
- **Edge cases**: Empty input, None, boundaries
- **Property-based tests** (hypothesis): Generate random inputs
- **Aim for 80%+ coverage**

### Sandbox Execution

Tests run in Docker container with:
- **CPU**: 1 core
- **RAM**: 1GB
- **Timeout**: 5 minutes
- **Network**: Disabled (unless approved)
- **Filesystem**: Workspace only

---

## Reflector Agent

**File**: `src/agents/reflector.py`  
**Goal**: Analyze failures and generate fix hypotheses

### Process

1. Receive test failures from tester
2. Parse error messages and stack traces
3. Categorize error type (ImportError, AttributeError, AssertionError, etc.)
4. Normalize error signature (e.g., "ImportError: module 'X'" → "ImportError: missing module")
5. Vector search for similar past failures in memory
6. If similar failures found, extract their solutions
7. Generate specific fix hypothesis (not just "fix the error")
8. Return hypothesis with supporting evidence

### Tools

- `search_similar_failures(error_message)`: Vector similarity search in `failures` table
- `search_success_patterns(problem_type)`: Vector search in `patterns` table

### Input Context

```python
{
    "test_results": {
        "status": "failed",
        "errors": [
            {
                "test": "test_create_todo",
                "error_type": "ImportError",
                "error_message": "No module named 'flask'",
                "traceback": "..."
            }
        ]
    },
    "iteration": 3
}
```

### Output

```python
{
    "reflection": {
        "error_analysis": {
            "primary_error": "ImportError",
            "error_signature": "ImportError: missing module 'flask'",
            "root_cause": "Missing dependency in requirements.txt or not installed"
        },
        "hypothesis": "Add 'flask==3.0.0' to requirements.txt. The import statement exists in app.py but the package is not listed as a dependency.",
        "similar_failures_found": 2,
        "similar_failures": [
            {
                "error": "ImportError: module 'flask-sqlalchemy'",
                "solution": "Added flask-sqlalchemy to requirements.txt",
                "similarity": 0.92
            }
        ],
        "confidence": "high"
    },
    "tokens_used": 600
}
```

### Configuration

**Model**: Configurable in `config/openai.yaml` (`models.reflector`)  
**System Prompt**: Defined in `config/system_prompts.yaml` (`reflector`)

### Error Analysis Patterns

**ImportError**:
- Check if module in requirements.txt
- Check for typos in import statement
- Check if module name changed (e.g., PIL vs Pillow)

**AttributeError**:
- Check if attribute exists in current version
- Check for typos
- Check if object is None

**AssertionError** (test failure):
- Check expected vs actual values
- Check if logic error in implementation
- Check if test expectations are correct

**SyntaxError**:
- Check for unclosed brackets, quotes
- Check indentation
- Check for Python version compatibility

### Hypothesis Quality

Good hypothesis:
- ✅ Specific: "Add 'flask==3.0.0' to requirements.txt"
- ✅ Actionable: Coder knows exactly what to do
- ✅ Justified: References similar past solutions

Bad hypothesis:
- ❌ Vague: "Fix the import error"
- ❌ Not actionable: "Something is wrong with the code"
- ❌ No evidence: "Try changing something"

---

## Agent Collaboration

### Information Flow

```
Planner → Coder → Tester → (if fail) → Reflector → Coder → ...
```

### Context Passing

Agents communicate via the shared `context` dictionary managed by orchestrator:

```python
# After Planner
context["plan"] = planner_output["plan"]

# After Coder
context["files_created"] = coder_output["files_created"]

# After Tester
context["test_results"] = tester_output["test_results"]

# After Reflector
context["reflection"] = reflector_output["reflection"]

# Next iteration: Coder sees plan + reflection
```

### Iteration Awareness

Agents can behave differently based on iteration:

```python
# First iteration: Use plan
if "reflection" not in context:
    # Fresh implementation from plan
    pass
else:
    # Incorporate feedback from reflection
    hypothesis = context["reflection"]["hypothesis"]
    # Fix based on hypothesis
```

---

## Extending Agents

### Adding a New Agent

1. Create class inheriting from `BaseAgent` in `src/agents/`
2. Implement `async execute(self, context: dict) -> dict`
3. Define tools in `src/llm/tools.py`
4. Add model to `config/openai.yaml`
5. Add system prompt to `config/system_prompts.yaml`
6. Add state to `OrchestrationState` enum
7. Add state handler to orchestrator

**Example**: Validator agent for static analysis

```python
# src/agents/validator.py
from .base_agent import BaseAgent

class ValidatorAgent(BaseAgent):
    """Static analysis and linting agent."""
    
    async def execute(self, context: dict) -> dict:
        """Run static analysis on generated code.
        
        Args:
            context: Must contain 'files_created' key
            
        Returns:
            Validation results with issues found
        """
        files = context["files_created"]
        issues = []
        
        for file_path in files:
            # Run mypy, flake8, etc.
            file_issues = await self._analyze_file(file_path)
            issues.extend(file_issues)
        
        return {
            "validation_status": "passed" if not issues else "failed",
            "issues": issues,
            "tokens_used": 0  # No LLM calls for static analysis
        }
```

---

## For More Information

- **Architecture**: See [Architecture](architecture.md)
- **Code patterns**: See [Code Conventions](code-conventions.md)
- **System behavior**: See [FUNCTIONALITY.md](../../FUNCTIONALITY.md)
