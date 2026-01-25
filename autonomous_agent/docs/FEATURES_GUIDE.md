# Miracle Features Guide

A practical guide to the advanced features that make Miracle smarter and safer.

---

## Quick Start

```bash
# Basic run (all safety features active by default)
python -m src.main run --task "Create a REST API for user management"

# With code review (catches bugs before testing)
python -m src.main run --task "..." --enable-review

# With security audit (finds vulnerabilities)
python -m src.main run --task "..." --enable-audit

# Both review phases
python -m src.main run --task "..." --enable-review --enable-audit
```

---

## What's New?

Miracle now includes 5 advanced patterns that make it work better:

| Feature | What It Does | When To Use |
|---------|-------------|-------------|
| **Reprompter** | Turns vague tasks into structured specs | Always on by default |
| **Context Hygiene** | Prevents memory overflow during long tasks | Automatic |
| **Execution Hooks** | Blocks dangerous commands | Automatic |
| **Code Reviewer** | Catches bugs before testing | Use `--enable-review` |
| **Security Auditor** | Finds security vulnerabilities | Use `--enable-audit` |

---

## 1. The Reprompter (Task Structuring)

### The Problem It Solves
Vague tasks lead to bad code. "Make a login system" could mean anything.

### How It Works
When you submit a task, Miracle analyzes it and may ask clarifying questions:

```
$ python -m src.main run --task "Add authentication"

Analyzing task for better structuring...

Some clarification would help:
  ? What authentication method? [password, oauth, jwt]: jwt
  ? Which framework are you using? [flask, fastapi, express]: fastapi

Task structured:
  Title: Add JWT authentication
  Goal: Implement JWT-based authentication for FastAPI
  Complexity: moderate
```

### When To Skip It
For very specific tasks, you can skip the analysis:

```bash
python -m src.main run --task "Fix the TypeError in utils.py line 23" --skip-reprompter
```

---

## 2. Context Hygiene (Memory Management)

### The Problem It Solves
Long-running tasks fill up the AI's memory. When memory gets full:
- Important details get lost
- The AI starts making mistakes
- Quality drops sharply

### How It Works
Miracle automatically monitors memory usage:

| Usage | Status | What Happens |
|-------|--------|--------------|
| < 50% | Healthy | Nothing, keep working |
| 50-75% | Warning | Start monitoring closely |
| 75-90% | Critical | Compress old context |
| > 90% | Overflow | Force compression |

**What gets preserved during compression:**
- Your original task and goal
- The current plan
- Recent errors (so it doesn't repeat mistakes)
- The latest code

**What gets trimmed:**
- Old test outputs
- Superseded code versions
- Lengthy stack traces

### Configuration
In `config/settings.yaml`:

```yaml
context_hygiene:
  max_tokens: 128000        # Your model's limit
  warning_threshold: 0.50   # When to start watching
  critical_threshold: 0.75  # When to compress
```

---

## 3. Execution Hooks (Safety Guardrails)

### The Problem They Solve
AI can accidentally run dangerous commands. Execution hooks catch these before they run.

### What Gets Blocked

**Dangerous Commands:**
- `rm -rf /` or `rm -rf ~` (delete everything)
- `sudo` commands
- Commands that send data to unknown servers
- Fork bombs

**Protected Files:**
- `.env` files (secrets)
- `credentials.json`
- `.ssh/` directory
- `.git/config`

### Example
```
$ Attempting: rm -rf ./node_modules/../..

[BLOCKED] Command matches dangerous pattern: rm -rf
Reason: Could delete files outside workspace
```

### What Happens When Blocked
- The command doesn't run
- A safe error is returned instead
- The AI tries a different approach

### Configuration
In `config/settings.yaml`:

```yaml
execution_hooks:
  enabled: true
  hooks:
    block_dangerous_commands:
      enabled: true
    protect_sensitive_files:
      enabled: true
    auto_format_code:
      enabled: true
```

---

## 4. Code Reviewer Agent

### The Problem It Solves
Testing catches runtime errors, but misses:
- Logic bugs that pass tests but do wrong things
- Poor code style
- Maintainability issues
- Performance problems

### How To Enable
```bash
python -m src.main run --task "..." --enable-review
```

### What It Checks

| Category | Examples |
|----------|----------|
| **Logic** | Off-by-one errors, wrong conditions, missing null checks |
| **Style** | Inconsistent naming, poor formatting |
| **Performance** | Unnecessary loops, memory leaks |
| **Maintainability** | Complex functions, missing docs |

### Output Example
```
Code Review Results:
  Overall Quality: acceptable

  Findings:
    [WARNING] logic: calculate_total() doesn't handle empty list
      Line 45 in pricing.py
      Suggestion: Add early return for empty input

    [SUGGESTION] style: Function 'x' should have a descriptive name
      Line 12 in utils.py

  Recommendation: Address the warning before proceeding
```

### Severity Levels

| Severity | Meaning | Blocks Progress? |
|----------|---------|------------------|
| Critical | Must fix now | Yes |
| Warning | Should fix | No (but noted) |
| Suggestion | Nice to have | No |
| Info | FYI | No |

---

## 5. Security Auditor Agent

### The Problem It Solves
Generated code might have security vulnerabilities that tests won't catch.

### How To Enable
```bash
python -m src.main run --task "..." --enable-audit
```

### What It Checks (OWASP Top 10)

| Vulnerability | Example |
|--------------|---------|
| **Injection** | SQL built with string concatenation |
| **Hardcoded Secrets** | `password = "admin123"` |
| **Path Traversal** | `open(user_input)` without validation |
| **Weak Crypto** | Using MD5 for passwords |
| **Command Injection** | `os.system(user_input)` |

### Output Example
```
Security Audit Results:
  Risk Level: HIGH

  Vulnerabilities:
    [HIGH] CWE-89 SQL Injection
      File: db.py, Line 34
      Code: f"SELECT * FROM users WHERE id = {user_id}"
      Impact: Attackers could read/modify database
      Fix: Use parameterized queries

    [MEDIUM] CWE-798 Hardcoded Credentials
      File: config.py, Line 12
      Code: API_KEY = "sk-abc123..."
      Fix: Use environment variables

  Immediate Actions:
    1. Replace SQL string formatting with parameterized queries
    2. Move API_KEY to environment variable
```

---

## Execution Flow

### Default Flow (no flags)
```
PLANNING → CODING → TESTING → [REFLECTING → CODING]*
                                        ↓
                                     SUCCESS
```

### With --enable-review
```
PLANNING → CODING → REVIEWING → TESTING → [REFLECTING → CODING]*
```

### With --enable-audit
```
PLANNING → CODING → AUDITING → TESTING → [REFLECTING → CODING]*
```

### With Both
```
PLANNING → CODING → REVIEWING → AUDITING → TESTING → [REFLECTING → CODING]*
```

---

## Common Scenarios

### Scenario 1: New Feature Development
Use both review and audit for production code:
```bash
python -m src.main run \
  --task "Add user authentication with password hashing" \
  --enable-review \
  --enable-audit
```

### Scenario 2: Quick Fix
Skip extra phases for simple fixes:
```bash
python -m src.main run \
  --task "Fix typo in error message in handlers.py line 42" \
  --skip-reprompter
```

### Scenario 3: Security-Critical Work
Audit is essential:
```bash
python -m src.main run \
  --task "Add payment processing endpoint" \
  --enable-audit
```

### Scenario 4: Code Cleanup
Review catches quality issues:
```bash
python -m src.main run \
  --task "Refactor the utils module for better readability" \
  --enable-review
```

---

## Troubleshooting

### "Context compaction triggered"
**What it means:** Memory was getting full, old data was compressed.
**Is it bad?:** Usually no. This is protective behavior.
**When to worry:** If it happens very early (iteration 2-3), your task might be too big. Break it into smaller pieces.

### "Command blocked by safety hook"
**What it means:** A command looked dangerous and was stopped.
**Is it bad?:** No, this is good! The AI will try another approach.
**When to worry:** If the block was wrong, you can disable specific hooks in `settings.yaml`.

### "Code review found critical issues"
**What it means:** The reviewer found bugs that should be fixed.
**What to do:** The AI will see this feedback and fix the issues in the next iteration.

### "Security audit found vulnerabilities"
**What it means:** Security issues were detected.
**What to do:** The AI will attempt to fix them. For critical vulnerabilities, review the fixes manually.

---

## Configuration Reference

### Full settings.yaml Options

```yaml
# How long before giving up
orchestrator:
  max_iterations: 15
  circuit_breaker:
    warning_threshold: 12   # Warn at iteration 12
    hard_stop: 15           # Stop at iteration 15

# Memory management
context_hygiene:
  max_tokens: 128000        # Model's context window
  warning_threshold: 0.50   # 50% = start monitoring
  critical_threshold: 0.75  # 75% = compress old data
  overflow_threshold: 0.90  # 90% = force compression

# Safety guardrails
execution_hooks:
  enabled: true             # Master switch
  hooks:
    block_dangerous_commands:
      enabled: true
    protect_sensitive_files:
      enabled: true
    auto_format_code:
      enabled: true
    token_budget:
      enabled: true
      max_tokens: 50000     # Per-iteration budget
    iteration_guard:
      enabled: true
      max_same_error: 3     # Warn if same error 3x

# Optional review phases
review_phases:
  code_review:
    enabled: false          # CLI flag overrides
    block_on_critical: true
  security_audit:
    enabled: false          # CLI flag overrides
    block_on_critical: true
```

---

## CLI Reference

```bash
python -m src.main run [OPTIONS]

Options:
  -t, --task TEXT           Task description
  -p, --problem-type TEXT   Problem type (default: general)
  -l, --language TEXT       Language (python, node)
  -m, --max-iterations INT  Max iterations (default: 15)
  -w, --workspace PATH      Workspace directory
  --enable-review           Enable code review phase
  --enable-audit            Enable security audit phase
  --skip-reprompter         Skip task structuring
```

---

## Summary

| Feature | Default | Flag to Change |
|---------|---------|----------------|
| Reprompter | ON | `--skip-reprompter` to disable |
| Context Hygiene | ON | Configure in settings.yaml |
| Execution Hooks | ON | Configure in settings.yaml |
| Code Review | OFF | `--enable-review` to enable |
| Security Audit | OFF | `--enable-audit` to enable |

**For most tasks:** Just run with default settings.
**For production code:** Add `--enable-review --enable-audit`.
**For quick fixes:** Add `--skip-reprompter`.
