# DEPENDENCIES.md

> **Purpose**: Dependency management, setup, and configuration guide.

---

## System Requirements

### Minimum Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **OS** | Linux, macOS, Windows (WSL2) | Windows native not fully supported |
| **Python** | 3.11+ | 3.12 recommended |
| **Docker** | 20.10+ | For code sandboxing |
| **PostgreSQL** | 14+ | With pgvector extension |
| **RAM** | 4GB | 8GB recommended |
| **Disk** | 10GB free | For Docker images and workspaces |
| **Internet** | Stable | For OpenAI API calls |

### Recommended (Production)

| Component | Requirement |
|-----------|-------------|
| **OS** | Ubuntu 22.04 LTS |
| **Python** | 3.12 |
| **Docker** | 24.0+ |
| **PostgreSQL** | 16 (pgvector 0.5+) |
| **RAM** | 16GB |
| **Disk** | 50GB+ |
| **CPU** | 4+ cores |

### External Services

| Service | Required | Purpose | Cost |
|----------|-----------|---------|------|
| **OpenAI API** | Yes | LLM, embeddings | Pay-per-use |
| **PostgreSQL** | Yes | Self-hosted (Docker) | Free |
| **Docker Hub** | Yes | Pull base images | Free |

---

## Installation Guide

### Quick Start

```bash
# Clone repository
git clone <repo-url>
cd autonomous_agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add OPENAI_API_KEY and DB_PASSWORD

# Start PostgreSQL
docker-compose up -d postgres

# Initialize database
python scripts/setup_db.py

# Run tests
pytest tests/ -v

# Run agent
python -m src.main run
```

### Step-by-Step

**1. System Dependencies**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv docker.io docker-compose postgresql-client

# macOS
brew install python@3.11 docker docker-compose

# Windows (WSL2)
# Install Docker Desktop for Windows
# Install Python 3.11 from python.org
```

**2. Python Setup**
```bash
# Verify Python version
python --version  # Should be 3.11+

# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

**3. Install Python Packages**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**4. Environment Variables**
```bash
# Copy example
cp .env.example .env

# Edit .env with your values:
# OPENAI_API_KEY=sk-...
# DB_PASSWORD=your_secure_password
# LOG_LEVEL=info
```

**5. Start PostgreSQL**
```bash
# Start Docker containers
docker-compose up -d postgres

# Wait for startup (10-30 seconds)
# Check logs
docker-compose logs postgres

# Verify connection
docker exec -it autonomous-agent-postgres-1 psql -U agent_user -d autonomous_agent -c "SELECT version();"
```

**6. Initialize Database**
```bash
python scripts/setup_db.py
# This runs init_db.sql to create tables and indexes
```

**7. Verify Installation**
```bash
# Run tests
pytest tests/ -v

# Start CLI
python -m src.main --help

# Should see commands: run, history, resume, etc.
```

---

## Python Dependencies

### Core Dependencies

**requirements.txt**:
```txt
# Core
python-dotenv==1.0.0
pyyaml==6.0.1

# OpenAI (flexible model support)
openai==1.12.0

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.25
pgvector==0.2.4

# Testing
pytest==8.0.0
pytest-cov==4.1.0
pytest-timeout==2.2.0
hypothesis==6.98.0

# Code analysis
bandit==1.7.6
pylint==3.0.3

# Docker
docker==7.0.0

# CLI & UI
click==8.1.7
rich==13.7.0
prompt-toolkit==3.0.43

# Logging
structlog==24.1.0
python-json-logger==2.0.7

# Utilities
tenacity==8.2.3
tiktoken==0.6.0
```

### Dependency Categories

| Category | Packages | Purpose |
|----------|-----------|---------|
| **Core** | python-dotenv, pyyaml | Config loading |
| **LLM** | openai, tenacity, tiktoken | OpenAI API, retry, tokens |
| **Database** | psycopg2, sqlalchemy, pgvector | PostgreSQL + vectors |
| **Testing** | pytest, hypothesis | Test framework |
| **Security** | bandit | SAST scanning |
| **Sandbox** | docker | Container management |
| **CLI** | click, rich | Terminal interface |
| **Logging** | structlog | Structured JSON logs |

### Version Management

- All packages pinned to exact versions
- Use `pip-compile` (pip-tools) to update:
  ```bash
  pip install pip-tools
  pip-compile requirements.in
  ```

### Adding New Dependencies

1. Add to `requirements.txt`
2. Update `requirements.in` (if using pip-tools)
3. Install: `pip install -r requirements.txt`
4. Add to Dockerfile if needed
5. Update documentation

---

## Configuration Management

### Configuration Files

**settings.yaml** - System settings:
```yaml
orchestrator:
  max_iterations: 15
  checkpoint_frequency: 5
  circuit_breaker_warning: 12
  circuit_breaker_stop: 15

logging:
  level: info
  format: json
  file: logs/autonomous_agent.log

sandbox:
  cpu_limit: 1
  memory_limit: 1g
  timeout: 300  # seconds
```

**openai.yaml** - LLM configuration:
```yaml
models:
  planner: "gpt-4-turbo-preview"
  coder: "gpt-4-turbo-preview"
  tester: "gpt-4-turbo-preview"
  reflector: "gpt-4-turbo-preview"
  embedding: "text-embedding-3-large"

fallback_sequence:
  - "gpt-4-turbo-preview"
  - "gpt-4"
  - "gpt-3.5-turbo"

parameters:
  temperature: 0.2
  max_tokens: 4096
  top_p: 1.0
```

**database.yaml** - Database connection:
```yaml
host: localhost
port: 5432
name: autonomous_agent
user: agent_user
password: ${DB_PASSWORD}  # From .env

pool_size: 10
max_overflow: 20
pool_timeout: 30

pgvector:
  dimension: 1536
  index_lists: 100
```

**safety_rules.yaml** - Safety configuration:
```yaml
blocked_imports:
  - os
  - subprocess
  - pty
  - socket
  - sys
  - __builtin__

blocked_functions:
  - eval
  - exec
  - compile

approval_required:
  - requests
  - urllib
  - httpx
  - subprocess.run
```

**allowed_deps.json** - Dependency allowlist:
```json
{
  "approved": [
    {"name": "flask", "max_version": "3.0.0"},
    {"name": "requests", "max_version": "2.31.0"},
    {"name": "numpy", "max_version": "1.26.0"}
  ],
  "blocked": [
    "eval", "exec", "__import__"
  ]
}
```

### Environment Variables

**Required**:
- `OPENAI_API_KEY` - OpenAI API key
- `DB_PASSWORD` - PostgreSQL password

**Optional**:
- `LOG_LEVEL` - debug, info, warning, error (default: info)
- `MAX_ITERATIONS` - Override default max iterations
- `SANDBOX_TIMEOUT` - Override default timeout (seconds)

### Loading Configuration

Configuration loading in `src/config_loader.py`:
1. Load YAML files from `config/` directory
2. Substitute environment variables (`${VAR_NAME}`)
3. Validate required fields present
4. Merge with defaults

---

## Database Setup

### PostgreSQL with pgvector

**docker-compose.yml**:
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: autonomous_agent
      POSTGRES_USER: agent_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent_user"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Initializing Database

**scripts/init_db.sql**:
- Enable pgvector extension
- Create tables (tasks, iterations, failures, patterns, metrics, approvals)
- Create indexes (B-tree for standard columns, IVFFlat for vectors)
- Create views (success_rate_by_type, recent_failures)

**Run initialization**:
```bash
# Via setup script
python scripts/setup_db.py

# Manually
psql -h localhost -U agent_user -d autonomous_agent -f scripts/init_db.sql
```

### Connecting to Database

**Python** (via sqlalchemy):
```python
from src.memory.db_manager import DatabaseManager

db_manager = DatabaseManager(config)
async with db_manager.get_connection() as conn:
    await conn.execute("SELECT * FROM tasks")
```

**psql CLI**:
```bash
# Connect
psql -h localhost -U agent_user -d autonomous_agent

# Useful commands
\dt                    # List tables
\d tasks                # Describe table
SELECT COUNT(*) FROM tasks;
```

### Database Maintenance

**Backup**:
```bash
# Full backup
pg_dump -h localhost -U agent_user autonomous_agent > backup.sql

# Backup specific table
pg_dump -h localhost -U agent_user -t patterns autonomous_agent > patterns.sql
```

**Restore**:
```bash
psql -h localhost -U agent_user autonomous_agent < backup.sql
```

**Cleanup old data**:
```sql
-- Delete tasks older than 30 days
DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '30 days';

-- Clean up orphaned records
DELETE FROM iterations WHERE task_id NOT IN (SELECT task_id FROM tasks);
```

---

## Docker Setup

### Docker Installation

**Linux**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in
```

**macOS**:
```bash
brew install --cask docker
# Open Docker Desktop app
```

**Windows**:
- Download Docker Desktop from docker.com
- Enable WSL2 backend in settings

### Verifying Installation

```bash
docker --version      # Should be 20.10+
docker-compose --version
docker info
```

### Docker Images

**PostgreSQL**:
```bash
# Pull image
docker pull pgvector/pgvector:pg15

# Run standalone
docker run -d \
  --name my-postgres \
  -e POSTGRES_DB=autonomous_agent \
  -e POSTGRES_USER=agent_user \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

**Sandbox** (Dockerfile.sandbox):
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 sandbox_user

WORKDIR /workspace
USER sandbox_user

CMD ["/bin/bash"]
```

Build:
```bash
docker build -f Dockerfile.sandbox -t python-sandbox .
```

### Docker Compose

**Start all services**:
```bash
docker-compose up -d
```

**View logs**:
```bash
docker-compose logs -f
```

**Stop services**:
```bash
docker-compose down
```

**Restart specific service**:
```bash
docker-compose restart postgres
```

---

## Dependency Approval System

### Allowlist Approach

All dependencies must be pre-approved in `config/allowed_deps.json`:
```json
{
  "approved": [
    {"name": "flask", "max_version": "3.0.0"},
    {"name": "requests", "max_version": "2.31.0"}
  ]
}
```

### Approval Flow

1. Coder agent generates code with dependencies
2. Check against allowlist
3. If not approved:
   - Block installation
   - Prompt user: "Install dependency: X (version Y)? [Y/n]"
   - Store decision in `approvals` table
4. If user approves: Add to allowlist or install manually

### Adding New Dependencies

**Option 1: Manual addition**:
```bash
# Edit config/allowed_deps.json
# Add dependency
# Restart agent
```

**Option 2: Via CLI approval**:
- Agent requests dependency
- User approves
- Dependency added to temporary allowlist for task
- Optionally persist to global allowlist

### Blocked Dependencies

Never allow (hardcoded in safety_checker.py):
- `eval`, `exec`, `__import__` (built-ins)
- `os`, `subprocess`, `pty`, `socket` (dangerous modules)

---

## Troubleshooting

### Common Issues

**PostgreSQL connection failed**:
```bash
# Check if running
docker ps | grep postgres

# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres

# Verify connection
psql -h localhost -U agent_user -d autonomous_agent -c "SELECT 1"
```

**Docker permission denied**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

**OpenAI API rate limit**:
- Check usage at https://platform.openai.com/usage
- Wait for quota reset or upgrade plan
- Configure fallback models in `config/openai.yaml`

**pgvector extension not found**:
```sql
-- Connect to database
psql -h localhost -U agent_user -d autonomous_agent

-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

**Python import errors**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check virtual environment activated
which python  # Should point to venv
```

**Container spawn failed**:
- Check Docker daemon: `docker info`
- Check disk space: `df -h`
- Check logs: `docker-compose logs`

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=debug
python -m src.main run
```

Or set in `config/settings.yaml`:
```yaml
logging:
  level: debug
```

### Health Checks

**Check all services**:
```bash
# PostgreSQL
docker-compose ps postgres

# OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Database connection
python -c "from src.memory.db_manager import DatabaseManager; print('OK')"
```

---

## Upgrading

### Upgrading Python Dependencies

```bash
# Update single package
pip install --upgrade openai

# Update all
pip install --upgrade -r requirements.txt

# Check for vulnerabilities
pip-audit
```

### Upgrading PostgreSQL

```bash
# Stop container
docker-compose stop postgres

# Backup database
docker-compose exec postgres pg_dump -U agent_user autonomous_agent > backup.sql

# Pull new image
docker pull pgvector/pgvector:pg16

# Update docker-compose.yml image version
# Restart
docker-compose up -d postgres

# Restore backup if needed
docker-compose exec -T postgres psql -U agent_user autonomous_agent < backup.sql
```

### Database Migrations

**Create migration script**:
```bash
# scripts/migrate_db_v2.py
# Apply schema changes
# Migrate data if needed
```

**Run migration**:
```bash
python scripts/migrate_db_v2.py
```

**Best practices**:
1. Backup before migration
2. Test migration on staging database
3. Rollback script prepared
4. Atomic migrations (all or nothing)

---

## Development Dependencies

For development/testing:

**requirements-dev.txt**:
```txt
# Additional testing
pytest-mock==3.12.0
pytest-xdist==3.5.0  # Parallel tests

# Code quality
black==24.1.0
isort==5.13.0
mypy==1.8.0
flake8==7.0.0

# Documentation
sphinx==7.2.0
sphinx-rtd-theme==2.0.0

# Development
ipython==8.20.0
ipdb==0.13.13
```

Install:
```bash
pip install -r requirements-dev.txt
```

---

**Last Updated**: 2025-01-21
**Purpose**: Dependency and setup documentation for developers
