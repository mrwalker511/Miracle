# AGENT-EXECUTION.md

> **Purpose**: Concise guide for AI execution agents implementing features, fixing bugs, and executing tasks.

## Quick Context

**Project**: Miracle - Autonomous Coding Agent
**Your Role**: Implementation, bug fixes, testing, refactoring
**Language**: Python 3.11+
**Entry Point**: `src/main.py` (CLI)
**Test Framework**: pytest + hypothesis
**Code Style**: PEP 8, type hints required
**Documentation**: Use docstrings for all public functions

---

## Project Structure

```
autonomous_agent/
├── src/
│   ├── main.py                  # CLI entry point ⭐ START HERE
│   ├── orchestrator.py          # State machine controller
│   ├── config_loader.py         # Configuration management
│   ├── agents/                  # AI agents (BaseAgent subclass)
│   │   ├── base_agent.py        # Abstract base
│   │   ├── planner.py           # Task planning
│   │   ├── coder.py             # Code generation
│   │   ├── tester.py            # Test generation + execution
│   │   └── reflector.py         # Error analysis
│   ├── llm/                     # LLM interface + tools
│   ├── memory/                  # Vector DB + pattern matching
│   ├── sandbox/                 # Docker execution + safety
│   ├── testing/                 # Test generation/running
│   ├── projects/                # Language scaffolding
│   ├── ui/                      # Rich CLI, logging
│   └── utils/                   # Circuit breaker, checkpoints
├── config/                      # YAML configs ⚙️
├── scripts/                     # Database setup
├── tests/                       # Unit tests
├── sandbox/workspace/           # Code execution area
└── logs/                        # Structured logs
```

---

## Setup (First Time)

```bash
# Navigate and setup
cd /home/user/Miracle/autonomous_agent
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add OPENAI_API_KEY, DB_PASSWORD

# Start database
docker-compose up -d postgres
python scripts/setup_db.py

# Run tests
pytest tests/ -v
```

---

## Common Implementation Tasks

### Task 1: Adding a New Tool

**Example**: Add `delete_file` tool for Coder

1. Define tool schema in `src/llm/tools.py`:
   ```python
   DELETE_FILE_TOOL = {
       "type": "function",
       "function": {
           "name": "delete_file",
           "description": "Delete a file from the workspace",
           "parameters": {
               "type": "object",
               "properties": {
                   "path": {"type": "string"}
               },
               "required": ["path"]
           }
       }
   }
   # Add to CODER_TOOLS list
   ```

2. Implement handler in `src/agents/coder.py`:
   ```python
   def _handle_tool_call(self, tool_call: dict, workspace: Path) -> dict:
       # ... routing logic ...
       if tool_name == "delete_file":
           return self._delete_file(args["path"], workspace)

   def _delete_file(self, path: str, workspace: Path) -> dict:
       file_path = workspace / path
       # Safety: must be within workspace
       if not file_path.resolve().is_relative_to(workspace.resolve()):
           return {"error": "Path must be within workspace"}
       file_path.unlink()
       return {"success": True, "message": f"Deleted {path}"}
   ```

3. Add tests in `tests/agents/test_coder.py`

4. Update docs: `FUNCTIONALITY.md`, `ARCHITECTURE.md`

---

### Task 2: Adding Safety Rules

**Example**: Block `socket` module

1. Update `src/sandbox/safety_checker.py`:
   ```python
   DANGEROUS_IMPORTS = ["os", "subprocess", "pty", "socket", ...]
   ```

2. Add to `config/safety_rules.yaml`:
   ```yaml
   blocked_imports: [socket, ...]
   blocked_functions: [socket.socket, ...]
   ```

3. Add tests in `tests/sandbox/test_safety_checker.py`

---

### Task 3: Adding a New State

**Example**: Add `VALIDATING` state for syntax checking

1. Add to `OrchestrationState` enum in `src/orchestrator.py`
2. Implement `async def _run_validating_state(self)` method
3. Update state_handlers dictionary
4. Update state transition logic
5. Add tests for new state

---

### Task 4: Bug Fix Workflow

1. **Reproduce**: Run task, check logs
2. **Identify root cause**: Read relevant code
3. **Fix**: Make minimal change
4. **Test**: Add unit tests
5. **Verify**: Run pytest, check for regressions

**Example**: Fix vector search threshold too strict (0.9 → 0.6)

---

## Code Patterns

### Async/Await
All agent methods and LLM calls are async:
```python
# ✅ Good
result = await coder.execute(context)
response = await self.llm_client.chat_completion(messages)

# ❌ Bad - missing await
result = coder.execute(context)  # Returns coroutine
```

### Database Operations
Use context managers:
```python
# ✅ Good
async with self.db_manager.get_connection() as conn:
    await conn.execute(query, params)

# ❌ Bad - leaks connections
conn = await self.db_manager.get_connection()
await conn.execute(query)
```

### Configuration Access
```python
# ✅ Good
max_iterations = self.config.orchestrator.max_iterations

# ❌ Bad - hardcoded
max_iterations = 15
```

### LLM Retry Logic
Use tenacity for resilience:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _call_llm_with_retry(self, messages):
    response = await self.llm_client.chat_completion(messages)
    return response.choices[0].message.content
```

---

## Testing Guidelines

### Unit Tests
- Mock LLM calls (expensive, non-deterministic)
- Use pytest fixtures for setup/teardown
- Test state transitions exhaustively

### Property-Based Testing
Use hypothesis for safety checker:
```python
@given(st.text())
def test_safety_checker_blocks_dangerous_input(code):
    checker = SafetyChecker()
    violations = checker.check_code(code)
    assert all("dangerous" in v for v in violations)
```

### Coverage
Aim for 80%+ on core modules:
```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Security Checklist

Before committing code that executes user code:

- [ ] AST scanning blocks eval, exec, __import__
- [ ] Bandit scan passes
- [ ] User approval for network/subsystem access
- [ ] Docker sandboxing with resource limits
- [ ] Path validation prevents directory traversal
- [ ] Input sanitization for file paths/commands
- [ ] No secrets logged (API keys, passwords)
- [ ] Allowlist approach for dependencies

---

## Pre-Commit Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/`
- [ ] Imports sorted: `isort src/ tests/`
- [ ] Type hints correct: `mypy src/`
- [ ] No linting errors: `flake8 src/ tests/`
- [ ] Docstrings complete (public functions)
- [ ] Config updated if needed
- [ ] New features tested
- [ ] Logs appropriate level
- [ ] No debug statements (print, IPython embed)
- [ ] Database migrations included if schema changed

---

## Common Pitfalls

1. **Missing await**: LLM calls and agent methods return coroutines
2. **Modifying shared state directly**: Use orchestrator methods
3. **Hardcoding config**: Always use `self.config`
4. **Not handling LLM failures**: Wrap in retry logic
5. **Leaking database connections**: Always use context managers
6. **Forgetting type hints**: Required for all public functions
7. **Not testing edge cases**: Add comprehensive unit tests

---

## Collaboration with Planning Agents

### Receiving Plans
1. Read full plan before starting
2. Clarify ambiguities early
3. Report blockers (missing deps, unclear requirements)
4. Follow architecture (deviate only after discussion)
5. Document deviations with rationale

### Reporting Progress
Update on: completion status, unexpected challenges, technical decisions, new edge cases, performance observations

### Handoff Format
```markdown
## Implementation Status: [Feature Name]

### Completed
- ✅ Task 1 (commit: abc123)
- ✅ Task 2 (commit: def456)

### In Progress
- 🔄 Task 3 (80%) - Blocker: Need clarification on X

### Deviations
- Changed approach for Task 2 because Y

### Questions
1. Should we handle edge case Z?
```

---

## Key Files to Understand

**Must-read** (in order):
1. `src/orchestrator.py` - State machine core
2. `src/agents/base_agent.py` - Agent interface
3. `src/llm/tools.py` - Available tools
4. `config/settings.yaml` - System config
5. `scripts/init_db.sql` - Database schema

**Reference:**
- `ARCHITECTURE.md` - Deep technical details
- `FUNCTIONALITY.md` - System behavior
- `DEPENDENCIES.md` - Setup instructions
- `autonomous_coding_agent_handoff.md` - Comprehensive spec (1516 lines)

---

## Success Criteria

An execution agent succeeds when:
1. ✅ All tests pass (unit + integration)
2. ✅ Code follows PEP 8, type hints, docstrings
3. ✅ No regressions (existing functionality works)
4. ✅ Performance acceptable (no major slowdowns)
5. ✅ Security maintained (no new vulnerabilities)
6. ✅ Documentation updated (if behavior changed)
7. ✅ Config backward compatible (or migration provided)
8. ✅ Logs informative (debuggable)
9. ✅ Error handling robust (no unhandled exceptions)

---

**Last Updated**: 2025-01-21
**Maintained By**: AI Execution Agents
**Related**: `AGENT-PLANNING.md`, `ARCHITECTURE.md`, `FUNCTIONALITY.md`
