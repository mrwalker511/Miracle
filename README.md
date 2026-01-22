# Miracle - Autonomous Coding Agent

An autonomous AI-powered coding system that iteratively writes and tests code until it works.

**Core Philosophy**: _"The difference between a chatbot and an agent is the loop."_

---

## 📚 Agent Documentation

**Start here**: **[AGENTS.md](AGENTS.md)** - Progressive disclosure entry point for AI agents

This project uses **progressive disclosure** for documentation - start with what you need, dig deeper as needed. The root [AGENTS.md](AGENTS.md) contains only essentials (commands, requirements), with links to focused topic files:

### 📖 Topic-Based Documentation

Navigate by what you need to accomplish:

- 🚀 **[Getting Started](docs/agents/getting-started.md)** - Setup, installation, project structure, first run
- 🏗️ **[Architecture](docs/agents/architecture.md)** - State machine, components, data flow, patterns
- 🔧 **[Development Workflows](docs/agents/development-workflows.md)** - Adding tools/states, bug fixes, common tasks
- 📝 **[Code Conventions](docs/agents/code-conventions.md)** - Async patterns, DB ops, config access, best practices
- 🤖 **[Agent Behaviors](docs/agents/agent-behaviors.md)** - Planner, Coder, Tester, Reflector specifics
- 🔒 **[Safety & Security](docs/agents/safety-security.md)** - Multi-layer protection, security checklist
- 🧠 **[Memory & Learning](docs/agents/memory-learning.md)** - Vector search, pattern storage, failure analysis
- 🧪 **[Testing Strategy](docs/agents/testing-strategy.md)** - Unit, integration, e2e testing approaches

### 🏗️ Architecture Deep-Dive

**[docs/architecture/](docs/architecture/)** - Complete technical architecture (10 focused files)
- Each file covers a specific architectural concern (200-500 lines)
- Numbered for logical progression
- From system overview to technical decisions

### 🔄 Functionality Documentation

**[FUNCTIONALITY.md](FUNCTIONALITY.md)** - System behavior and operational flows
- Core functionality explained
- Iteration loop behavior
- Agent behaviors (Planner, Coder, Tester, Reflector)
- Tool use mechanics
- Memory and learning system
- Safety mechanisms
- Error handling strategies
- User interaction flows
- Edge cases and limitations
- Observability and debugging

### 📦 Dependencies & Setup

**[DEPENDENCIES.md](DEPENDENCIES.md)** - Setup, configuration, and dependency management
- System requirements
- Installation guide (all platforms)
- Python dependencies
- Configuration management
- Database setup
- Docker setup
- Dependency approval system
- Environment variables
- Troubleshooting guide
- Upgrade procedures

---

## 🚀 Quick Start

For detailed setup instructions, see [DEPENDENCIES.md](DEPENDENCIES.md).

```bash
# 1. Clone and navigate
git clone https://github.com/yourusername/miracle.git
cd miracle/autonomous_agent

# 2. Install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Start database
docker-compose up -d postgres

# 5. Initialize database
python scripts/setup_db.py

# 6. Run your first task
python -m src.main run --task "Write a function to calculate fibonacci" --language python
```

---

## 📖 Project Overview

### What It Does

The Autonomous Coding Agent accepts high-level coding tasks and autonomously:
1. **Plans** - Breaks down tasks into subtasks
2. **Codes** - Generates code using LLM + tools
3. **Tests** - Generates and runs comprehensive tests
4. **Reflects** - Analyzes failures and searches for solutions
5. **Iterates** - Continues until tests pass (max 15 iterations)

### Key Features

- **Autonomous Loop**: Operates continuously until success or max iterations
- **Learning System**: Stores failures and patterns with vector embeddings for retrieval
- **Multi-layer Safety**: AST scanning, Bandit SAST, user approval, sandbox isolation
- **Memory System**: PostgreSQL + pgvector for similarity search
- **Language Support**: Implemented in Python, can generate code in multiple languages
- **Resumable**: Checkpoint/resume support for interrupted tasks
- **Flexible Deployment**: Works with or without Docker

---

## 🤝 Contributing

When contributing to this project:

1. Start with [AGENTS.md](AGENTS.md) for essential commands and requirements
2. Read [Architecture](docs/agents/architecture.md) if designing features
3. Read [Development Workflows](docs/agents/development-workflows.md) for implementation tasks
4. Follow [Code Conventions](docs/agents/code-conventions.md)
5. Write tests following [Testing Strategy](docs/agents/testing-strategy.md)
6. Update relevant documentation if behavior changes

---

## 📄 License

[Add license information here]

---

## 🔗 Additional Resources

- **Database Schema**: See `scripts/init_db.sql`
- **Archived Documentation**: Legacy agent docs moved to `docs/archive/` (historical reference)

---

**Built with**: Python 3.11+, OpenAI GPT-4, PostgreSQL + pgvector, Docker (optional)