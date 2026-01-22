# Getting Started

Quick guide to set up and start working on the Miracle autonomous coding agent.

---

## First-Time Setup

### Prerequisites

**Required:**
- Python 3.11+
- PostgreSQL 14+ (Can be via Docker or local installation)
- OpenAI API key
- Docker and Docker Compose (Optional, for sandboxed execution)

**Optional:**
- Docker and Docker Compose (for sandboxed code execution)

### Installation

```bash
# Navigate to project
cd /path/to/autonomous_agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add:
#   OPENAI_API_KEY=your_key_here
#   DB_PASSWORD=your_password_here
```

### Database Setup

**Option 1: Docker (recommended for development)**
```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Initialize database
python scripts/setup_db.py
```

**Option 2: Local PostgreSQL**
```bash
# Install PostgreSQL with pgvector extension
# On macOS: brew install postgresql pgvector
# On Ubuntu: apt-get install postgresql postgresql-contrib
# Then: CREATE EXTENSION vector;

# Configure connection in .env
# DB_HOST=localhost
# DB_PORT=5432

# Initialize database
python scripts/setup_db.py
```

**Option 3: Hosted PostgreSQL**
```bash
# Use any PostgreSQL provider with pgvector support:
# - Supabase, Neon, or managed cloud providers
# - Update connection details in .env

# Initialize database
python scripts/setup_db.py
```

### Verify Installation

```bash
pytest tests/ -v
```

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

## Running the System

### Start a New Task (Supports Any Language)

```bash
python -m src.main run \
    --task "Build a REST API for todo items with SQLite" \
    --language python
```

### Resume a Task

```bash
python -m src.main --resume <task_id>
```

### View History

```bash
python -m src.main --history
```

### View Metrics

```bash
python -m src.main --metrics
```

---

## Configuration Files

All system behavior is controlled via YAML (not code):

| File | Purpose |
|------|---------|
| `config/settings.yaml` | System settings (max_iterations, checkpoint_frequency, log_level) |
| `config/openai.yaml` | LLM models per agent, parameters, fallback sequence |
| `config/database.yaml` | PostgreSQL connection and pool settings |
| `config/system_prompts.yaml` | Agent system prompts |
| `config/allowed_deps.json` | Dependency allowlist |
| `config/safety_rules.yaml` | AST patterns to block, approval triggers |

---

## Quick Verification

After setup, verify everything works:

```bash
# Check database connection
python -c "from src.memory.db_manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().test_connection())"

# Check OpenAI API
python -c "from src.llm.openai_client import OpenAIClient; import asyncio; asyncio.run(OpenAIClient().test_connection())"

# Check Docker (Optional)
docker ps

# Run minimal test suite
pytest tests/unit/ -v
```

---

## Development Workflow

1. **Make changes** to code
2. **Run tests**: `pytest tests/ -v`
3. **Format**: `black src/ tests/`
4. **Sort imports**: `isort src/ tests/`
5. **Type check**: `mypy src/`
6. **Lint**: `flake8 src/ tests/`
7. **Commit** when all checks pass

---

## Troubleshooting

### Database Connection Failed

**If using Docker:**
```bash
# Check PostgreSQL is running
docker-compose ps

# Restart database
docker-compose down
docker-compose up -d postgres

# Re-initialize
python scripts/setup_db.py
```

**If using local PostgreSQL:**
```bash
# Check PostgreSQL status
pg_isready

# Check connection settings in .env
# Verify DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

# Re-initialize
python scripts/setup_db.py
```

### OpenAI API Errors
- Verify `OPENAI_API_KEY` in `.env`
- Check API rate limits at platform.openai.com
- Try fallback model in `config/openai.yaml`

### Docker Sandbox Issues (If using Docker)
```bash
# Check Docker daemon
docker info

# Rebuild sandbox image
docker build -f Dockerfile.sandbox -t python-sandbox .
```

**If Docker not available:**
- Configure sandbox to use subprocess execution
- Update `config/settings.yaml`: `sandbox.use_docker: false`
- Note: Subprocess has fewer security guarantees

---

## Next Steps

- **For implementation tasks**: See [Development Workflows](development-workflows.md)
- **For architecture understanding**: See [Architecture](architecture.md)
- **For code patterns**: See [Code Conventions](code-conventions.md)
