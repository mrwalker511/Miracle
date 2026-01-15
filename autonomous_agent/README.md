# Autonomous Coding Agent

An autonomous AI agent that writes code iteratively until tests pass, learning from failures using vector similarity.

## 🎯 Mission

Build an autonomous agent that:
- Accepts coding tasks as goals (not prompts)
- Writes code iteratively in a loop
- Generates and runs tests automatically
- Learns from failures using vector similarity
- Doesn't stop until code is functional or max iterations reached

**"The difference between a chatbot and an agent is the loop."**

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           ORCHESTRATOR                  │
│    (State Machine Controller)           │
│                                         │
│  INIT → PLANNING → CODING → TESTING    │
│              ↑            |              │
│              └─REFLECTING─┘              │
└────────┬─────┬──────┬─────┬────────────┘
         │     │      │     │
    ┌────▼┐ ┌──▼──┐ ┌▼───┐ ┌▼────────┐
    │PLAN │ │CODE │ │TEST│ │ REFLECT │
    │ NER │ │  R  │ │ ER │ │   OR    │
    └─────┘ └─────┘ └────┘ └─────────┘
         │     │      │     │
         └─────┴──────┴─────┴───────▶ MEMORY
                              (PostgreSQL + pgvector)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   cd autonomous_agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   # - OPENAI_API_KEY=your_key_here
   # - DB_PASSWORD=secure_password
   ```

4. **Start PostgreSQL with pgvector**
   ```bash
   docker-compose up -d postgres
   ```

5. **Initialize database**
   ```bash
   python scripts/setup_db.py
   ```

### Running a Task

Python task:
```bash
python -m src.main run --language python --task "Build a REST API for managing todo items with SQLite"
```

Node.js task:
```bash
python -m src.main run --language node --task "Build a Node.js CLI tool that prints the current time"
```

Or interactive mode:
```bash
python -m src.main run
```

### View Task History

```bash
python -m src.main history
```

## 📁 Project Structure

```
autonomous_agent/
├── config/                 # Configuration files (YAML)
│   ├── settings.yaml      # System settings
│   ├── database.yaml      # Database config
│   ├── openai.yaml        # OpenAI API config
│   ├── system_prompts.yaml # Agent prompts
│   └── allowed_deps.json  # Dependency allowlist
├── src/
│   ├── main.py           # CLI entry point
│   ├── orchestrator.py   # State machine controller
│   ├── config_loader.py  # Config management
│   ├── agents/           # Specialized agents
│   │   ├── planner.py    # Task decomposition
│   │   ├── coder.py      # Code generation
│   │   ├── tester.py     # Test generation & execution
│   │   └── reflector.py  # Error analysis
│   ├── llm/              # LLM interface
│   │   ├── openai_client.py  # Flexible OpenAI client
│   │   ├── tools.py          # Function calling tools
│   │   └── token_counter.py  # Usage tracking
│   ├── memory/           # Database & vector store
│   │   ├── db_manager.py     # PostgreSQL operations
│   │   └── vector_store.py   # Similarity search
│   ├── sandbox/          # Code execution
│   │   ├── safety_checker.py # AST + Bandit scanning
│   │   └── docker_executor.py # Sandbox management
│   ├── ui/               # User interface
│   │   ├── cli.py        # Rich terminal UI
│   │   └── logger.py     # Structured logging
│   └── utils/            # Utilities
│       ├── circuit_breaker.py # Prevent infinite loops
│       └── metrics_collector.py # Performance tracking
├── scripts/
│   ├── setup_db.py       # Database initialization
│   └── init_db.sql       # Schema definition
├── tests/                # Unit tests
├── sandbox/workspace/    # Generated code workspace
├── logs/                 # Structured JSON logs
├── docker-compose.yml    # PostgreSQL + pgvector
├── requirements.txt      # Python dependencies
└── README.md
```

## 🔧 Configuration

### Model Selection

Edit `config/openai.yaml` to use different models:

```yaml
models:
  planner: "gpt-4-turbo-preview"
  coder: "gpt-4-turbo-preview"
  tester: "gpt-4-turbo-preview"
  reflector: "gpt-4-turbo-preview"
  embedding: "text-embedding-3-large"
```

Supports any OpenAI model: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.

### Iteration Limits

Edit `config/settings.yaml`:

```yaml
orchestrator:
  max_iterations: 15
  circuit_breaker:
    warning_threshold: 12
    hard_stop: 15
```

### Safety Rules

Edit `config/settings.yaml`:

```yaml
safety:
  block_operations:
    - "eval"
    - "exec"
    - "compile"
```

## 🧠 How It Works

### The Loop

1. **PLANNING**: Agent analyzes the task, queries past patterns, creates subtasks
2. **CODING**: Agent writes code using available tools (create_file, read_file, etc.)
3. **TESTING**: Agent generates pytest tests (including hypothesis property tests) and executes them
4. **REFLECTING**: If tests fail, agent analyzes errors, searches for similar past failures, proposes fixes
5. **Loop**: Returns to CODING with hypothesis → repeat until tests pass or max iterations

### Learning from Failures

- Every failure is stored with a vector embedding
- When a new error occurs, vector similarity search finds similar past failures
- Agent uses past solutions to inform current fixes
- Successful patterns are stored for future tasks

### Safety

- **AST scanning**: Blocks dangerous operations (`eval`, `exec`, etc.)
- **Bandit integration**: Security vulnerability scanning
- **Sandbox isolation**: Code runs in restricted Docker containers
- **Dependency approval**: User must approve package installations

## 📊 Database Schema

PostgreSQL with pgvector extension:

- **tasks**: Main task tracking
- **iterations**: Detailed loop cycle logs
- **failures**: Error memory with embeddings
- **patterns**: Successful solution templates
- **metrics**: Performance data
- **approvals**: User decision tracking

## 🎯 Example Usage

### REST API Task

```bash
python -m src.main run -t "Create a Flask REST API for managing books with SQLite" -p web_app
```

### Data Processing Task

```bash
python -m src.main run -t "Build a script to parse CSV files and generate statistics" -p data_pipeline
```

### CLI Tool Task

```bash
python -m src.main run -t "Create a CLI tool for managing TODO items stored in JSON" -p cli_tool
```

## 🔍 Monitoring

### Logs

Structured JSON logs in `logs/agent.log`:

```json
{
  "timestamp": "2025-01-13T10:30:45.123Z",
  "level": "INFO",
  "task_id": "abc-123",
  "iteration": 3,
  "phase": "testing",
  "event": "test_execution_complete",
  "data": {"passed": 8, "failed": 2}
}
```

### Metrics

Track performance in database:
- Iteration duration
- Token usage per phase
- Test pass rate
- Error type frequency
- Pattern match effectiveness

## 🚧 Current Limitations

- **Languages**: Python and Node.js (JavaScript)
- **Testing**: pytest (Python) and node:test (Node.js)
- **Dependencies**: Manual installation required (no auto-install)
- **Sandbox**: Basic Docker isolation (can be enhanced)

## 🔮 Future Enhancements

- [ ] More languages (TypeScript, Go, etc.)
- [ ] Parallel execution of subtasks
- [ ] Cost optimization (model selection based on task complexity)
- [ ] Web UI dashboard
- [ ] Collaborative learning across agent instances
- [ ] Fine-tuning based on success metrics

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## 📧 Support

For issues and questions:
- GitHub Issues: [github.com/yourrepo/issues](https://github.com/yourrepo/issues)
- Documentation: See `docs/` folder

## 🙏 Acknowledgments

Built with:
- OpenAI API (GPT-4, text-embedding-3-large)
- PostgreSQL + pgvector
- Python 3.11+
- Rich (terminal UI)
- pytest + hypothesis (testing)

---

**Remember: "The difference between a chatbot and an agent is the loop."**
