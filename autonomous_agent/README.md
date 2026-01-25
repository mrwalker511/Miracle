# Autonomous Coding Agent

An AI agent that writes code iteratively until tests pass, learning from failures using vector similarity.

**"The difference between a chatbot and an agent is the loop."**

---

## How It Works

```
PLANNING → CODING → [REVIEW] → [AUDIT] → TESTING
    ↑                                       |
    └────────────── REFLECTING ─────────────┘
```

1. **Planning** - Breaks down your task, queries past patterns
2. **Coding** - Writes code using LLM with file tools
3. **Review** - (Optional) Checks code quality before testing
4. **Audit** - (Optional) Scans for security vulnerabilities
5. **Testing** - Generates and runs tests
6. **Reflecting** - If tests fail, analyzes errors and loops back

The agent continues until tests pass or max iterations reached.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### Installation

```bash
cd autonomous_agent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and DB_PASSWORD

# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Initialize database
python scripts/setup_db.py
```

### Run a Task

```bash
# Basic
python -m src.main run --task "Build a REST API for managing todo items"

# With code review
python -m src.main run --task "..." --enable-review

# With security audit
python -m src.main run --task "..." --enable-audit

# Both (recommended for production code)
python -m src.main run --task "..." --enable-review --enable-audit

# Interactive mode
python -m src.main run
```

---

## CLI Reference

```
python -m src.main run [OPTIONS]

Options:
  -t, --task TEXT           Task description
  -l, --language TEXT       Language: python (default) or node
  -p, --problem-type TEXT   Hint: web_app, cli_tool, data_pipeline, etc.
  -m, --max-iterations INT  Max attempts (default: 15)
  -w, --workspace PATH      Working directory
  --enable-review           Run code review before testing
  --enable-audit            Run security audit before testing
  --skip-reprompter         Use task as-is without structuring

Other commands:
  python -m src.main history   # View past tasks
  python -m src.main setup     # Show setup instructions
```

---

## Working with Your Own Projects

**Important:** The agent modifies files in-place. Always commit your work first.

```bash
# Point to your project
python -m src.main run --workspace "/path/to/your/project" --task "..."
```

Or set a default in `config/settings.yaml`:

```yaml
sandbox:
  workspace_root: "/path/to/your/project"
```

**Tips:**
- Be specific: "Fix the TypeError in src/utils.py line 45"
- Reference files: "Use the database wrapper in lib/db.js"
- Commit before running so you can `git checkout .` to undo

---

## Configuration

### `config/settings.yaml`

```yaml
orchestrator:
  max_iterations: 15
  circuit_breaker:
    warning_threshold: 12    # Warn user
    hard_stop: 15            # Force stop

context_hygiene:
  max_tokens: 128000         # Model context limit
  warning_threshold: 0.50    # Start monitoring at 50%
  critical_threshold: 0.75   # Compress context at 75%

execution_hooks:
  enabled: true
  hooks:
    block_dangerous_commands:
      enabled: true          # Blocks rm -rf, sudo, etc.
    protect_sensitive_files:
      enabled: true          # Guards .env, credentials
    iteration_guard:
      enabled: true
      max_same_error: 3      # Warn if same error repeats

sandbox:
  engine: "docker"           # or "local"
  workspace_root: "./sandbox/workspace"
  resource_limits:
    memory_mb: 1024
    execution_timeout: 300
```

### `config/openai.yaml`

```yaml
models:
  planner: "gpt-4-turbo-preview"
  coder: "gpt-4-turbo-preview"
  tester: "gpt-4-turbo-preview"
  reflector: "gpt-4-turbo-preview"
  embedding: "text-embedding-3-large"
```

---

## What the Agent Does

### Task Structuring
When you submit a task, the agent analyzes it and may ask clarifying questions to ensure it understands what you want. Skip with `--skip-reprompter` for specific tasks.

### Memory Management
Long tasks fill up context. The agent automatically compresses old data while preserving your goal, current plan, recent errors, and latest code.

### Safety Guardrails
Commands are validated before execution:
- Dangerous commands blocked (`rm -rf /`, `sudo`, etc.)
- Sensitive files protected (`.env`, credentials, SSH keys)
- Repeated errors detected (warns if stuck in a loop)

### Code Review (--enable-review)
Before testing, reviews code for:
- Logic errors and bugs
- Style and readability issues
- Performance problems
- Maintainability concerns

### Security Audit (--enable-audit)
Scans for OWASP vulnerabilities:
- SQL/Command injection
- Hardcoded secrets
- Path traversal
- Weak cryptography

### Learning from Failures
Every failure is stored with a vector embedding. When similar errors occur, the agent retrieves past solutions to inform fixes. Successful patterns are saved for future tasks.

---

## Project Structure

```
autonomous_agent/
├── config/
│   ├── settings.yaml       # System configuration
│   ├── database.yaml       # PostgreSQL settings
│   ├── openai.yaml         # Model configuration
│   ├── system_prompts.yaml # Agent prompts
│   └── allowed_deps.json   # Approved dependencies
├── src/
│   ├── main.py             # CLI entry point
│   ├── orchestrator.py     # State machine controller
│   ├── agents/
│   │   ├── planner.py      # Task decomposition
│   │   ├── coder.py        # Code generation
│   │   ├── tester.py       # Test execution
│   │   ├── reflector.py    # Error analysis
│   │   ├── code_reviewer.py    # Quality checks
│   │   └── security_auditor.py # Vulnerability scanning
│   ├── llm/                # OpenAI integration
│   ├── memory/             # PostgreSQL + pgvector
│   ├── sandbox/            # Code execution
│   └── utils/              # Helpers
├── scripts/
│   ├── setup_db.py         # Database initialization
│   └── init_db.sql         # Schema
├── tests/                  # Unit tests
├── logs/                   # JSON logs
└── docker-compose.yml      # PostgreSQL + pgvector
```

---

## Troubleshooting

| Message | Meaning | Action |
|---------|---------|--------|
| "Context compaction triggered" | Memory was getting full | Normal - old data compressed |
| "Command blocked by safety hook" | Dangerous command stopped | Agent will try another approach |
| "Code review found critical issues" | Bugs detected | Agent will fix in next iteration |
| "Circuit breaker triggered" | Max iterations reached | Task paused - may need manual help |
| "Same error repeated X times" | Stuck in a loop | Consider breaking task into smaller pieces |

### Logs

Structured JSON logs in `logs/agent.log`:

```json
{
  "timestamp": "2025-01-25T10:30:45Z",
  "level": "INFO",
  "task_id": "abc-123",
  "iteration": 3,
  "phase": "testing",
  "event": "test_execution_complete",
  "data": {"passed": 8, "failed": 2}
}
```

---

## Examples

### REST API
```bash
python -m src.main run \
  --task "Create a Flask REST API for managing books with SQLite" \
  --language python \
  --enable-review
```

### CLI Tool
```bash
python -m src.main run \
  --task "Build a CLI tool for converting CSV to JSON" \
  --language python
```

### Node.js
```bash
python -m src.main run \
  --task "Create an Express API with user authentication" \
  --language node \
  --enable-audit
```

### Bug Fix
```bash
python -m src.main run \
  --workspace "/path/to/project" \
  --task "Fix the null pointer exception in handlers.py line 142" \
  --skip-reprompter
```

---

## Limitations

- **Languages:** Python and Node.js
- **Testing:** pytest (Python), node:test (Node.js)
- **Dependencies:** Manual approval required
- **Sandbox:** Docker recommended for isolation

---

## License

MIT License - See LICENSE file.

---

**Remember: "The difference between a chatbot and an agent is the loop."**
