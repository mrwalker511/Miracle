# Agent Documentation

Progressive disclosure documentation for AI agents working on the Miracle autonomous coding agent.

---

## 📖 Documentation Structure

```
AGENTS.md (root - 58 lines)
  ↓ Start here for essentials
  ↓
docs/agents/
├── getting-started.md (189 lines)         # Setup & first run
├── architecture.md (283 lines)            # System design & patterns
├── development-workflows.md (509 lines)   # Common tasks & workflows
├── code-conventions.md (543 lines)        # Patterns & best practices
├── agent-behaviors.md (455 lines)         # Planner/Coder/Tester/Reflector
├── safety-security.md (547 lines)         # Multi-layer security
├── memory-learning.md (628 lines)         # Vector DB & learning
└── testing-strategy.md (646 lines)        # Testing approaches
```

**Total**: 58 lines (root) + 3,800 lines (topic files) = ~3,858 lines  
**Organization**: Progressive disclosure - read only what you need

---

## 🎯 Quick Navigation

### I want to...

**Get started working on the codebase**  
→ Read [getting-started.md](getting-started.md) for setup and project structure

**Understand how the system works**  
→ Read [architecture.md](architecture.md) for state machine and components

**Implement a new feature**  
→ Read [development-workflows.md](development-workflows.md) for common tasks

**Write code that fits the patterns**  
→ Read [code-conventions.md](code-conventions.md) for patterns and anti-patterns

**Understand how agents work**  
→ Read [agent-behaviors.md](agent-behaviors.md) for Planner/Coder/Tester/Reflector

**Ensure my code is secure**  
→ Read [safety-security.md](safety-security.md) for security layers and checklist

**Work with the memory system**  
→ Read [memory-learning.md](memory-learning.md) for vector search and patterns

**Write tests**  
→ Read [testing-strategy.md](testing-strategy.md) for unit/integration/e2e testing

---

## 📊 Documentation Metrics

### Coverage by Topic

| Topic | Lines | Focus |
|-------|-------|-------|
| Root (AGENTS.md) | 58 | Essential commands & links |
| Getting Started | 189 | Setup, installation, verification |
| Architecture | 283 | State machine, components, data flow |
| Development Workflows | 509 | Adding tools/states, bug fixes |
| Code Conventions | 543 | Patterns, async, DB, logging |
| Agent Behaviors | 455 | Planner, Coder, Tester, Reflector |
| Safety & Security | 547 | AST, Bandit, approval, Docker |
| Memory & Learning | 628 | Vector DB, patterns, failures |
| Testing Strategy | 646 | Unit, integration, e2e, coverage |

### Reading Time Estimates

- **Root (AGENTS.md)**: 2 minutes
- **Any single topic file**: 10-20 minutes
- **All topic files**: 2-3 hours
- **With comprehensive references**: 5-6 hours

---

## 🔄 Progressive Disclosure in Action

### Level 1: Essential (2 min)
Read `AGENTS.md` only
- Commands (pytest, black, mypy, flake8)
- Requirements (Python 3.11, PEP 8, type hints, async)
- Links to deeper topics

### Level 2: Getting Started (15 min)
Read `AGENTS.md` + `getting-started.md`
- Setup instructions
- Project structure
- Run your first task
- Verify installation

### Level 3: Implementation (1 hour)
Add relevant topic files:
- `development-workflows.md` - How to add features
- `code-conventions.md` - How to write code
- `testing-strategy.md` - How to test

### Level 4: Deep Understanding (3 hours)
Read all topic files:
- Complete understanding of system
- All patterns and conventions
- Security considerations
- Testing strategies

### Level 5: Comprehensive (6 hours)
Add comprehensive references:
- `ARCHITECTURE.md` - Complete technical architecture
- `FUNCTIONALITY.md` - System behavior details
- `DEPENDENCIES.md` - All dependencies and setup
- Source code exploration

---

## 🎨 Design Principles

### 1. Progressive Disclosure
Information revealed gradually based on need. Essential info first, details on-demand.

### 2. Topic-Based Organization
Navigate by what you want to accomplish, not by document type.

### 3. Single Source of Truth
Each concept documented once, linked from multiple places.

### 4. Actionable Content
Every section should be immediately useful. No vague advice.

### 5. Focused Files
Each file covers one topic (200-650 lines), not monolithic documents.

### 6. Clear Links
Extensive cross-linking between related topics.

---

## 🔗 Relationship to Other Docs

### Complementary (Unchanged)

**Comprehensive References** (for deep dives):
- `ARCHITECTURE.md` - Complete technical architecture (409 lines)
- `FUNCTIONALITY.md` - System behavior and flows (560+ lines)
- `DEPENDENCIES.md` - Setup and configuration (detailed)
- `README.md` - Project overview

**Historical Archives**:
- `docs/archive/AGENT-EXECUTION.md` - Legacy execution guide
- `docs/archive/AGENT-PLANNING.md` - Legacy planning guide
- `docs/archive/autonomous_coding_agent_handoff.md` - Legacy handoff doc

### Hierarchy

```
README.md (project overview)
   ↓
AGENTS.md (agent entry point)
   ↓
docs/agents/*.md (focused topics)
   ↓
ARCHITECTURE.md, FUNCTIONALITY.md (comprehensive references)
   ↓
Source code (implementation)
```

---

## 🚀 For New Contributors

**First time here?**

1. Read [AGENTS.md](../../AGENTS.md) (2 min)
2. Run through [getting-started.md](getting-started.md) setup (30 min)
3. Read [architecture.md](architecture.md) to understand the system (20 min)
4. Pick a task from issues
5. Read relevant topic files as needed:
   - [development-workflows.md](development-workflows.md) for implementation
   - [code-conventions.md](code-conventions.md) for patterns
   - [testing-strategy.md](testing-strategy.md) for tests

**That's it!** You're ready to contribute.

---

## 📝 Maintenance

### When to Update This Documentation

**Update `AGENTS.md`**:
- Essential commands change (rare)
- New required dependencies (rare)

**Update topic files**:
- New patterns emerge
- Common tasks added
- Architecture changes
- Security requirements change

**Don't update**:
- For minor bug fixes
- For implementation details (document in source)
- For temporary workarounds

### How to Update

1. **Find the right file**: Which topic does this relate to?
2. **Update once**: Make the change in that topic file
3. **Add links**: If referenced from multiple places, link instead of duplicating
4. **Keep it actionable**: Remove vague advice, add specific examples

---

## 🎯 Success Metrics

Documentation is successful when:
- New contributors can get started in < 1 hour
- Common questions are answered in < 5 minutes
- Agents can find relevant info without reading everything
- Updates are easy (change one file, not many)
- No redundant information across files

---

**Structure**: Progressive disclosure  
**Created**: 2025-01-22  
**Maintained by**: Project contributors
