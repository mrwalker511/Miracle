# Architecture

Miracle is an autonomous coding agent that writes code, runs tests, and
iterates until the tests pass — up to 15 times. Its unique feature is
**cross-session memory**: every failure is stored in PostgreSQL + pgvector so
the agent learns from past mistakes across completely separate runs.

---

## Folder map

```
autonomous_agent/
├── src/
│   ├── main.py              # CLI entry point (commands: run, history, setup)
│   ├── orchestrator.py      # State machine — drives the agent loop
│   ├── config_loader.py     # Loads YAML config + .env
│   │
│   ├── preprocessing/       # Runs ONCE before the loop starts
│   │   └── reprompter.py    # Turns a rough task into a structured goal
│   │
│   ├── agents/              # Core loop agents (always active)
│   │   ├── base_agent.py    # Abstract base: execute(context) → dict
│   │   ├── planner.py       # Breaks the task into a plan
│   │   ├── coder.py         # Writes code files
│   │   ├── tester.py        # Generates and runs tests
│   │   ├── reflector.py     # Analyses failures, proposes fixes
│   │   └── optional/        # Flag-enabled phases (not in the core loop)
│   │       ├── code_reviewer.py     # --enable-review
│   │       └── security_auditor.py  # --enable-audit
│   │
│   ├── memory/              # The learning system — what makes Miracle unique
│   │   ├── db_manager.py    # PostgreSQL CRUD: tasks, iterations, metrics
│   │   ├── vector_store.py  # pgvector: store + search failures and patterns
│   │   ├── failure_analyzer.py  # Parses test output into structured errors
│   │   └── pattern_matcher.py   # Finds successful templates for similar tasks
│   │
│   ├── sandbox/             # Runs generated code safely
│   │   ├── sandbox_manager.py   # Chooses Docker or subprocess, returns results
│   │   ├── docker_executor.py   # Container lifecycle + resource limits
│   │   └── safety_checker.py    # AST + Bandit static analysis before execution
│   │
│   ├── llm/                 # All OpenAI API calls live here
│   │   ├── openai_client.py # chat_completion with retry/backoff
│   │   └── token_counter.py # tiktoken-based counting for context hygiene
│   │
│   ├── utils/               # Infrastructure (not business logic)
│   │   ├── circuit_breaker.py   # Hard stop at max iterations
│   │   ├── context_hygiene.py   # Token budget management + compaction
│   │   ├── execution_hooks.py   # Safety guardrails per iteration
│   │   └── state_saver.py       # Checkpoint/resume every 5 iterations
│   │
│   └── ui/                  # Terminal output
│       ├── logger.py        # Structured JSON logging (structlog)
│       └── progress.py      # Rich progress bars
│
├── config/                  # YAML configuration files
│   ├── settings.yaml        # Orchestrator, sandbox, hooks, logging
│   ├── openai.yaml          # Model names per agent
│   ├── database.yaml        # PostgreSQL connection
│   ├── safety_rules.yaml    # Blocked commands, protected files
│   └── system_prompts.yaml  # LLM prompts for each agent
│
├── tests/                   # pytest test suite (101 tests)
└── scripts/
    └── setup_db.py          # Creates tables and pgvector indexes
```

---

## Core loop

```
User types a task
        │
        ▼
preprocessing/reprompter.py
  Asks the LLM to extract: goal, language, constraints, acceptance criteria.
  Optionally asks the user clarifying questions. Runs once, before the loop.
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Orchestrator loop  (max 15 iterations)             │
│                                                     │
│  PLANNING   planner.py      Decomposes the task     │
│      │                      into a step-by-step     │
│      │                      plan with subtasks      │
│      ▼                                              │
│  CODING     coder.py        Writes code files to    │
│      │                      the sandbox workspace   │
│      │                                              │
│      │  [optional phases — only if flags enabled]   │
│      │  code_reviewer.py    Quality check           │
│      │  security_auditor.py OWASP vulnerability     │
│      ▼                      scan                    │
│  TESTING    tester.py       Generates a test file,  │
│      │                      runs it in Docker       │
│      │                                              │
│  ┌───┴─── pass ──▶  SUCCESS                         │
│  │                  Stores code pattern in pgvector │
│  │                                                  │
│  └─── fail ──▶  REFLECTING  reflector.py            │
│                  Queries pgvector for similar past  │
│                  failures. Proposes a fix.          │
│                  Loops back to CODING               │
└─────────────────────────────────────────────────────┘
```

---

## How the memory system works

Every failure and every success is embedded and stored in pgvector.

| Event | What gets stored | Used by |
|---|---|---|
| Test fails | Error signature + stack trace + code context | Reflector: finds similar past failures to inform the fix |
| Task succeeds | Working code + test template | Planner: retrieves similar patterns for new tasks |

This is why Miracle gets better over time: the second time it sees a
`ModuleNotFoundError` in a similar context, it already knows what fixed it last
time.

**Requires:** PostgreSQL 14+ with the `pgvector` extension.

---

## Quick start

```bash
# 1. Configure
cp autonomous_agent/.env.example autonomous_agent/.env
# Edit .env: add OPENAI_API_KEY, DB_PASSWORD

# 2. Start the database
docker compose up -d

# 3. Create tables and pgvector indexes
python autonomous_agent/scripts/setup_db.py

# 4. Run a task
cd autonomous_agent
python -m src.main run --task "write a function that reverses a string"

# With optional phases
python -m src.main run --task "build a REST API" --enable-review --enable-audit
```

---

## Running tests

```bash
cd autonomous_agent
pip install -r requirements.txt
python -m pytest tests/ -v
```

The test suite runs without any infrastructure (no database or OpenAI key
needed) — all external dependencies are mocked.

---

## How to add a new core agent

1. Create `src/agents/my_agent.py` inheriting from `BaseAgent`:
   ```python
   from src.agents.base_agent import BaseAgent

   class MyAgent(BaseAgent):
       def execute(self, context: dict) -> dict:
           result = self.call_llm(self.build_messages("..."))
           return {'my_output': self.extract_text_response(result)}
   ```

2. Register it in `src/agents/__init__.py`:
   ```python
   from src.agents.my_agent import MyAgent
   AGENT_REGISTRY['my_agent'] = MyAgent
   ```

3. Add a state to `OrchestrationState` in `src/orchestrator.py` and a
   transition branch in the `run()` loop.

4. Write tests in `tests/test_orchestrator_loop.py` — mock the agent and
   verify context flows correctly.

---

## How to add an optional phase

Optional phases run after `CODING` and before `TESTING`. They don't need a
new state in the enum.

1. Create `src/agents/optional/my_phase.py` (inherits `BaseAgent`).
2. Add a CLI flag in `src/main.py` and pass it to `Orchestrator.__init__`.
3. In `Orchestrator.__init__`, instantiate the agent and append
   `self._execute_my_phase` to `self.optional_phases`.
4. Add `_execute_my_phase(self, iteration_id)` following the same pattern
   as `_execute_review_phase`.
