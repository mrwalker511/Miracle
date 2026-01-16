# DEPENDENCIES.md

> **Purpose**: Comprehensive guide for dependency management, setup, configuration, and operational requirements for the Autonomous Coding Agent system.

---

## 📑 Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Guide](#installation-guide)
3. [Python Dependencies](#python-dependencies)
4. [Configuration Management](#configuration-management)
5. [Database Setup](#database-setup)
6. [Docker Setup](#docker-setup)
7. [Dependency Approval System](#dependency-approval-system)
8. [Environment Variables](#environment-variables)
9. [Troubleshooting](#troubleshooting)
10. [Upgrading](#upgrading)

---

## 1. System Requirements

### 1.1 Minimum Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Operating System** | Linux, macOS, Windows (WSL2) | Windows native not fully supported |
| **Python** | 3.11 or higher | 3.12 recommended |
| **Docker** | 20.10 or higher | For code sandboxing |
| **PostgreSQL** | 14 or higher | With pgvector extension |
| **RAM** | 4GB | 8GB recommended |
| **Disk Space** | 10GB free | For Docker images and workspaces |
| **Internet** | Stable connection | For OpenAI API calls |

### 1.2 Recommended Requirements (Production)

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Operating System** | Ubuntu 22.04 LTS | Or similar Linux distribution |
| **Python** | 3.12 | Latest stable version |
| **Docker** | 24.0 or higher | Latest stable version |
| **PostgreSQL** | 16 | Latest stable with pgvector 0.5+ |
| **RAM** | 16GB | For parallel task execution |
| **Disk Space** | 50GB+ | For large workspaces and logs |
| **CPU** | 4+ cores | For Docker container isolation |

### 1.3 External Services

| Service | Required | Purpose | Cost |
|---------|----------|---------|------|
| **OpenAI API** | ✅ Yes | LLM inference + embeddings | Pay-per-use (~$0.50-$2 per task) |
| **PostgreSQL** | ✅ Yes | Task state + vector storage | Self-hosted (free) or managed ($10-50/month) |
| **Docker** | ✅ Yes | Code sandboxing | Self-hosted (free) |

---

## 2. Installation Guide

### 2.1 Quick Start (Development)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/miracle.git
cd miracle/autonomous_agent

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Start PostgreSQL with Docker
docker-compose up -d postgres

# 6. Initialize database
python scripts/setup_db.py

# 7. Verify installation
python -m src.main --version
python -m src.main run --task "Write a hello world function" --language python
```

### 2.2 Step-by-Step Installation (All Platforms)

#### Step 1: Install Python 3.11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- Install with "Add Python to PATH" checked
- Use WSL2 for better compatibility

**Verify:**
```bash
python3.11 --version
# Should output: Python 3.11.x or higher
```

#### Step 2: Install Docker

**Ubuntu:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect
```

**macOS:**
- Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
- Install and start Docker Desktop

**Windows (WSL2):**
- Install WSL2: `wsl --install`
- Install Docker Desktop for Windows
- Enable WSL2 backend in Docker settings

**Verify:**
```bash
docker --version
docker compose version
```

#### Step 3: Install PostgreSQL (Optional - Or Use Docker)

**Option A: Use Docker (Recommended for Development)**
```bash
# Included in docker-compose.yml, no manual install needed
docker-compose up -d postgres
```

**Option B: Install Locally (Production)**

**Ubuntu:**
```bash
sudo apt install postgresql-14 postgresql-contrib-14
sudo apt install postgresql-14-pgvector  # pgvector extension
```

**macOS:**
```bash
brew install postgresql@14
brew install pgvector
```

**Verify:**
```bash
psql --version
# Should output: psql (PostgreSQL) 14.x or higher
```

#### Step 4: Clone and Set Up Project

```bash
git clone https://github.com/yourusername/miracle.git
cd miracle/autonomous_agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep openai  # Should show openai package
```

#### Step 5: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or vim, code, etc.

# Required variables:
#   OPENAI_API_KEY=sk-...
#   DB_PASSWORD=your_secure_password
```

#### Step 6: Start Services

```bash
# Start PostgreSQL (if using Docker)
docker-compose up -d postgres

# Wait for PostgreSQL to be ready (5-10 seconds)
sleep 10

# Initialize database schema
python scripts/setup_db.py

# Verify database connection
python -c "from src.memory.db_manager import DatabaseManager; print('DB connection OK')"
```

#### Step 7: Run First Task

```bash
python -m src.main run \
    --task "Write a function that calculates the factorial of a number" \
    --language python

# If successful, you'll see the agent working through iterations
```

### 2.3 Verifying Installation

**Run diagnostics:**
```bash
python scripts/diagnose.py
```

**Expected output:**
```
✓ Python version: 3.11.5
✓ Docker running: Yes
✓ PostgreSQL accessible: Yes
✓ pgvector installed: Yes (version 0.5.1)
✓ OpenAI API key: Set (sk-...XXXX)
✓ Configuration files: All present
✓ Workspace directory: Writable

All checks passed! System is ready.
```

---

## 3. Python Dependencies

### 3.1 Core Dependencies

```txt
# requirements.txt

# LLM and AI
openai==1.12.0                  # OpenAI API client (GPT-4, embeddings)
tiktoken==0.6.0                 # Token counting for OpenAI models

# Database
psycopg2-binary==2.9.9          # PostgreSQL adapter
sqlalchemy==2.0.25              # ORM (optional, for advanced queries)

# Vector similarity
pgvector==0.2.4                 # Python client for pgvector

# Docker integration
docker==7.0.0                   # Docker Python SDK

# Testing frameworks (for generated code)
pytest==8.0.0                   # Test framework
pytest-cov==4.1.0               # Coverage plugin
hypothesis==6.98.0              # Property-based testing

# CLI and UI
click==8.1.7                    # Command-line interface framework
rich==13.7.0                    # Terminal UI (colors, progress bars)
prompt-toolkit==3.0.43          # Interactive prompts

# Logging and observability
structlog==24.1.0               # Structured logging (JSON)

# Code analysis
bandit==1.7.6                   # Security scanning (SAST)

# Utilities
tenacity==8.2.3                 # Retry logic with exponential backoff
pydantic==2.5.0                 # Data validation
pyyaml==6.0.1                   # YAML configuration parsing
python-dotenv==1.0.0            # .env file loading

# Async support
aiofiles==23.2.1                # Async file I/O
asyncio==3.4.3                  # Async runtime (builtin, but specified for clarity)
```

### 3.2 Dependency Groups

**Development Dependencies** (not in requirements.txt, install separately):
```bash
pip install pytest pytest-asyncio pytest-mock black isort mypy flake8 ipython
```

| Package | Purpose |
|---------|---------|
| pytest-asyncio | Testing async code |
| pytest-mock | Mocking in tests |
| black | Code formatting |
| isort | Import sorting |
| mypy | Type checking |
| flake8 | Linting |
| ipython | REPL for debugging |

**Optional Dependencies** (for advanced features):
```bash
pip install redis prometheus-client sentry-sdk
```

| Package | Purpose |
|---------|---------|
| redis | Caching for embeddings (performance) |
| prometheus-client | Metrics export (monitoring) |
| sentry-sdk | Error tracking (production) |

### 3.3 Installing Dependencies

**Standard Install:**
```bash
pip install -r requirements.txt
```

**With Development Dependencies:**
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

**Update All Dependencies:**
```bash
pip install --upgrade -r requirements.txt
```

**Install Specific Version:**
```bash
pip install openai==1.12.0  # Pin to specific version
```

### 3.4 Dependency Pinning

**Why Pin Versions?**
- Reproducibility (same environment every time)
- Stability (avoid breaking changes)
- Security (control when to upgrade)

**Current Strategy**: Exact version pinning (e.g., `openai==1.12.0`)

**Alternative Strategy**: Compatible version ranges (e.g., `openai>=1.12.0,<2.0.0`)

**Updating Dependencies:**
```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade openai

# Freeze new versions
pip freeze > requirements.txt
```

### 3.5 Dependency Security

**Scan for Vulnerabilities:**
```bash
# Install safety
pip install safety

# Scan dependencies
safety check --json

# Example output:
# {
#   "vulnerabilities": [
#     {
#       "package": "requests",
#       "version": "2.25.0",
#       "cve": "CVE-2023-XXXXX",
#       "severity": "high"
#     }
#   ]
# }
```

**Automated Security Scanning** (CI/CD):
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run safety check
        run: safety check --json
```

---

## 4. Configuration Management

### 4.1 Configuration Files

**Location**: `autonomous_agent/config/`

```
config/
├── settings.yaml          # Main system settings
├── database.yaml          # Database connection
├── openai.yaml            # LLM models and parameters
├── system_prompts.yaml    # Agent prompts
├── allowed_deps.json      # Dependency allowlist
└── safety_rules.yaml      # Security rules
```

### 4.2 Main Configuration (settings.yaml)

```yaml
# config/settings.yaml

orchestrator:
  max_iterations: 15
  checkpoint_frequency: 5        # Save state every N iterations
  warning_threshold: 12          # Warn user at this iteration
  max_concurrent_tasks: 1        # Future: parallel execution

memory:
  similarity_threshold: 0.6      # Min similarity for retrieval
  max_similar_failures: 5        # Max results to retrieve
  max_similar_patterns: 3        # Max patterns for planning
  embedding_cache_ttl: 86400     # 24 hours in seconds

sandbox:
  cpu_limit: 1.0                 # CPU cores per container
  memory_limit: "1g"             # RAM per container
  timeout_seconds: 300           # 5 minutes
  network_enabled: false         # Require approval for network
  allow_network_after_approval: true

logging:
  level: "INFO"                  # DEBUG, INFO, WARNING, ERROR
  format: "json"                 # json or text
  log_dir: "logs"
  max_size_mb: 100               # Rotate logs at 100MB
  backup_count: 5                # Keep 5 old log files

cost_control:
  max_budget_per_task: 5.0       # USD
  warn_at_percentage: 80         # Warn at 80% of budget
```

### 4.3 Database Configuration (database.yaml)

```yaml
# config/database.yaml

postgresql:
  host: "localhost"
  port: 5432
  database: "autonomous_agent"
  user: "postgres"
  password: "${DB_PASSWORD}"     # From environment variable
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  echo: false                    # Set true for SQL logging

pgvector:
  dimensions: 1536               # OpenAI text-embedding-3-large
  index_type: "ivfflat"          # ivfflat or hnsw
  lists: 100                     # IVFFlat parameter
  probes: 10                     # Query probes
```

### 4.4 LLM Configuration (openai.yaml)

```yaml
# config/openai.yaml

provider: "openai"

api:
  key: "${OPENAI_API_KEY}"       # From environment variable
  organization: "${OPENAI_ORG_ID}"  # Optional
  base_url: "https://api.openai.com/v1"  # For custom endpoints

models:
  planner: "gpt-4-turbo-preview"
  coder: "gpt-4-turbo-preview"
  tester: "gpt-4-turbo-preview"
  reflector: "gpt-4-turbo-preview"
  embedding: "text-embedding-3-large"

fallback_sequence:
  - "gpt-4-turbo-preview"
  - "gpt-4"
  - "gpt-3.5-turbo-16k"

parameters:
  temperature: 0.2               # Low for deterministic code
  top_p: 1.0
  max_tokens: 4096
  frequency_penalty: 0.0
  presence_penalty: 0.0

retry:
  max_attempts: 3
  min_wait_seconds: 2
  max_wait_seconds: 10
  exponential_base: 2
```

### 4.5 System Prompts (system_prompts.yaml)

```yaml
# config/system_prompts.yaml

planner: |
  You are an expert software architect. Given a task description, create a detailed
  implementation plan.

  Guidelines:
  - Break down into 2-5 concrete, testable subtasks
  - Identify dependencies between subtasks
  - List expected challenges and edge cases
  - Suggest a testing strategy

  Be specific. Avoid vague subtasks like "make it work" or "add features".

coder: |
  You are an expert software engineer. Generate clean, well-documented code.

  Guidelines:
  - Follow language best practices (PEP 8 for Python, ESLint for Node.js)
  - Include type hints (Python) or JSDoc (Node.js)
  - Handle errors gracefully with try/except or try/catch
  - Write self-documenting code with clear variable names
  - Add comments only where logic is non-obvious

  Use the provided tools to create files:
  - create_file(path, content): Create a new file
  - read_file(path): Read existing file
  - list_files(): List workspace contents

  If tests failed in previous iteration, focus on fixing those specific issues.

tester: |
  You are an expert test engineer. Generate comprehensive tests.

  Guidelines:
  - Include happy path tests (normal operation)
  - Include edge case tests (empty input, null, boundary values)
  - Include error handling tests (invalid input)
  - Use property-based testing (hypothesis) for algorithmic functions
  - Aim for >80% code coverage

  Test framework: pytest for Python, jest for Node.js

reflector: |
  You are an expert debugger. Analyze test failures and identify root causes.

  Guidelines:
  - Parse error messages and stack traces
  - Identify the ROOT CAUSE, not just the symptom
  - Consider similar past failures and their solutions
  - Generate a SPECIFIC, ACTIONABLE fix hypothesis

  Be precise. Avoid vague suggestions like "check your code" or "add error handling".
  Provide actionable fixes: "Change line X from Y to Z because [reason]".
```

### 4.6 Dependency Allowlist (allowed_deps.json)

```json
{
  "python": {
    "allowed": [
      "flask",
      "fastapi",
      "django",
      "requests",
      "httpx",
      "pandas",
      "numpy",
      "scipy",
      "matplotlib",
      "sqlalchemy",
      "psycopg2",
      "pymongo",
      "redis",
      "pytest",
      "hypothesis",
      "click",
      "pydantic",
      "pyyaml",
      "python-dotenv"
    ],
    "blocked": [
      "os",
      "subprocess",
      "pty",
      "socket",
      "pickle"
    ],
    "approval_required": [
      "requests",
      "urllib",
      "httpx",
      "paramiko",
      "fabric"
    ]
  },
  "node": {
    "allowed": [
      "express",
      "axios",
      "lodash",
      "moment",
      "jest",
      "eslint"
    ],
    "blocked": [
      "child_process",
      "net",
      "dgram"
    ],
    "approval_required": [
      "axios",
      "node-fetch",
      "ssh2"
    ]
  }
}
```

### 4.7 Safety Rules (safety_rules.yaml)

```yaml
# config/safety_rules.yaml

python:
  blocked_imports:
    - os
    - subprocess
    - pty
    - socket
    - __builtin__
    - __import__
    - ctypes
    - pickle

  blocked_functions:
    - eval
    - exec
    - compile
    - __import__

  approval_required_operations:
    - network_request
    - subprocess_call
    - file_access_outside_workspace
    - install_dependency

  severity_levels:
    blocked: "critical"          # Block immediately
    approval_required: "high"    # Require user approval
    warning: "medium"            # Log warning, allow

node:
  blocked_modules:
    - child_process
    - net
    - dgram
    - cluster

  blocked_functions:
    - eval
    - Function              # new Function(...)

  approval_required_operations:
    - network_request
    - spawn_process
    - file_access_outside_workspace
```

### 4.8 Loading Configuration

**In Code:**
```python
from src.config_loader import ConfigLoader

# Load all configuration
config = ConfigLoader(config_dir="config")

# Access settings
max_iterations = config.settings.orchestrator.max_iterations
api_key = config.openai.api.key  # Loads from env var
db_host = config.database.postgresql.host

# Validate configuration
config.validate()  # Raises error if invalid
```

---

## 5. Database Setup

### 5.1 Using Docker Compose (Recommended)

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: autonomous_agent_db
    environment:
      POSTGRES_DB: autonomous_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Start Database:**
```bash
docker-compose up -d postgres

# Wait for health check to pass
docker-compose ps  # Should show "healthy"

# View logs
docker-compose logs -f postgres
```

### 5.2 Manual Setup (Local PostgreSQL)

**Step 1: Create Database**
```bash
sudo -u postgres psql -c "CREATE DATABASE autonomous_agent;"
sudo -u postgres psql -c "CREATE USER agent_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE autonomous_agent TO agent_user;"
```

**Step 2: Install pgvector Extension**
```bash
sudo apt install postgresql-14-pgvector

# Enable extension
sudo -u postgres psql -d autonomous_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Step 3: Run Schema Script**
```bash
psql -U agent_user -d autonomous_agent -f scripts/init_db.sql
```

### 5.3 Database Schema (init_db.sql)

**Location**: `scripts/init_db.sql` (202 lines)

**Key Tables**:
- `tasks`: Main task tracking
- `iterations`: Iteration history
- `failures`: Error memory with embeddings
- `patterns`: Success patterns with embeddings
- `metrics`: Performance metrics
- `approvals`: User approval logs

**Indexes**:
- B-tree indexes on foreign keys
- IVFFlat indexes on vector columns (for similarity search)

**Running Manually**:
```bash
psql -U postgres -d autonomous_agent -f scripts/init_db.sql
```

### 5.4 Database Migrations

**Current State**: No formal migration system (MVP)

**Future**: Use Alembic (SQLAlchemy migrations)

**Manual Migration Example**:

**Add a new column to tasks table:**
```sql
-- Create migration file: migrations/001_add_language_version.sql

BEGIN;

ALTER TABLE tasks ADD COLUMN language_version VARCHAR(20);

-- Backfill existing data
UPDATE tasks SET language_version = '3.11' WHERE language = 'python';
UPDATE tasks SET language_version = '18.0' WHERE language = 'node';

COMMIT;
```

**Run migration:**
```bash
psql -U postgres -d autonomous_agent -f migrations/001_add_language_version.sql
```

### 5.5 Database Maintenance

**Backup Database:**
```bash
# Full backup
docker-compose exec postgres pg_dump -U postgres autonomous_agent > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U postgres autonomous_agent < backup.sql
```

**Vacuum Database** (reclaim space, update stats):
```bash
docker-compose exec postgres psql -U postgres -d autonomous_agent -c "VACUUM ANALYZE;"
```

**Check Database Size:**
```bash
docker-compose exec postgres psql -U postgres -d autonomous_agent -c "
SELECT pg_size_pretty(pg_database_size('autonomous_agent')) AS size;
"
```

---

## 6. Docker Setup

### 6.1 Docker Images

**PostgreSQL Image**: `pgvector/pgvector:pg16`
- Pre-built with pgvector extension
- Based on official PostgreSQL 16 image

**Sandbox Images**:
- **Python**: Custom image based on `python:3.11-slim`
- **Node.js**: Custom image based on `node:18-slim`

**Building Sandbox Images:**

```dockerfile
# Dockerfile.sandbox.python
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 sandbox_user

# Install common dependencies
RUN pip install --no-cache-dir pytest hypothesis

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox_user

# Default command
CMD ["/bin/bash"]
```

**Build and Tag:**
```bash
docker build -f Dockerfile.sandbox.python -t autonomous-agent-sandbox:python3.11 .
docker build -f Dockerfile.sandbox.node -t autonomous-agent-sandbox:node18 .
```

### 6.2 Docker Compose Full Stack

```yaml
# docker-compose.yml (full stack)

version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: autonomous_agent_db
    environment:
      POSTGRES_DB: autonomous_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: autonomous_agent_cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: autonomous_agent
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      DB_PASSWORD: ${DB_PASSWORD}
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/autonomous_agent
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./autonomous_agent:/app
      - /var/run/docker.sock:/var/run/docker.sock  # For spawning sandbox containers
    command: python -m src.main run --task "Test task"

volumes:
  postgres_data:
  redis_data:
```

**Start Full Stack:**
```bash
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### 6.3 Docker Best Practices

**1. Use specific tags, not `latest`:**
```yaml
# Bad
image: postgres:latest

# Good
image: pgvector/pgvector:pg16
```

**2. Set resource limits:**
```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 2G
```

**3. Use health checks:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**4. Persist data with volumes:**
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data  # Named volume (persistent)
  # Not: /tmp/data:/var/lib/postgresql/data (lost on reboot)
```

---

## 7. Dependency Approval System

### 7.1 How It Works

**Process**:
1. Agent generates code with `import requests`
2. Tester tries to run tests → ImportError
3. Agent detects missing dependency
4. System checks `allowed_deps.json`:
   - If in `allowed` list → Prompt user
   - If in `blocked` list → Reject immediately
   - If not in list → Prompt with warning
5. User approves or denies
6. If approved: User manually installs (`pip install requests`)
7. Agent retries test execution

### 7.2 Configuration

**File**: `config/allowed_deps.json`

```json
{
  "python": {
    "allowed": ["flask", "requests", "pandas", ...],
    "blocked": ["os", "subprocess", ...],
    "approval_required": ["requests", "httpx", ...]
  }
}
```

### 7.3 User Approval Prompt

```
╭────────────────────────────────────────────────────────────────╮
│ 📦 Dependency Installation Required                            │
├────────────────────────────────────────────────────────────────┤
│ Package: requests                                              │
│ Language: Python                                               │
│ Purpose: HTTP library for API calls                            │
│ Status: ✓ Allowed (in allowlist)                              │
│                                                                │
│ The generated code requires this dependency.                   │
│                                                                │
│ Approve installation? (Y/n)                                    │
╰────────────────────────────────────────────────────────────────╯
```

**If approved:**
```
Please run: pip install requests
Press Enter when ready to continue...
```

### 7.4 Automatic Approval (Future)

**Config**: `config/settings.yaml`

```yaml
dependencies:
  auto_approve_allowed: true     # Auto-approve packages in allowlist
  auto_install: false            # Never auto-install (security)
  prompt_timeout_seconds: 300    # 5 minutes to respond
```

---

## 8. Environment Variables

### 8.1 Required Variables

**File**: `.env`

```bash
# OpenAI API
OPENAI_API_KEY=sk-...          # Required: Your OpenAI API key
OPENAI_ORG_ID=org-...          # Optional: Organization ID

# Database
DB_PASSWORD=your_secure_password  # Required: PostgreSQL password
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@localhost:5432/autonomous_agent

# Environment
ENVIRONMENT=development         # development or production
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR

# Optional: Redis cache
REDIS_URL=redis://localhost:6379
```

### 8.2 Loading Environment Variables

**Automatic Loading** (using python-dotenv):
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env file

api_key = os.getenv("OPENAI_API_KEY")
db_password = os.getenv("DB_PASSWORD")
```

**Manual Loading**:
```bash
export OPENAI_API_KEY=sk-...
export DB_PASSWORD=your_password
python -m src.main run --task "Test task"
```

### 8.3 Security Best Practices

**1. Never commit .env to Git:**
```bash
# .gitignore
.env
.env.*
!.env.example
```

**2. Use .env.example as template:**
```bash
# .env.example
OPENAI_API_KEY=sk-your-key-here
DB_PASSWORD=your-password-here
```

**3. Rotate secrets regularly:**
- OpenAI API keys: Every 90 days
- Database passwords: Every 180 days

**4. Use secrets management in production:**
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Issue 1: "ModuleNotFoundError: No module named 'openai'"

**Cause**: Dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt
```

#### Issue 2: "Could not connect to database"

**Cause**: PostgreSQL not running or wrong credentials

**Solution**:
```bash
# Check if PostgreSQL is running
docker-compose ps

# Start PostgreSQL
docker-compose up -d postgres

# Check credentials in .env file
cat .env | grep DB_PASSWORD
```

#### Issue 3: "Docker daemon is not running"

**Cause**: Docker service not started

**Solution**:
```bash
# Linux
sudo systemctl start docker

# macOS/Windows
# Open Docker Desktop application
```

#### Issue 4: "pgvector extension not found"

**Cause**: pgvector not installed in PostgreSQL

**Solution**:
```bash
# If using Docker Compose (recommended)
docker-compose down
docker-compose up -d postgres  # Uses pgvector/pgvector image

# If using local PostgreSQL
sudo apt install postgresql-14-pgvector
psql -U postgres -d autonomous_agent -c "CREATE EXTENSION vector;"
```

#### Issue 5: "OpenAI API key invalid"

**Cause**: API key not set or incorrect

**Solution**:
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY

# Test API key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If invalid, get new key from https://platform.openai.com/api-keys
```

### 9.2 Diagnostic Tools

**Run diagnostics:**
```bash
python scripts/diagnose.py
```

**Output**:
```
Checking system requirements...
✓ Python version: 3.11.5 (OK)
✓ Docker installed: 24.0.5 (OK)
✗ PostgreSQL connection: Failed (Connection refused)
  → Solution: Start PostgreSQL with: docker-compose up -d postgres

✓ OpenAI API key: Valid
✓ Configuration files: All present
✗ Workspace directory: Not writable
  → Solution: chmod 755 autonomous_agent/sandbox/workspace/

2 issues found. Fix them and run again.
```

### 9.3 Debug Mode

**Enable verbose logging:**
```yaml
# config/settings.yaml
logging:
  level: "DEBUG"
```

**Or use environment variable:**
```bash
export LOG_LEVEL=DEBUG
python -m src.main run --task "Test"
```

**View debug logs:**
```bash
tail -f logs/autonomous_agent.log | jq '.'
```

---

## 10. Upgrading

### 10.1 Upgrading Python Dependencies

```bash
# Check outdated packages
pip list --outdated

# Upgrade specific package
pip install --upgrade openai

# Update requirements.txt
pip freeze > requirements.txt

# Test after upgrade
pytest tests/ -v
```

### 10.2 Upgrading Database

**Minor version** (e.g., PostgreSQL 14.10 → 14.11):
```bash
docker-compose down
docker-compose pull postgres  # Get latest image
docker-compose up -d postgres
```

**Major version** (e.g., PostgreSQL 14 → 16):
```bash
# 1. Backup database
docker-compose exec postgres pg_dump -U postgres autonomous_agent > backup.sql

# 2. Update docker-compose.yml
#    image: pgvector/pgvector:pg14 → pg16

# 3. Recreate container
docker-compose down -v  # Warning: Destroys data
docker-compose up -d postgres

# 4. Restore backup
docker-compose exec -T postgres psql -U postgres autonomous_agent < backup.sql
```

### 10.3 Upgrading Configuration

**When adding new config options:**

1. **Add default value**:
```yaml
# config/settings.yaml
new_feature:
  enabled: false  # Default (safe)
```

2. **Update config loader**:
```python
# src/config_loader.py
new_feature_enabled = config.get("new_feature", {}).get("enabled", False)
```

3. **Document in DEPENDENCIES.md** (this file)

### 10.4 Breaking Changes

**v1.0 → v2.0 (Hypothetical)**:

**Breaking Change**: Database schema modified

**Migration Steps**:
1. Backup database: `pg_dump ... > backup.sql`
2. Run migration: `python scripts/migrate_v1_to_v2.py`
3. Test: `pytest tests/ -v`
4. If issues: Restore backup `psql ... < backup.sql`

---

## 11. Production Deployment Checklist

### 11.1 Pre-Deployment

- [ ] All dependencies pinned to specific versions
- [ ] Environment variables set (not using .env file)
- [ ] Database backups automated
- [ ] Log rotation configured
- [ ] Resource limits set (Docker, PostgreSQL)
- [ ] Secrets stored in vault (not environment variables)
- [ ] Monitoring configured (Prometheus, Sentry)
- [ ] Health checks configured
- [ ] Load testing completed

### 11.2 Deployment

- [ ] Use production-grade PostgreSQL (RDS, Cloud SQL)
- [ ] Use managed Docker (ECS, GKE)
- [ ] Enable TLS for database connections
- [ ] Set up firewall rules (restrict database access)
- [ ] Use CDN for static assets (if applicable)
- [ ] Configure auto-scaling (if needed)

### 11.3 Post-Deployment

- [ ] Monitor logs for errors
- [ ] Monitor metrics (task success rate, latency)
- [ ] Test with production data
- [ ] Set up alerts (high error rate, high cost)
- [ ] Document deployment process
- [ ] Plan for disaster recovery

---

**Last Updated**: 2026-01-16
**Maintained By**: DevOps Team
**Related Documents**: `AGENT-PLANNING.md`, `AGENT-EXECUTION.md`, `ARCHITECTURE.md`, `FUNCTIONALITY.md`
