# Miracle - Autonomous Coding Agent

An autonomous AI-powered coding system that iteratively writes and tests code until it works.

**Core Philosophy**: _"The difference between a chatbot and an agent is the loop."_

---

## 📚 Agent Documentation (Agent.MD Files)

This project includes comprehensive **Agent.MD** documentation to enable any AI coding tool to work on this codebase effectively. Whether you're using Claude, ChatGPT, GitHub Copilot, or any other AI assistant, these documents provide all the context you need.

### 🎯 For Planning Agents

**[AGENT-PLANNING.md](AGENT-PLANNING.md)** - High-level architecture and feature design
- System architecture overview
- State machine patterns
- Component responsibilities
- Extension points
- Feature planning checklist
- Architectural decisions and trade-offs

### 🛠️ For Execution/Worker Agents

**[AGENT-EXECUTION.md](AGENT-EXECUTION.md)** - Implementation guidelines and best practices
- Getting started guide
- Common implementation tasks
- Testing guidelines
- Code style conventions
- Debugging tips
- Pre-commit checklist

### 🏗️ Architecture Documentation

**[ARCHITECTURE.md](ARCHITECTURE.md)** - Deep technical architecture
- High-level system design
- Architectural patterns (State Machine, Agent, Tool Use, etc.)
- Component architecture details
- Data flow diagrams
- Database schema design
- LLM integration architecture
- Security architecture
- Technical decisions and rationale

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
- **Multi-layer Safety**: AST scanning, Bandit SAST, user approval, Docker sandboxing
- **Memory System**: PostgreSQL + pgvector for similarity search
- **Multi-language**: Python (primary), Node.js (secondary)
- **Resumable**: Checkpoint/resume support for interrupted tasks

---

## 🤝 Contributing

When contributing to this project:

1. Read [AGENT-PLANNING.md](AGENT-PLANNING.md) if designing features
2. Read [AGENT-EXECUTION.md](AGENT-EXECUTION.md) if implementing code
3. Follow the code style guidelines
4. Write tests for new features
5. Update relevant Agent.MD files if behavior changes

---

## 📄 License

[Add license information here]

---

## 🔗 Additional Resources

- **Main Agent README**: `autonomous_agent/README.md`
- **Handoff Document**: `autonomous_coding_agent_handoff.md` (1,516 lines of detailed specs)
- **Database Schema**: `autonomous_agent/scripts/init_db.sql`

---

**Built with**: Python 3.11+, OpenAI GPT-4, PostgreSQL + pgvector, Docker