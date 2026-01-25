# Miracle - Autonomous Coding Agent User Manual

A comprehensive guide to using the Miracle autonomous coding agent for efficient development and automation.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation & Setup](#installation--setup)
4. [CLI Commands Reference](#cli-commands-reference)
5. [Task Structuring Guide](#task-structuring-guide)
6. [Working with Existing Projects](#working-with-existing-projects)
7. [Advanced Features](#advanced-features)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Configuration](#configuration)
11. [FAQ](#faq)

---

## Overview

Miracle is an autonomous AI-powered coding system that iteratively writes and tests code until it works. Unlike traditional AI chat interfaces, Miracle operates in a continuous loop, planning, coding, testing, and reflecting until your task is successfully completed.

### Key Capabilities

- **Autonomous Execution**: Continuously iterates until success or maximum iterations
- **Multi-Language Support**: Works with Python, Node.js, and any programming language
- **Smart Task Structuring**: Automatically breaks down complex tasks into manageable subtasks
- **Memory & Learning**: Stores patterns and solutions for future tasks
- **Safety Features**: AST scanning, security auditing, and user approval systems
- **Flexible Deployment**: Works with or without Docker sandboxing
- **Existing Project Integration**: Can modify your current codebase safely

### How It Works

```
User Task → Planning → Coding → Testing → Reflecting → (Loop until success)
     ↓         ↓         ↓        ↓          ↓
  Structure   Generate  Execute  Validate    Fix
  & Goals     Code      Tests    Results    Failures
```

---

## Quick Start

### Basic Usage

```bash
# Navigate to the project
cd autonomous_agent

# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Start a simple task
python -m src.main run --task "Create a function to calculate fibonacci numbers"
```

### First Task Output

```
AUTONOMOUS CODING AGENT v0.1.0
Build code autonomously with AI

Task: Create a function to calculate fibonacci numbers
Problem type: general
Language: python

Starting autonomous execution (max 15 iterations)...
Phases: planning -> coding -> testing

[Planning] Analyzing task and creating implementation plan...
[Coding] Generating code based on plan...
[Testing] Creating and running tests...
[Reflecting] Analyzing results and planning improvements...
...
TASK COMPLETED SUCCESSFULLY ✅
```

---

## Installation & Setup

### Prerequisites

**Required:**
- Python 3.11+
- PostgreSQL 14+ (with pgvector extension)
- OpenAI API key
- 4GB+ RAM recommended

**Optional:**
- Docker & Docker Compose (for sandboxed execution)

### Step-by-Step Installation

#### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd autonomous_agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials
OPENAI_API_KEY=sk-your-openai-api-key-here
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=autonomous_agent
DB_USER=agent_user
```

#### 3. Database Setup

**Option A: Docker (Recommended for Development)**

```bash
# Start PostgreSQL with pgvector
docker-compose up -d postgres

# Initialize database schema
python scripts/setup_db.py
```

**Option B: Local PostgreSQL**

```bash
# Ensure PostgreSQL 14+ is installed with pgvector
# Create database
createdb autonomous_agent

# Initialize schema
python scripts/setup_db.py
```

#### 4. Verify Installation

```bash
# Test setup
python -m src.main setup

# Run a simple test
python -m src.main run --task "Create a hello world script"
```

---

## CLI Commands Reference

### Main Commands

#### `run` - Execute a new task

```bash
python -m src.main run [OPTIONS]
```

**Essential Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `--task`, `-t` | Task description | `--task "Build a REST API"` |
| `--language`, `-l` | Programming language | `--language python` |
| `--max-iterations`, `-m` | Maximum iterations | `--max-iterations 10` |
| `--workspace`, `-w` | Target workspace | `--workspace "/path/to/project"` |
| `--enable-review` | Enable code review phase | `--enable-review` |
| `--enable-audit` | Enable security audit | `--enable-audit` |
| `--skip-reprompter` | Skip task structuring | `--skip-reprompter` |

**Examples:**

```bash
# Basic task
python -m src.main run --task "Create a web scraper for news articles"

# With language specification
python -m src.main run --task "Build a CLI todo app" --language node

# With custom workspace
python -m src.main run --task "Add user authentication" --workspace "/my/project"

# With advanced features
python -m src.main run --task "Create a payment processing system" --enable-review --enable-audit

# Interactive mode (no task specified)
python -m src.main run
```

#### `history` - View task history

```bash
python -m src.main history
```

Shows recent tasks with status, iterations, and timestamps.

#### `setup` - Initialize system

```bash
python -m src.main setup
```

Displays setup instructions and system requirements.

### Task Arguments

#### Problem Types

Specify the type of problem for better task structuring:

- `general` - General programming task
- `web_app` - Web application development
- `cli_tool` - Command-line tool
- `data_pipeline` - Data processing pipeline
- `api` - API development
- `automation` - Task automation
- `testing` - Test suite creation

```bash
python -m src.main run --task "Build a weather API" --problem-type api
```

#### Language Selection

```bash
# Python (default)
python -m src.main run --task "Process CSV files" --language python

# Node.js
python -m src.main run --task "Create Express server" --language node

# Auto-detect from problem type
python -m src.main run --task "Build React component" --problem-type web_app  # Will use Node.js
```

---

## Task Structuring Guide

### Writing Effective Tasks

The quality of your task description directly impacts the agent's success. Follow these guidelines:

#### ✅ Good Task Examples

**Specific and Actionable:**
```
"Create a function called 'calculate_tax' that takes income as input and returns tax amount using a progressive tax system with brackets: 10% on first $50k, 20% on next $100k, 30% above $150k"
```

**Contextual and Goal-Oriented:**
```
"Build a REST API endpoint '/api/users/{id}' that returns user profile data from PostgreSQL database, including error handling for invalid user IDs and proper HTTP status codes"
```

**Constraints and Requirements:**
```
"Create a web scraper for 'example.com/news' that extracts article titles and URLs, saves them to CSV, handles rate limiting (1 request per second), and includes retry logic for failed requests"
```

#### ❌ Poor Task Examples

**Too Vague:**
```
"Make something with Python"
"Build an app"
"Fix the website"
```

**Overly Complex:**
```
"Create a complete e-commerce platform with payment processing, user management, inventory system, admin dashboard, and mobile app"
```

**Missing Context:**
```
"Create a function that processes data"
```

### Task Components

#### Essential Elements

1. **Action**: What you want the agent to do
2. **Target**: What file(s) or component(s) to work with
3. **Input/Output**: Expected inputs and outputs
4. **Constraints**: Any limitations or requirements
5. **Context**: How it fits into your project

#### Template Structure

```
[Action] + [Target/Component] + [Specific Requirements] + [Context]
```

**Examples:**
- `Create a function 'validate_email' in utils.py that checks email format using regex`
- `Add user authentication middleware to Express app.js that checks JWT tokens`
- `Fix the database connection error in models.py that occurs when DB_HOST is unset`

### Interactive Task Refinement

When you run tasks interactively (without `--task`), the system will ask clarifying questions:

```
? Enter your coding task: Build a web app
[Reprompter] Analyzing task for better structuring...

Some clarification would help:
  ? What type of web app? (flask, django, fastapi, express, react, vue): flask
  ? What's the main purpose? (api, dashboard, blog, e-commerce, other): api
  ? Any specific requirements? (database, authentication, file uploads): database, authentication

Task structured:
  Title: Flask API with Database and Authentication
  Goal: Build a REST API using Flask with user authentication and database integration
  Complexity: moderate
```

---

## Working with Existing Projects

### Safety First

⚠️ **CRITICAL WARNINGS:**

- **ALWAYS** commit your changes to git before running the agent
- Ensure you have a clean working tree
- The agent modifies files in-place with no "undo" button
- Test on a separate branch first

### Using External Workspace

#### Method 1: CLI Argument (Recommended)

```bash
# Point to your existing project
python -m src.main run --task "Add user registration endpoint" --workspace "/path/to/your/project"
```

This is the safest approach - no permanent configuration changes.

#### Method 2: Configuration File

```bash
# Edit config/settings.yaml
sandbox:
  workspace_root: "/path/to/your/project"
```

#### Method 3: Docker File Sharing (Windows/Mac)

If using Docker sandbox:
1. Open Docker Desktop
2. Settings → Resources → File Sharing
3. Add your project directory path

### Best Practices for Existing Projects

#### 1. Project Exploration

Start with exploration tasks:

```bash
python -m src.main run --task "Explore the project structure and identify the main entry point"
```

#### 2. Be Specific with File Paths

```bash
# Instead of:
python -m src.main run --task "Fix the authentication bug"

# Use:
python -m src.main run --task "Fix the authentication error in src/auth/login.py on line 45"
```

#### 3. Context About Project Structure

Provide context about your project:

```bash
python -m src.main run --task "Add error handling middleware to the Express app in app.js. The app uses mongoose for MongoDB and has existing error handling in middleware/errorHandler.js"
```

#### 4. Language-Specific Considerations

**Python Projects:**
```bash
python -m src.main run --task "Add type hints to the User class in models/user.py using dataclasses"
```

**Node.js Projects:**
```bash
python -m src.main run --task "Convert the CommonJS require statements to ES6 imports in utils/helpers.js"
```

### Common Project Modifications

#### Adding Features

```bash
# Database operations
python -m src.main run --task "Add a new 'UserPreference' model with fields for theme and language, including migrations"

# API endpoints
python -m src.main run --task "Create POST /api/notifications endpoint that sends email notifications using the existing mailer service"

# Frontend components
python -m src.main run --task "Create a reusable Button component in src/components/ui/Button.tsx with variants: primary, secondary, danger"
```

#### Bug Fixes

```bash
# Memory leaks
python -m src.main run --task "Fix the memory leak in data/processor.py by properly closing database connections"

# Performance issues
python -m src.main run --task "Optimize the slow database query in queries/user_analytics.sql that takes over 5 seconds"

# Error handling
python -m src.main run --task "Add proper error handling for the FileNotFoundError in utils/file_loader.py"
```

#### Code Quality Improvements

```bash
# Adding tests
python -m src.main run --task "Create comprehensive test suite for the payment processing module using pytest"

# Documentation
python -m src.main run --task "Add docstrings and type hints to all functions in src/api/handlers.py"

# Refactoring
python -m src.main run --task "Extract the duplicate validation logic from user_registration.py into a reusable validation module"
```

---

## Advanced Features

### Code Review Phase

Enable comprehensive code review:

```bash
python -m src.main run --task "Build a user management system" --enable-review
```

The review phase includes:
- Code quality analysis
- Style and convention checks
- Architecture review
- Performance considerations
- Maintainability assessment

### Security Audit

Enable security auditing:

```bash
python -m src.main run --task "Create a file upload API" --enable-audit
```

Security checks include:
- SQL injection vulnerabilities
- XSS prevention
- Input validation
- Authentication/authorization gaps
- Dependency security scanning

### Memory and Learning System

The agent learns from each task:

- **Success Patterns**: Stores effective approaches for similar problems
- **Failure Analysis**: Records what doesn't work and why
- **Context Building**: Builds understanding of your project structure
- **Performance Metrics**: Tracks iteration counts and success rates

### Custom Iterations

Control the iteration process:

```bash
# Quick tasks (faster but may fail)
python -m src.main run --task "Simple function" --max-iterations 5

# Complex tasks (more thorough)
python -m src.main run --task "Complex system integration" --max-iterations 25
```

### Task Structuring Options

Skip automatic task refinement:

```bash
python -m src.main run --task "Raw task description" --skip-reprompter
```

Use this when you have very specific requirements and don't want the agent to interpret your task.

---

## Best Practices

### 1. Task Writing

#### Be Specific and Detailed

```bash
# Instead of:
"Create a calculator"

# Use:
"Create a Calculator class in src/utils/calculator.py with methods: add(), subtract(), multiply(), divide(). Include input validation and handle division by zero errors"
```

#### Provide Context

```bash
# Include project context:
python -m src.main run --task "Add caching to the existing API endpoints in app.py using Redis. The app currently uses Flask and SQLAlchemy"
```

#### Specify Success Criteria

```bash
# Define what success looks like:
python -m src.main run --task "Create unit tests for the User model that achieve 90% code coverage and test all validation rules, edge cases, and database operations"
```

### 2. Project Organization

#### Use Structured Workspaces

```bash
# Organize your project for better agent understanding:
your_project/
├── src/          # Source code
├── tests/        # Test files
├── docs/         # Documentation
├── config/       # Configuration files
└── scripts/      # Utility scripts
```

#### Provide README Files

Include clear README.md files explaining:
- Project structure
- Dependencies
- Setup instructions
- Key components

### 3. Iterative Development

#### Start Small

```bash
# Break large features into smaller tasks:
# Task 1: Database model
python -m src.main run --task "Create User model with basic fields"

# Task 2: API endpoints
python -m src.main run --task "Create user registration API endpoint"

# Task 3: Validation
python -m src.main run --task "Add input validation to user registration"

# Task 4: Tests
python -m src.main run --task "Create comprehensive tests for user registration"
```

#### Use Checkpoints

```bash
# Test each major component:
python -m src.main run --task "Test the user authentication system by creating a test user and verifying login works"
```

### 4. Code Quality

#### Enable Review Features

```bash
# Always use review for production code:
python -m src.main run --task "Create production-ready API endpoint" --enable-review --enable-audit
```

#### Add Tests Early

```bash
# Generate tests alongside features:
python -m src.main run --task "Create a new service module and its test suite"
```

### 5. Error Handling

#### Provide Error Context

```bash
# Instead of:
"Fix the bug"

# Use:
"Fix the AttributeError in data_processor.py line 23 where 'data' is sometimes None, causing the processing to fail"
```

#### Specify Expected Behavior

```bash
# Define what should happen:
python -m src.main run --task "Fix the email validation to accept international domains like user@例え.jp and handle edge cases gracefully"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Setup and Installation

**Issue**: `PostgreSQL connection refused`

```bash
# Solution:
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Or start with Docker
docker-compose up -d postgres

# Verify connection
psql -h localhost -U agent_user -d autonomous_agent
```

**Issue**: `OPENAI_API_KEY not found`

```bash
# Solution:
# Verify .env file exists and contains the key
cat .env | grep OPENAI_API_KEY

# Check environment variables
echo $OPENAI_API_KEY

# Restart terminal after adding to .env
```

**Issue**: `pgvector extension not found`

```bash
# Solution:
# Install pgvector extension
psql -d autonomous_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Or rebuild PostgreSQL with pgvector
docker-compose down
docker-compose up -d postgres
```

#### 2. Task Execution Issues

**Issue**: `Task fails immediately with "No valid workspace"`

```bash
# Solutions:
# 1. Check workspace permissions
ls -la /path/to/workspace

# 2. Use absolute paths
python -m src.main run --task "..." --workspace "/absolute/path/to/project"

# 3. Create workspace if using default
mkdir -p sandbox/workspace
```

**Issue**: `Agent gets stuck in infinite loop`

```bash
# Solutions:
# 1. Set lower iteration limit
python -m src.main run --task "..." --max-iterations 5

# 2. Be more specific in task description
python -m src.main run --task "Create a simple hello function" --skip-reprompter

# 3. Check for circular dependencies in existing code
```

**Issue**: `Tests keep failing`

```bash
# Solutions:
# 1. Check if dependencies are installed
pip list | grep -E "(pytest|hypothesis)"

# 2. Verify test environment
python -c "import pytest; print('Tests OK')"

# 3. Simplify the task initially
python -m src.main run --task "Create a basic function that returns 'hello world'"
```

#### 3. Code Generation Issues

**Issue**: `Generated code has import errors`

```bash
# Solutions:
# 1. Specify required dependencies
python -m src.main run --task "Create a data analysis script using pandas and numpy"

# 2. Check current environment
pip list

# 3. Install missing packages manually first
pip install pandas numpy
```

**Issue**: `Agent generates incorrect business logic`

```bash
# Solutions:
# 1. Provide more detailed specifications
# Instead of:
"Create a tax calculator"

# Use:
"Create a tax calculator for US federal income tax 2024 with brackets: 10% on $0-$11,600, 12% on $11,601-$47,150, etc."

# 2. Add examples of expected input/output
# 3. Break complex logic into smaller steps
```

**Issue**: `Agent modifies wrong files`

```bash
# Solutions:
# 1. Use absolute paths in task descriptions
python -m src.main run --task "Modify /absolute/path/to/specific/file.py"

# 2. Use workspace targeting
python -m src.main run --task "Add function to main.py" --workspace "/project/path"

# 3. Review file structure first
python -m src.main run --task "List all Python files in the project"
```

#### 4. Performance Issues

**Issue**: `Agent is very slow`

```bash
# Solutions:
# 1. Reduce iteration limit for simple tasks
python -m src.main run --task "Simple task" --max-iterations 3

# 2. Use faster models (check config/openai.yaml)
# 3. Check OpenAI API rate limits
# 4. Monitor system resources
```

**Issue**: `High token usage`

```bash
# Solutions:
# 1. Break large tasks into smaller ones
# 2. Use structured tasks (--skip-reprompter for simple tasks)
# 3. Review and optimize prompt engineering
```

#### 5. Database and Memory Issues

**Issue**: `Memory search returns irrelevant results`

```bash
# Solutions:
# 1. Clear memory for specific task types
# Check database directly:
psql -d autonomous_agent -c "DELETE FROM patterns WHERE task_type = 'your_task_type';"

# 2. Use different problem types
python -m src.main run --task "..." --problem-type specific_type
```

**Issue**: `Database schema out of sync`

```bash
# Solutions:
# 1. Reinitialize database
python scripts/setup_db.py --force

# 2. Check database migrations
# Review scripts/init_db.sql
```

### Debug Mode

Enable verbose logging:

```bash
# Set debug level in .env
LOG_LEVEL=DEBUG

# Run with detailed output
python -m src.main run --task "..." 2>&1 | tee debug.log
```

### Performance Monitoring

Monitor system resources:

```bash
# Check memory usage
free -h

# Monitor disk space
df -h

# Check database connections
psql -d autonomous_agent -c "SELECT count(*) FROM pg_stat_activity;"
```

### Getting Help

1. **Check logs**: Review application logs for specific error messages
2. **Search issues**: Look for similar problems in documentation
3. **Isolate problems**: Test with minimal task examples
4. **Check configuration**: Verify all settings are correct
5. **Test components**: Verify each system component individually

---

## Configuration

### Configuration Files

The system uses multiple YAML configuration files:

#### Main Configuration (`config/settings.yaml`)

```yaml
sandbox:
  engine: "docker"  # or "subprocess"
  workspace_root: "/path/to/workspace"
  timeout: 300

database:
  host: "localhost"
  port: 5432
  name: "autonomous_agent"
  user: "agent_user"

logging:
  level: "INFO"
  format: "json"
```

#### OpenAI Configuration (`config/openai.yaml`)

```yaml
models:
  planner: "gpt-4"
  coder: "gpt-4"
  tester: "gpt-3.5-turbo"
  reflector: "gpt-4"

settings:
  max_tokens: 4000
  temperature: 0.1
  retry_attempts: 3
```

#### System Prompts (`config/system_prompts.yaml`)

Customize agent behaviors by modifying system prompts.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DB_PASSWORD` | Database password | Required |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `LOG_LEVEL` | Logging level | INFO |
| `ENVIRONMENT` | Environment mode | development |

### Docker Configuration

#### Custom Docker Setup

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  postgres:
    environment:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=C"
    volumes:
      - ./custom_init.sql:/docker-entrypoint-initdb.d/custom_init.sql
```

#### Resource Limits

```yaml
sandbox:
  build:
    context: .
    dockerfile: Dockerfile.sandbox
  container_name: agent_sandbox
  mem_limit: 2g
  cpus: 2
  security_opt:
    - no-new-privileges:true
```

### Performance Tuning

#### Database Optimization

```sql
-- Optimize for vector search
ALTER TABLE patterns ADD INDEX idx_embedding vector_cosine_ops;
ALTER TABLE failures ADD INDEX idx_embedding vector_cosine_ops;
```

#### Model Configuration

```yaml
# Use faster models for testing
models:
  tester: "gpt-3.5-turbo"  # Faster for test generation
  planner: "gpt-4"         # More capable for planning

# Reduce token limits for speed
settings:
  max_tokens: 2000
  temperature: 0.0  # Deterministic for faster responses
```

---

## FAQ

### General Questions

**Q: How is this different from ChatGPT or GitHub Copilot?**

A: Unlike chat interfaces, Miracle operates autonomously in a continuous loop, planning → coding → testing → reflecting until success. It also maintains long-term memory and learns from previous tasks.

**Q: What programming languages are supported?**

A: Miracle can generate code in any programming language you specify, including Python, JavaScript/Node.js, Java, C++, and many others. The agent is language-agnostic.

**Q: Can it work with my existing codebase?**

A: Yes, you can point Miracle to your existing project using the `--workspace` flag. However, always commit your changes to git first as modifications are in-place.

**Q: How many iterations does it typically take?**

A: Simple tasks: 1-3 iterations, Complex tasks: 5-15 iterations. You can control this with `--max-iterations`.

### Technical Questions

**Q: Do I need Docker?**

A: No, Docker is optional. Miracle can run with local PostgreSQL or subprocess execution. Docker provides better security and isolation.

**Q: What happens if it fails?**

A: The agent records failures in its memory system and provides detailed logs. You can review what went wrong and retry with refined instructions.

**Q: Is my code secure?**

A: Miracle includes multiple security layers: AST scanning, security auditing, user approval for dependencies, and optional Docker sandboxing. However, always review generated code before production use.

**Q: Can I customize the behavior?**

A: Yes, you can modify system prompts, configuration files, and even create custom agents. See the architecture documentation for details.

### Usage Questions

**Q: How do I write good task descriptions?**

A: Be specific about what you want, include file paths if working with existing projects, specify inputs/outputs, and include any constraints or requirements.

**Q: Should I use interactive mode or command line?**

A: Interactive mode is better for complex tasks that need clarification. Command line is better for well-defined tasks and automation.

**Q: How do I handle large projects?**

A: Break them into smaller tasks. Start with exploration, then add features incrementally. Use the `--workspace` flag to target specific directories.

**Q: Can it create tests?**

A: Yes, the tester agent generates comprehensive test suites using pytest and hypothesis for property-based testing.

### Troubleshooting Questions

**Q: What if the agent gets stuck?**

A: Check the iteration limit, simplify the task, or kill the process and retry with more specific instructions.

**Q: How do I fix import errors?**

A: Ensure all dependencies are installed, specify required packages in your task description, and verify the Python environment.

**Q: Why is it slow?**

A: Complex tasks take time. You can reduce iterations for simple tasks, use faster models, or check your OpenAI API rate limits.

### Advanced Questions

**Q: Can I integrate this into my CI/CD pipeline?**

A: Yes, you can run Miracle programmatically. Check the API documentation for integration examples.

**Q: How does the memory system work?**

A: Miracle uses PostgreSQL with pgvector to store patterns, failures, and successful solutions, enabling similarity search for better future performance.

**Q: Can I run multiple agents in parallel?**

A: The current design is single-threaded per task, but you can run multiple tasks in parallel using different terminal sessions or process managers.

---

## Support

For additional support:

1. **Documentation**: Check the comprehensive docs in `/docs`
2. **Examples**: Look at sample tasks in `/examples`
3. **Issues**: Search existing issues or create new ones
4. **Community**: Join discussions and share experiences

---

*Last Updated: 2025-01-25*  
*Version: 0.1.0*