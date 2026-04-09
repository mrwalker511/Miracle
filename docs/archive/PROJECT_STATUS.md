# Project Status & Remaining Phases

**Project**: Miracle — Autonomous Coding Agent  
**Last Updated**: 2026-04-09  
**Version**: 0.1.0

---

## Current State Audit

### ✅ What's Built and Working

| Component | File(s) | Status | Notes |
|-----------|---------|--------|-------|
| **CLI Entry Point** | `src/main.py` | ✅ Complete | Click CLI with `run`, `history`, `setup` commands. Rich UI panels. |
| **Orchestrator** | `src/orchestrator.py` | ✅ Complete | Full state machine (INIT→PLANNING→CODING→TESTING→REFLECTING→loop). 667 lines. |
| **Agent Base Class** | `src/agents/base_agent.py` | ✅ Complete | `BaseAgent` ABC with `execute()`, `build_messages()`, `call_llm()`, `extract_text_response()`, `extract_tool_calls()`. |
| **Planner Agent** | `src/agents/planner.py` | ✅ Complete | Task decomposition, pattern memory queries, plan parsing. |
| **Coder Agent** | `src/agents/coder.py` | ✅ Complete | Code generation via LLM tool calls, file writing. 13KB. |
| **Tester Agent** | `src/agents/tester.py` | ✅ Complete | Test generation and execution via sandbox. 14KB. |
| **Reflector Agent** | `src/agents/reflector.py` | ✅ Complete | Error analysis, vector search for similar failures, fix hypothesis. 8.7KB. |
| **Code Reviewer** | `src/agents/optional/code_reviewer.py` | ✅ Complete | Optional phase, flag-enabled (`--enable-review`). |
| **Security Auditor** | `src/agents/optional/security_auditor.py` | ✅ Complete | Optional phase, flag-enabled (`--enable-audit`). 16KB. |
| **Agent Factory** | `src/agents/__init__.py` | ✅ Complete | Registry + factory pattern for agent creation. |
| **Reprompter** | `src/preprocessing/reprompter.py` | ✅ Complete | Turns rough tasks into structured goals. 19KB. Handles clarification questions. |
| **OpenAI Client** | `src/llm/openai_client.py` | ✅ Complete | Chat completions + embeddings, Tenacity retry, fallback model sequence, token tracking. |
| **Tool Definitions** | `src/llm/tools.py` | ✅ Complete | OpenAI function calling schemas (create_file, read_file, etc.). |
| **Token Counter** | `src/llm/token_counter.py` | ✅ Complete | tiktoken-based counting, cost estimation. |
| **Database Manager** | `src/memory/db_manager.py` | ✅ Complete | Full CRUD: tasks, iterations, failures, patterns, metrics, approvals. Connection pooling. 506 lines. |
| **Vector Store** | `src/memory/vector_store.py` | ✅ Complete | Embedding storage + cosine similarity for failures and patterns. 8.7KB. |
| **Failure Analyzer** | `src/memory/failure_analyzer.py` | ✅ Complete | Parses test output into structured errors, diagnoses, error signatures. 13KB. |
| **Pattern Matcher** | `src/memory/pattern_matcher.py` | ✅ Complete | Thin wrapper over VectorStore for pattern retrieval. |
| **Sandbox Manager** | `src/sandbox/sandbox_manager.py` | ✅ Complete | Dual-mode (Docker/subprocess). 11 language runtimes. Execution hooks integration. 673 lines. |
| **Docker Executor** | `src/sandbox/docker_executor.py` | ✅ Complete | Container lifecycle, resource limits, volume mounts. |
| **Safety Checker** | `src/sandbox/safety_checker.py` | ✅ Complete | AST scanning + Bandit SAST integration. |
| **Resource Limits** | `src/sandbox/resource_limits.py` | ✅ Complete | CPU, RAM, timeout dataclass. |
| **Circuit Breaker** | `src/utils/circuit_breaker.py` | ✅ Complete | Warning threshold + hard stop. |
| **Context Hygiene** | `src/utils/context_hygiene.py` | ✅ Complete | Token budget management, compaction, recency bias. 13KB. |
| **Execution Hooks** | `src/utils/execution_hooks.py` | ✅ Complete | Pre/post hooks for safety guardrails. 16KB. |
| **State Saver** | `src/utils/state_saver.py` | ✅ Complete | Checkpoint/resume to JSON. |
| **Metrics Collector** | `src/utils/metrics_collector.py` | ✅ Complete | Token usage + test pass rate recording. |
| **Logger** | `src/ui/logger.py` | ✅ Complete | structlog JSON logging. |
| **Progress** | `src/ui/progress.py` | ✅ Complete | Rich progress bars. |
| **Approval Prompt** | `src/ui/approval_prompt.py` | ✅ Complete | Interactive Y/N prompts. |
| **Project Scaffolder** | `src/projects/scaffolder.py` | ✅ Complete | Language-specific project setup (Python, Node, Java, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Elixir). 22KB. |
| **Config Loader** | `src/config_loader.py` | ✅ Complete | YAML loading with env var substitution. |
| **DB Schema** | `scripts/init_db.sql` | ✅ Complete | Tables: tasks, iterations, failures, patterns, metrics, approvals with pgvector. |
| **YAML Configs** | `config/*.yaml` | ✅ Complete | settings, database, openai, safety_rules, system_prompts, allowed_deps. |
| **Unit Tests** | `tests/` | ⚠️ Partial | 101 tests, **100 passing, 1 failing** (scaffolder case-insensitive language test). |
| **Documentation** | `docs/` | ✅ Complete | 10 architecture files, 10 agent docs, progressive disclosure from AGENTS.md. |

### ⚠️ Known Issues

1. **1 failing test**: `test_case_insensitive_language` in `test_scaffolder.py` — the scaffolder doesn't handle `"PYTHON"` as a language input.
2. **Sync-only codebase**: AGENTS.md requires "all agent methods and LLM calls must be async", but the entire codebase is **synchronous**. `BaseAgent.execute()` is `def execute()`, not `async def execute()`. `OpenAIClient.chat_completion()` is synchronous. The `Orchestrator.run()` is synchronous. There is **zero** `async def` usage in the source (only a string match in tester.py for parsing code).
3. **Architecture docs describe async API** (`async def execute()`, `async run()`) but the implementation is fully synchronous. The docs and code are misaligned.
4. **No end-to-end test coverage** — never been run against a real LLM + database.
5. **`--resume` CLI command** is documented in the handoff doc but not implemented in `main.py`.
6. **`--metrics` CLI command** is documented but not implemented.
7. **`--config` CLI command** is documented but not implemented.
8. **Coverage integration** — `src/testing/coverage_analyzer.py` exists but is not wired into the main loop (docstring says so explicitly).
9. **`REQUIRE_APPROVAL` hook result** — sandbox manager logs a warning but does not actually pause for user approval (comment says "In a full implementation, this would pause for user approval").

---

## Remaining Phases

### Phase 1: Stabilize & Fix (Priority: 🔴 Critical)

> **Goal**: Make the existing code actually runnable end-to-end.

#### 1.1 Fix the Failing Test

- [ ] Fix `test_case_insensitive_language` in `test_scaffolder.py` — scaffolder should normalize language input to lowercase before matching.

#### 1.2 Async Migration

- [ ] Convert `BaseAgent.execute()` to `async def execute()`
- [ ] Convert `OpenAIClient.chat_completion()` to async (use `openai.AsyncOpenAI`)
- [ ] Convert `OpenAIClient.create_embedding()` to async
- [ ] Convert `Orchestrator.run()` to `async def run()`
- [ ] Convert all orchestrator phase methods to async (`_execute_planning_phase`, etc.)
- [ ] Convert `DatabaseManager` to async (use `asyncpg` or `psycopg[async]` instead of `psycopg2`)
- [ ] Update `main.py` to use `asyncio.run()` for the CLI entry point
- [ ] Update all agent subclasses (`PlannerAgent`, `CoderAgent`, `TesterAgent`, `ReflectorAgent`, `CodeReviewerAgent`, `SecurityAuditorAgent`) to async
- [ ] Update all tests to use `pytest-asyncio`
- [ ] Update `requirements.txt` (add `asyncpg` or `psycopg[async]`, `pytest-asyncio` if not present)

> [!IMPORTANT]
> This is the single largest piece of tech debt. The AGENTS.md mandate and architecture docs both describe an async system, but nothing is async. This must be resolved before any real execution or new feature work.

#### 1.3 Documentation-Code Alignment

- [ ] Update `docs/agents/architecture.md` to reflect actual sync/async state post-migration
- [ ] Update code examples in `docs/agents/code-conventions.md` if patterns change

---

### Phase 2: End-to-End Verification (Priority: 🟠 High)

> **Goal**: Prove the core loop works against real infrastructure.

#### 2.1 Local Smoke Test

- [ ] Start PostgreSQL + pgvector (Docker Compose or local install)
- [ ] Run `scripts/setup_db.py` to initialize database
- [ ] Set up `.env` with a valid `OPENAI_API_KEY`
- [ ] Execute a simple task: `python -m src.main run --task "Write a function that reverses a string" --language python`
- [ ] Verify: task creates in DB, iterations record, code generates, tests run, success or meaningful failure
- [ ] Document any runtime errors and fix them

#### 2.2 Multi-Iteration Verification

- [ ] Execute a task complex enough to require >1 iteration (e.g., "Build a REST API with CRUD endpoints using Flask")
- [ ] Verify: reflector runs, failure stored in DB, vector search works, coder retries
- [ ] Verify: pattern stored on success

#### 2.3 Learning System Verification

- [ ] Run the same or similar task again
- [ ] Verify: planner retrieves stored pattern from first run
- [ ] Verify: fewer iterations needed (learning is working)

---

### Phase 3: Integration & E2E Tests (Priority: 🟠 High)

> **Goal**: Add the test coverage that's completely missing.

#### 3.1 Integration Tests (`tests/integration/`)

- [ ] `test_agent_interactions.py` — Test that agents pass context correctly through the orchestrator
- [ ] `test_database_operations.py` — Test full DB lifecycle (create task → iterations → failures → patterns) against a test database
- [ ] `test_vector_search.py` — Test embedding storage and cosine similarity retrieval (requires test DB with pgvector)
- [ ] `test_reprompter_flow.py` — Test task structuring end-to-end with mocked LLM

#### 3.2 End-to-End Tests (`tests/e2e/`)

- [ ] `test_simple_function.py` — Complete loop for "write a fibonacci function"
- [ ] `test_api_task.py` — Complete loop for "build a REST API"  
- [ ] `test_node_task.py` — Complete loop for "create a Node.js CLI tool"
- [ ] `test_failure_recovery.py` — Verify the system recovers from deliberate test failures
- [ ] `test_max_iterations.py` — Verify graceful failure after max iterations

#### 3.3 Test Infrastructure

- [ ] Create `conftest.py` fixtures for: test database, mocked OpenAI client, temporary workspaces
- [ ] Add `docker-compose.test.yml` for test database
- [ ] Add CI configuration (GitHub Actions) for automated test runs

---

### Phase 4: Missing CLI Commands & UX (Priority: 🟡 Medium)

> **Goal**: Implement the CLI commands that are documented but not built.

#### 4.1 `--resume` Command

- [ ] Add `resume` command to `main.py` CLI
- [ ] Load checkpoint from `StateSaver` or database
- [ ] Reconstruct `Orchestrator` state from checkpoint
- [ ] Resume execution from the saved iteration/state

#### 4.2 `--metrics` Command

- [ ] Add `metrics` command to display performance metrics dashboard
- [ ] Query metrics table for: success rate, average iterations, token usage, duration
- [ ] Render with Rich tables/panels

#### 4.3 Approval System Integration

- [ ] Wire up `REQUIRE_APPROVAL` hook result to actually pause and prompt the user
- [ ] Integrate `approval_prompt.py` with `sandbox_manager.py`
- [ ] Store approval decisions in the `approvals` table

#### 4.4 Coverage Integration

- [ ] Wire `coverage_analyzer.py` into the tester agent output
- [ ] Report coverage results in the CLI output
- [ ] Store coverage metrics in the metrics table

---

### Phase 5: Hardening & Production Readiness (Priority: 🟡 Medium)

> **Goal**: Make the system robust enough for daily use.

#### 5.1 Error Handling & Recovery

- [ ] Add graceful handling for OpenAI API outages mid-loop
- [ ] Add handling for database connection drops
- [ ] Add workspace cleanup on failure (don't leak temp directories)
- [ ] Add proper signal handling (Ctrl+C gracefully saves checkpoint)

#### 5.2 Configuration Validation

- [ ] Add YAML schema validation on startup (fail fast with helpful errors)
- [ ] Validate `OPENAI_API_KEY` is set before attempting any run
- [ ] Validate database connectivity before starting a task

#### 5.3 Observability

- [ ] Add structured log aggregation guidance (ELK, Loki)
- [ ] Add optional Prometheus metrics endpoint
- [ ] Add task duration tracking and reporting

#### 5.4 CI/CD Pipeline

- [ ] GitHub Actions workflow for: lint (black, isort, flake8), type check (mypy), unit tests
- [ ] Pre-commit hooks configuration
- [ ] Automated release process

---

### Phase 6: Advanced Features (Priority: 🟢 Low / Future)

> **Goal**: Stretch features for v1.0+.

#### 6.1 Parallel Execution

- [ ] Run independent subtasks concurrently (asyncio.gather)
- [ ] Track parallel iteration state

#### 6.2 Multi-File Refactoring

- [ ] Enhanced coder agent that understands project-wide changes
- [ ] Dependency graph analysis for change impact

#### 6.3 Web Dashboard

- [ ] FastAPI backend exposing task/metrics data
- [ ] React/HTML dashboard for monitoring active and historical tasks

#### 6.4 Cost Optimization

- [ ] Model routing based on task complexity (GPT-3.5 for simple, GPT-4 for complex)
- [ ] Budget tracking and alerts per task
- [ ] Token usage analytics

#### 6.5 Collaborative Learning

- [ ] Export/import pattern databases
- [ ] Share patterns across agent instances
- [ ] Pre-seeded pattern library for common tasks

#### 6.6 Additional LLM Providers

- [ ] Anthropic Claude support via litellm
- [ ] Local model support (Ollama)
- [ ] Provider abstraction layer

---

## Recommended Next Action

**Start with Phase 1.1 (fix the failing test)** — it's a 5-minute fix and gets the test suite to 100%.

**Then tackle Phase 1.2 (async migration)** — this is the largest and most impactful change. The entire architecture is designed for async but implemented synchronously. Until this is resolved, the codebase contradicts its own AGENTS.md and architecture docs. This will touch every file in `src/` and every test.

**After that, Phase 2 (end-to-end verification)** will quickly reveal any remaining integration bugs when the system runs against real OpenAI and PostgreSQL.

---

## Metrics Snapshot

| Metric | Value |
|--------|-------|
| **Source files** | 32 Python files in `src/` |
| **Lines of code** | ~5,000 lines (core system) |
| **Test files** | 7 test files |
| **Tests** | 101 total, 100 passing, 1 failing |
| **Configuration files** | 6 YAML/JSON files |
| **Documentation files** | 20+ markdown files |
| **Languages supported** | 11 (Python, Node, Java, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Elixir) |
| **Async compliance** | ❌ 0% (all sync, docs say async) |
| **Integration test coverage** | ❌ 0% |
| **E2E test coverage** | ❌ 0% |
| **Has been run end-to-end** | ❌ Unknown/unlikely |
