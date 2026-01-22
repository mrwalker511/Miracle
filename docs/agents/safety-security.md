# Safety & Security

Multi-layer security architecture for safe code execution.

---

## Overview

The system uses defense-in-depth with four security layers:

```
Generated Code
    ↓
[1] AST Scanning ← Block dangerous operations
    ↓
[2] Bandit SAST ← Security vulnerability scan
    ↓
[3] User Approval ← Human review for risky operations
    ↓
[4] Docker Sandbox ← Isolated execution environment (Optional)
```

---

## Layer 1: AST Scanning

**File**: `src/sandbox/safety_checker.py`

### What It Blocks

**Dangerous built-in functions**:
- `eval()` - Arbitrary code execution
- `exec()` - Arbitrary code execution
- `compile()` - Can be used to bypass restrictions
- `__import__()` - Dynamic imports can bypass blocklist

**Dangerous modules**:
- `os` - File system and process access
- `subprocess` - Shell command execution
- `pty` - Pseudo-terminal operations
- `socket` - Network access
- `sys` - System-level operations
- `importlib` - Dynamic imports
- `shutil` - File operations (can delete files)

### How It Works

```python
import ast

class SafetyChecker:
    """AST-based code safety checker."""
    
    DANGEROUS_IMPORTS = ["os", "subprocess", "pty", "socket", "sys"]
    DANGEROUS_FUNCTIONS = ["eval", "exec", "compile", "__import__"]
    
    def check_code(self, code: str) -> List[str]:
        """Check code for safety violations.
        
        Args:
            code: Python code to check
            
        Returns:
            List of violation messages (empty if safe)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        violations = []
        
        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_IMPORTS:
                        violations.append(f"Blocked import: {alias.name}")
            
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_FUNCTIONS:
                        violations.append(f"Blocked function: {node.func.id}")
        
        return violations
```

### Configuration

**File**: `config/safety_rules.yaml`

```yaml
blocked_imports:
  - os
  - subprocess
  - pty
  - socket
  - sys
  - importlib
  - shutil

blocked_functions:
  - eval
  - exec
  - compile
  - __import__

# Exceptions for specific use cases
allowed_imports:
  - os.path  # Read-only path operations allowed
```

---

## Layer 2: Bandit SAST

**Tool**: Bandit - Security linter for Python

### What It Checks

- SQL injection vulnerabilities
- Hardcoded passwords/secrets
- Use of insecure functions (`pickle`, `yaml.load`)
- Weak cryptography
- Shell injection
- Path traversal
- And 50+ other security patterns

### How It Works

```python
import subprocess
import json

class BanditScanner:
    """Run Bandit security scanner on code."""
    
    def scan_code(self, file_path: Path) -> dict:
        """Scan file with Bandit.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Scan results with severity and issues
        """
        result = subprocess.run(
            ["bandit", "-f", "json", str(file_path)],
            capture_output=True,
            text=True
        )
        
        scan_results = json.loads(result.stdout)
        return {
            "issues": scan_results.get("results", []),
            "severity_high": len([r for r in scan_results.get("results", []) if r["issue_severity"] == "HIGH"]),
            "severity_medium": len([r for r in scan_results.get("results", []) if r["issue_severity"] == "MEDIUM"]),
        }
```

### Configuration

**File**: `config/safety_rules.yaml`

```yaml
bandit:
  severity_threshold: "HIGH"  # Block HIGH, warn MEDIUM, allow LOW
  skip_tests: ["B101"]  # Skip assertion warnings in tests
  
# Severity levels:
# - HIGH: Block execution, require user approval
# - MEDIUM: Warn, allow execution
# - LOW: Log only
```

### Action Based on Severity

| Severity | Action |
|----------|--------|
| HIGH | Block execution, require user approval |
| MEDIUM | Warn in logs, allow execution |
| LOW | Log informational message |

---

## Layer 3: User Approval

**File**: `src/ui/approval_prompt.py`

### When Approval Required

1. **Network access**: Any HTTP/HTTPS requests
2. **Subprocess execution**: Running shell commands
3. **New dependencies**: Installing packages not in allowlist
4. **Safety violations**: AST or Bandit violations detected
5. **File operations outside workspace**: Path traversal attempts

### Approval Flow

```python
class ApprovalManager:
    """Manage user approval prompts."""
    
    async def request_approval(
        self,
        approval_type: str,
        details: dict
    ) -> bool:
        """Request user approval for risky operation.
        
        Args:
            approval_type: Type of operation (network, subprocess, etc.)
            details: Context about the operation
            
        Returns:
            True if approved, False if denied
        """
        # Show Rich CLI prompt
        console.print(Panel(
            f"⚠️  APPROVAL REQUIRED\n\n"
            f"Type: {approval_type}\n"
            f"Details: {details}\n\n"
            f"Continue? [Y/n]: ",
            style="yellow"
        ))
        
        response = input().strip().lower()
        approved = response in ["y", "yes", ""]
        
        # Store decision in database
        await self.db.store_approval(
            approval_type=approval_type,
            details=details,
            approved=approved,
            timestamp=datetime.now()
        )
        
        return approved
```

### Approval Examples

**Network Access**:
```
⚠️  APPROVAL REQUIRED
┌─────────────────────────────────────────────────────────────┐
│  Agent requests network access:                             │
│    • URL: https://api.example.com/data                      │
│    • Method: GET                                            │
│                                                             │
│  This could access external data or services.               │
│  Continue? [Y/n]:                                          │
└─────────────────────────────────────────────────────────────┘
```

**Dependency Installation**:
```
⚠️  APPROVAL REQUIRED
┌─────────────────────────────────────────────────────────────┐
│  Agent requests to install dependencies:                    │
│    • flask==3.0.0 ✓ (in allowlist)                         │
│    • flask-sqlalchemy==3.1.1 ✓ (in allowlist)              │
│                                                             │
│  Install manually: pip install flask flask-sqlalchemy       │
│  Continue after installation? [Y/n]:                        │
└─────────────────────────────────────────────────────────────┘
```

**Safety Violation**:
```
⚠️  SAFETY VIOLATION
┌─────────────────────────────────────────────────────────────┐
│  Code contains blocked operation: 'subprocess.run'          │
│                                                             │
│  Location: app.py line 15                                   │
│  Code: subprocess.run(['ls', '-la'])                        │
│                                                             │
│  This could execute arbitrary shell commands.               │
│  Review code and approve? [Y/n]:                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 4: Docker Sandbox (Optional)

**File**: `src/sandbox/docker_executor.py`

Docker sandboxing provides the highest level of isolation but is optional. If Docker is not available, the system can fall back to local execution (with reduced isolation).

### Container Configuration

```python
container_config = {
    # Resource limits
    "cpu_period": 100000,
    "cpu_quota": 100000,  # 1 CPU core
    "mem_limit": "1g",    # 1GB RAM
    
    # Security
    "network_disabled": True,
    "read_only": True,
    "security_opt": ["no-new-privileges"],
    "cap_drop": ["ALL"],
    
    # User
    "user": "1000:1000",  # Non-root
    
    # Filesystem
    "volumes": {
        str(workspace): {"bind": "/workspace", "mode": "rw"}
    },
    "working_dir": "/workspace",
    
    # Timeout
    "timeout": 300  # 5 minutes
}
```

### What It Prevents

- **CPU/RAM exhaustion**: Resource limits enforced
- **Network access**: Disabled by default
- **Filesystem access**: Only workspace directory accessible
- **Privilege escalation**: Non-root user, no new privileges
- **Infinite loops**: 5-minute timeout
- **Fork bombs**: Process limits

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 sandbox_user

# Install minimal dependencies
RUN pip install pytest hypothesis

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox_user

# Default command
CMD ["/bin/bash"]
```

---

## Dependency Allowlist

**File**: `config/allowed_deps.json`

### Purpose

Curated list of safe, approved packages that can be installed without approval.

### Structure

```json
{
  "packages": {
    "flask": {
      "versions": ["2.3.0", "3.0.0"],
      "reason": "Popular web framework, widely used"
    },
    "requests": {
      "versions": ["2.31.0"],
      "reason": "HTTP library, requires network approval at runtime",
      "requires_approval_for": ["network"]
    },
    "numpy": {
      "versions": ["1.24.0", "1.25.0"],
      "reason": "Scientific computing, no I/O"
    }
  },
  "blocked_packages": {
    "pickle": "Arbitrary code execution via deserialization",
    "eval": "Code injection",
    "os": "System access"
  }
}
```

### Usage

```python
class DependencyManager:
    """Manage dependency installation and approval."""
    
    def __init__(self, allowlist_path: Path):
        with open(allowlist_path) as f:
            self.allowlist = json.load(f)
    
    def check_dependency(self, package: str, version: str) -> tuple[bool, str]:
        """Check if dependency is allowed.
        
        Args:
            package: Package name
            version: Package version
            
        Returns:
            (allowed, reason)
        """
        # Check if blocked
        if package in self.allowlist["blocked_packages"]:
            reason = self.allowlist["blocked_packages"][package]
            return False, f"Blocked: {reason}"
        
        # Check if in allowlist
        if package in self.allowlist["packages"]:
            allowed_versions = self.allowlist["packages"][package]["versions"]
            if version in allowed_versions:
                return True, "In allowlist"
            else:
                return False, f"Version {version} not approved"
        
        # Unknown package - requires approval
        return False, "Not in allowlist, requires approval"
```

---

## Security Checklist

Before committing code that executes user-generated code:

- [ ] AST scanning blocks eval, exec, __import__
- [ ] Bandit scan passes (no HIGH severity issues)
- [ ] User approval implemented for network/subprocess
- [ ] Docker sandboxing with resource limits (if enabled)
- [ ] Path validation prevents directory traversal
- [ ] Input sanitization for file paths and commands
- [ ] No secrets logged (API keys, passwords redacted)
- [ ] Dependencies checked against allowlist
- [ ] Tests verify security controls work
- [ ] Documentation updated with security implications

---

## Common Security Patterns

### Path Validation

```python
def validate_path(path: str, workspace: Path) -> Optional[str]:
    """Validate path is within workspace.
    
    Args:
        path: Path to validate
        workspace: Workspace root
        
    Returns:
        Error message if invalid, None if valid
    """
    # Resolve to absolute path
    file_path = workspace / path
    
    try:
        resolved = file_path.resolve()
    except (OSError, RuntimeError) as e:
        return f"Invalid path: {e}"
    
    # Check if within workspace
    if not resolved.is_relative_to(workspace.resolve()):
        return "Path must be within workspace"
    
    return None
```

### Input Sanitization

```python
def sanitize_command_arg(arg: str) -> str:
    """Sanitize argument for command execution.
    
    Args:
        arg: Command argument
        
    Returns:
        Sanitized argument
    """
    # Remove shell metacharacters
    dangerous_chars = [";", "&", "|", ">", "<", "`", "$", "(", ")", "{", "}"]
    
    for char in dangerous_chars:
        if char in arg:
            raise ValueError(f"Dangerous character in argument: {char}")
    
    return arg
```

### Secret Redaction

```python
import re

def redact_secrets(text: str) -> str:
    """Redact secrets from log messages.
    
    Args:
        text: Text potentially containing secrets
        
    Returns:
        Text with secrets redacted
    """
    # Redact API keys (common patterns)
    text = re.sub(r"sk-[a-zA-Z0-9]{32,}", "[REDACTED_API_KEY]", text)
    
    # Redact passwords
    text = re.sub(r"password['\"]?\s*[:=]\s*['\"]?([^'\"\s]+)", "password=[REDACTED]", text, flags=re.IGNORECASE)
    
    # Redact tokens
    text = re.sub(r"token['\"]?\s*[:=]\s*['\"]?([^'\"\s]+)", "token=[REDACTED]", text, flags=re.IGNORECASE)
    
    return text
```

---

## Incident Response

### If Security Violation Occurs

1. **Stop execution immediately**
2. **Log full context** (what was attempted, by which agent, in which iteration)
3. **Notify user** with details
4. **Mark task as FAILED**
5. **Store incident** in database for analysis
6. **Review and update** safety rules

### Monitoring

Track security metrics:
- Safety violations per task
- Approval request rate
- Blocked operations by type
- Container escape attempts (should be zero)

---

## For More Information

- **Architecture**: See [Architecture](architecture.md)
- **Sandbox implementation**: See `src/sandbox/`
- **Configuration**: See `config/safety_rules.yaml`
