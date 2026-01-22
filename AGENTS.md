# AGENTS.md

**Project**: Miracle - Autonomous Coding Agent  
**System Language**: Python 3.11+ (Supports any generated language)  
**Entry Point**: `src/main.py` (CLI)  
**Package Manager**: pip (venv)

## Essential Commands

```bash
# Run tests
pytest tests/ -v

# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type check
mypy src/

# Lint
flake8 src/ tests/
```

## Code Requirements

- **Style**: PEP 8
- **Type hints**: Required on all public functions
- **Docstrings**: Required for all public functions
- **Async/await**: All agent methods and LLM calls must be async

## Documentation

Progressive disclosure - start with what you need, dig deeper as needed:

- 📚 **[Getting Started](docs/agents/getting-started.md)** - Setup, installation, project structure
- 🏗️ **[Architecture](docs/agents/architecture.md)** - State machine, components, patterns
- 🔧 **[Development Workflows](docs/agents/development-workflows.md)** - Common tasks, bug fixes
- 📝 **[Code Conventions](docs/agents/code-conventions.md)** - Async patterns, DB ops, config
- 🤖 **[Agent Behaviors](docs/agents/agent-behaviors.md)** - Planner, Coder, Tester, Reflector
- 🔒 **[Safety & Security](docs/agents/safety-security.md)** - Multi-layer protection, checklist
- 🧠 **[Memory & Learning](docs/agents/memory-learning.md)** - Vector search, pattern storage
- 🧪 **[Testing Strategy](docs/agents/testing-strategy.md)** - Unit, integration, property-based

## Comprehensive References

For deep technical details, see:
- **[docs/architecture/](docs/architecture/)** - Complete technical architecture
- **[docs/agents/](docs/agents/)** - Detailed agent behaviors and workflows
- **[README.md](README.md)** - Project overview

Legacy comprehensive documents are preserved in **[docs/archive/](docs/archive/)**:
- `ARCHITECTURE.md`, `FUNCTIONALITY.md`, `DEPENDENCIES.md`

---

**Last Updated**: 2025-01-22  
**Structure**: Progressive disclosure for efficient AI agent navigation
