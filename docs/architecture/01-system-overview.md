# System Overview

> **Purpose**: High-level architecture and core philosophy of the Autonomous Coding Agent system.

---

## 1.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                            │
│                    (CLI - Click + Rich)                          │
│   Commands: run, history, resume, cancel                         │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR LAYER                           │
│                   (State Machine Controller)                      │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │   INIT     │→ │  PLANNING  │→ │   CODING   │→ │ VALIDATING│  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
│                                         │              │          │
│                                         ▼              ▼          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  SUCCESS   │← │  TESTING   │← │  CODING    │← │REFLECTING│  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
│                                         ▲              │          │
│                                         └──────────────┘          │
│                                         (Iteration Loop)          │
└────────┬──────────────┬──────────────┬──────────────┬────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────┐ │
│  │   Planner   │  │    Coder    │  │   Tester    │  │Reflec│ │
│  │    Agent    │  │    Agent    │  │    Agent    │  │ tor  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬──┘ │
└─────────┼─────────────────┼─────────────────┼─────────────┼────┘
          │                 │                 │             │
          └─────────────────┴─────────────────┴─────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      LLM INTERFACE LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  OpenAI Client (with retry logic + token tracking)      │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Tool Definitions (create_file, read_file, etc.)        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  Prompt Templates (system prompts for each agent)       │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬────────────────┐
         │               │               │                │
         ▼               ▼               ▼                ▼
┌───────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐
│  MEMORY       │ │  SANDBOX   │ │  TESTING   │ │   PROJECT    │
│  SYSTEM       │ │  SYSTEM    │ │  SYSTEM    │ │  SCAFFOLDING │
│               │ │            │ │            │ │              │
│ - DB Manager  │ │ - Docker   │ │ - Test Gen │ │ - Multi-      │
│ - Vector Store│ │ (Optional) │ │ - Test Run │ │   Language    │
│ - Pattern     │ │ - Safety   │ │ - Coverage │ │ Scaffolding   │
│   Matcher     │ │ - Resource │ │            │ │               │
│               │ │   Limits   │ │            │ │               │
└───────┬───────┘ └──────┬─────┘ └──────┬─────┘ └──────────────┘
        │                │               │
        ▼                ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DATA & EXECUTION LAYER                        │
│  ┌────────────────────────┐    ┌────────────────────────────┐   │
│  │  PostgreSQL + pgvector │    │  Execution Environment     │   │
│  │  - Tasks               │    │  - Docker (Optional)       │   │
│  │  - Iterations          │    │  - Local (Fallback)        │   │
│  │  - Failures (vectors)  │    │  - Isolated workspaces     │   │
│  │  - Patterns (vectors)  │    │  - Resource limits         │   │
│  │  - Metrics             │    │  - Security scanning       │   │
│  └────────────────────────┘    └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## 1.2 Core Philosophy

**"The difference between a chatbot and an agent is the loop."**

This system implements autonomous coding through:

1. **Goal-based operation**: Task descriptions, not prompts
2. **Iterative refinement**: Code → Test → Reflect → Code (loop)
3. **Learning from failure**: Vector similarity search for past solutions
4. **Safety-first execution**: Multi-layer sandboxing and validation
5. **Bounded autonomy**: 15-iteration circuit breaker

---

## Key Components

- **User Interface**: CLI with Click and Rich formatting
- **Orchestrator**: State machine controller with 15-iteration limit
- **Agents**: 4 specialized agents (Planner, Coder, Tester, Reflector)
- **LLM Interface**: OpenAI client with retry logic and token tracking
- **Memory System**: PostgreSQL + pgvector for learning from failures
- **Sandbox System**: Isolated execution environments (Docker optional)
- **Testing System**: Automatic test generation and execution
- **Project Scaffolding**: Multi-language project structure generation