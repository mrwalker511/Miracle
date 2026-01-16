# Data Flow

> **Purpose**: How data moves through the Autonomous Coding Agent system.

---

## 4.1 Complete Task Execution Flow

```
[USER]
  │
  ├─> "Write a REST API for managing todos"
  │
  ▼
[CLI - main.py]
  │
  ├─> Parse command
  ├─> Validate input
  └─> Create task record in DB
  │
  ▼
[ORCHESTRATOR - State: INIT]
  │
  ├─> Create workspace directory
  ├─> Load configuration
  └─> Initialize context
  │
  ▼
[ORCHESTRATOR - State: PLANNING]
  │
  ├─> Call PlannerAgent.execute()
  │    │
  │    ├─> Embed task description
  │    ├─> Query vector DB for similar patterns
  │    ├─> Build LLM prompt with context
  │    ├─> Call OpenAI API
  │    └─> Parse response (plan with subtasks)
  │
  ├─> Store plan in context
  └─> Transition to CODING
  │
  ▼
[ORCHESTRATOR - State: CODING]  ◄──────────────┐
  │                                             │
  ├─> Call CoderAgent.execute()                │
  │    │                                        │
  │    ├─> Build prompt (plan + past feedback) │
  │    ├─> Call OpenAI with tools             │
  │    ├─> LLM calls create_file()            │
  │    ├─> Agent writes files to workspace     │
  │    └─> Return list of files created        │
  │                                             │
  ├─> Store code files in context             │
  └─> Transition to TESTING                    │
  │                                             │
  ▼                                             │
[ORCHESTRATOR - State: TESTING]                │
  │                                             │
  ├─> Call TesterAgent.execute()               │
  │    │                                        │
  │    ├─> Generate tests (LLM)                │
  │    ├─> Write test files                    │
  │    ├─> Create Docker container             │
  │    ├─> Run pytest in container             │
  │    ├─> Capture output                      │
  │    └─> Parse results                       │
  │                                             │
  ├─> Store test results in context            │
  │                                             │
  ├─> Check pass rate                          │
  │    │                                        │
  │    ├─> 100% passed? ─YES──> [SUCCESS] ✅   │
  │    │                                        │
  │    └─> Failed? ─NO──> Transition to REFLECTING
  │                                             │
  ▼                                             │
[ORCHESTRATOR - State: REFLECTING]             │
  │                                             │
  ├─> Call ReflectorAgent.execute()            │
  │    │                                        │
  │    ├─> Analyze test failures               │
  │    ├─> Embed error context                 │
  │    ├─> Query vector DB for similar failures│
  │    ├─> Build prompt with similar solutions │
  │    ├─> Call OpenAI API                     │
  │    └─> Generate fix hypothesis             │
  │                                             │
  ├─> Store failure in DB (with embedding)     │
  ├─> Store analysis in context                │
  ├─> Increment iteration counter              │
  │                                             │
  ├─> Check iteration count                    │
  │    │                                        │
  │    ├─> < 15? ─YES──> Transition to CODING ─┘
  │    │
  │    └─> >= 15? ─NO──> [FAILED] ❌
  │
  ▼
[DATABASE]
  │
  ├─> Update task status (success/failed)
  ├─> Log final metrics
  └─> Store completion timestamp
  │
  ▼
[USER]
  │
  └─> View results in terminal (Rich UI)
```

---

## 4.2 Memory Retrieval Flow

```
[Agent needs similar patterns]
  │
  ▼
[Generate embedding for query]
  │
  ├─> Query: "REST API with authentication"
  ├─> Call OpenAI Embeddings API
  └─> Receive 1536-dim vector
  │
  ▼
[Search vector database]
  │
  ├─> SQL: SELECT ... WHERE similarity > 0.7
  ├─> pgvector performs cosine similarity
  └─> Returns top 5 matches
  │
  ▼
[Filter and rank results]
  │
  ├─> Filter by similarity threshold (0.7)
  ├─> Rank by recency (newer = better)
  └─> Return to agent
  │
  ▼
[Agent uses context]
  │
  ├─> Include in LLM prompt
  ├─> "Similar past solution: ..."
  └─> LLM generates better code
```

---

## 4.3 Checkpoint and Resume Flow

```
[Checkpoint Trigger]
  │
  ├─> Every 5 iterations
  ├─> Before user interrupt (Ctrl+C)
  └─> On critical errors
  │
  ▼
[Serialize State]
  │
  ├─> Current state (CODING, TESTING, etc.)
  ├─> Iteration number
  ├─> Context dictionary (JSON)
  └─> Workspace path
  │
  ▼
[Store in Database]
  │
  ├─> UPDATE tasks SET checkpoint_state = ...
  └─> Commit transaction
  │
  ▼
[User resumes later]
  │
  ├─> Command: python -m src.main resume <task_id>
  │
  ▼
[Load Checkpoint]
  │
  ├─> Query: SELECT checkpoint_state FROM tasks WHERE id = ...
  ├─> Deserialize context
  └─> Restore orchestrator state
  │
  ▼
[Continue Execution]
  │
  └─> Resume from saved state
```