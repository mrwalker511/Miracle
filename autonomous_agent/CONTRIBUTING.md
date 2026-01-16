# Contributing to Autonomous Coding Agent

Thank you for your interest in contributing to the Autonomous Coding Agent! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

- Be respectful and inclusive
- Welcome new contributors and help them learn
- Focus on constructive feedback
- Assume good intentions

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for PostgreSQL with pgvector)
- OpenAI API key (for testing)

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd autonomous_agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-timeout hypothesis

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start PostgreSQL
docker-compose up -d postgres

# Initialize database
python scripts/setup_db.py
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style (PEP 8 for Python)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_config_loader.py

# Run tests with verbose output
pytest -v
```

### 4. Check Code Quality

```bash
# Type checking (if using mypy)
mypy src/

# Linting
pylint src/

# Security check
bandit -r src/
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve issue description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and concise
- Use meaningful variable names

Example:

```python
def process_data(input_data: str, *, max_length: int = 100) -> dict:
    """Process input data and return structured result.

    Args:
        input_data: Raw input string to process
        max_length: Maximum allowed length for output

    Returns:
        Dictionary with processed results

    Raises:
        ValueError: If input_data is empty
    """
    if not input_data:
        raise ValueError("input_data cannot be empty")

    # Implementation here
    return {"result": processed}
```

### File Organization

- Keep related functionality together
- Use descriptive file names
- Maintain existing directory structure

```
src/
├── agents/          # AI agent implementations
├── llm/            # LLM integration
├── memory/          # Database and vector store
├── sandbox/         # Code execution
├── testing/         # Test generation/execution
├── ui/             # User interface
└── utils/           # Utilities
```

## Testing

### Writing Tests

- Use pytest for all tests
- Use hypothesis for property-based testing
- Write descriptive test names
- Test both happy paths and edge cases
- Mock external dependencies (OpenAI API, database)

Example:

```python
import pytest
from src.config_loader import ConfigLoader

class TestConfigLoader:
    def test_initialization(self):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader()
        assert loader.config_dir == Path("config")

    def test_load_yaml_valid(self, tmp_path):
        """Test loading valid YAML file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("key: value")

        loader = ConfigLoader(str(tmp_path))
        config = loader.load_yaml("test.yaml")

        assert config["key"] == "value"
```

### Test Coverage

Aim for >80% code coverage. Run:

```bash
pytest --cov=src --cov-report=term-missing
```

### Integration Tests

For features that require database or external services:

```bash
# Start services
docker-compose up -d

# Run integration tests
pytest tests/integration/
```

## Documentation

### Code Documentation

- Write clear docstrings for all public APIs
- Use Google or NumPy docstring style
- Include examples for complex functions

### README Updates

When adding features:
- Update the README if user-facing
- Add usage examples
- Document new configuration options

### Architecture Documentation

For significant changes:
- Update ARCHITECTURE.md
- Document design decisions
- Include diagrams if helpful

## Submitting Changes

### Pull Request Process

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to your fork
5. Create a Pull Request

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] PR description clearly explains changes

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Reporting Issues

When reporting issues, please include:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS)
- Logs/error messages
- Possible workarounds (if any)

## Questions?

- Open an issue for questions
- Check existing issues first
- Join discussions in PRs

---

Thank you for contributing to Autonomous Coding Agent! 🚀
