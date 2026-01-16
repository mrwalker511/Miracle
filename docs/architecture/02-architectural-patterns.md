# Architectural Patterns

> **Purpose**: Core design patterns used in the Autonomous Coding Agent system.

---

## 2.1 State Machine Pattern

**Implementation**: Finite State Machine (FSM)

```python
class OrchestrationState(Enum):
    INIT = "init"           # Initialize workspace, load config
    PLANNING = "planning"    # Decompose task, query memory
    CODING = "coding"        # Generate code via LLM + tools
    TESTING = "testing"      # Run tests in sandbox
    REFLECTING = "reflecting" # Analyze failures, plan fixes
    SUCCESS = "success"      # All tests passed
    FAILED = "failed"        # Max iterations reached
    PAUSED = "paused"        # User interrupted
```

**State Transition Rules**:

| Current State | Event | Next State | Condition |
|---------------|-------|------------|-----------|
| INIT | Workspace ready | PLANNING | Always |
| PLANNING | Plan created | CODING | Always |
| CODING | Code generated | TESTING | Always |
| TESTING | Tests passed | SUCCESS | pass_rate == 100% |
| TESTING | Tests failed | REFLECTING | pass_rate < 100% |
| REFLECTING | Analysis done | CODING | iteration < max_iterations |
| REFLECTING | Max iterations | FAILED | iteration >= max_iterations |
| * | User interrupt | PAUSED | Any time |

**Benefits**:
- **Predictable behavior**: State transitions are explicit
- **Debuggability**: Can inspect current state at any time
- **Resumability**: Can checkpoint and resume from any state
- **Testability**: Can test each state handler in isolation

---

## 2.2 Agent Pattern

**Implementation**: Specialized AI agents with single responsibilities

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, llm_client: LLMClient, config: Config):
        self.llm_client = llm_client
        self.config = config
        self.logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """
        Execute agent-specific logic.

        Args:
            context: Shared context from orchestrator

        Returns:
            Results to merge back into context
        """
        pass
```

**Agent Responsibilities**:

| Agent | Single Responsibility | Input | Output |
|-------|----------------------|-------|--------|
| **PlannerAgent** | Task decomposition | Task description | Implementation plan, subtasks |
| **CoderAgent** | Code generation | Plan + feedback | Code files |
| **TesterAgent** | Test generation + execution | Code files | Test results |
| **ReflectorAgent** | Failure analysis | Test failures | Error analysis + fix hypothesis |

**Communication**: Agents communicate via **shared context dictionary** managed by orchestrator (not direct agent-to-agent calls).

**Benefits**:
- **Separation of concerns**: Each agent does one thing well
- **Independent testing**: Mock the LLM, test agent logic
- **Extensibility**: Add new agents without modifying existing ones
- **Composability**: Orchestrator can reorder or skip agents

---

## 2.3 Tool Use Pattern

**Implementation**: LLM function calling (OpenAI API)

```python
# Tool definition (declarative)
CREATE_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "create_file",
        "description": "Create a new file with content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    }
}

# Tool handler (imperative)
class CoderAgent:
    def _handle_tool_call(self, tool_call, workspace: Path) -> dict:
        if tool_call.function.name == "create_file":
            args = json.loads(tool_call.function.arguments)
            return self._create_file(args["path"], args["content"], workspace)
```

**Available Tools**:
- `create_file(path, content)` - Write a new file
- `read_file(path)` - Read existing file
- `list_files()` - List workspace contents
- `delete_file(path)` - Remove a file (if implemented)

**Benefits**:
- **Structured output**: LLM generates valid JSON (not free text)
- **Type safety**: Parameters are validated before execution
- **Discoverability**: LLM sees tool descriptions and decides when to use
- **Extensibility**: Add new tools without changing prompts

---

## 2.4 Repository Pattern

**Implementation**: Abstraction layer over database operations

```python
class DatabaseManager:
    """Centralized database operations"""

    async def create_task(self, description: str, language: str) -> UUID:
        """Create a new task record"""

    async def update_task_status(self, task_id: UUID, status: str):
        """Update task status"""

    async def log_iteration(self, task_id: UUID, iteration_data: dict):
        """Log an iteration"""

    async def store_failure(self, task_id: UUID, error: dict):
        """Store a failure for learning"""
```

**Benefits**:
- **Testability**: Mock database without PostgreSQL
- **Flexibility**: Can swap database implementations
- **Query optimization**: Centralized place for query tuning
- **Transaction management**: Handle ACID properties consistently

---

## 2.5 Circuit Breaker Pattern

**Implementation**: Prevent infinite loops

```python
class Orchestrator:
    MAX_ITERATIONS = 15
    WARNING_THRESHOLD = 12

    async def run(self):
        while self.current_iteration < self.MAX_ITERATIONS:
            if self.current_iteration == self.WARNING_THRESHOLD:
                self.logger.warning(
                    "Approaching max iterations",
                    current=self.current_iteration,
                    max=self.MAX_ITERATIONS
                )

            next_state = await self._execute_current_state()

            if next_state in (OrchestrationState.SUCCESS, OrchestrationState.FAILED):
                break

            self.current_iteration += 1

        if self.current_iteration >= self.MAX_ITERATIONS:
            self.logger.error("Max iterations reached, task failed")
            return {"status": "failed", "reason": "max_iterations"}
```

**Benefits**:
- **Cost control**: Prevents runaway LLM API costs
- **Time bounds**: User knows task won't run forever
- **Graceful degradation**: Warning before hard stop