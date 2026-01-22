# AGENTS.md

**Project**: Miracle - Autonomous Coding Agent  
**Implementation Language**: Python 3.11+  
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

**For this codebase (Python):**
- **Style**: PEP 8
- **Type hints**: Required on all public functions
- **Docstrings**: Required for all public functions
- **Async/await**: All agent methods and LLM calls must be async

**General principles (any language):**
- Follow established conventions for the target language
- Write tests for new functionality
- Document public interfaces
- Handle errors gracefully

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
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture
- **[FUNCTIONALITY.md](FUNCTIONALITY.md)** - System behavior and flows
- **[DEPENDENCIES.md](DEPENDENCIES.md)** - Setup and configuration
- **[README.md](README.md)** - Project overview

---

**Last Updated**: 2025-01-22  
**Structure**: Progressive disclosure for efficient AI agent navigation
