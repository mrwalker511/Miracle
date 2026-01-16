# Security Architecture

> **Purpose**: Security measures and threat mitigation strategies.

---

## 7.1 Threat Model

**Threats**:
1. **Arbitrary code execution**: Malicious code accessing host system
2. **Data exfiltration**: Code reading secrets or sensitive files
3. **Resource exhaustion**: Infinite loops consuming CPU/RAM
4. **Network abuse**: Making unauthorized external requests
5. **Dependency confusion**: Installing malicious packages

**Mitigations**:

| Threat | Mitigation | Layer |
|--------|-----------|-------|
| Arbitrary code execution | AST scanning + Docker isolation | 1 + 4 |
| Data exfiltration | Path validation + network disabled | 3 + 4 |
| Resource exhaustion | CPU/RAM/time limits in Docker | 4 |
| Network abuse | User approval + network disabled | 3 + 4 |
| Dependency confusion | Allowlist + manual approval | 3 |

---

## 7.2 AST Scanning Rules

```python
class SafetyChecker:
    # Blocked imports (never allowed)
    DANGEROUS_IMPORTS = [
        "os",           # File system access
        "subprocess",   # Execute shell commands
        "pty",          # Pseudo-terminal (shell escape)
        "socket",       # Network sockets
        "__builtin__",  # Python internals
        "__import__",   # Dynamic imports
        "ctypes",       # C bindings
        "pickle",       # Arbitrary code execution
    ]

    # Blocked function calls
    DANGEROUS_CALLS = [
        "eval",
        "exec",
        "compile",
        "open",  # Unless path is within workspace
    ]

    def check_code(self, code: str, workspace: Path) -> List[str]:
        """
        Scan code for dangerous operations.

        Returns:
            List of violation messages (empty if safe)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]

        violations = []
        violations.extend(self._check_imports(tree))
        violations.extend(self._check_function_calls(tree))
        violations.extend(self._check_file_operations(tree, workspace))

        return violations
```

---

## 7.3 Approval Workflow

```python
class ApprovalManager:
    def requires_approval(self, operation: str, details: dict) -> bool:
        """Check if operation requires user approval"""
        approval_rules = self.config.safety_rules.approval_required

        # Network operations always require approval
        if operation in ["network_request", "socket_connection"]:
            return True

        # Subprocess calls require approval
        if operation == "subprocess_call":
            # Unless it's a safe command (e.g., pytest)
            command = details.get("command", "")
            if command.startswith(("pytest", "python -m pytest")):
                return False
            return True

        # Installing dependencies requires approval
        if operation == "install_dependency":
            package = details.get("package", "")
            if package in self.config.allowed_dependencies:
                return True  # Still prompt, but mark as "recommended"
            return True

        return operation in approval_rules

    async def prompt_user(self, operation: str, details: dict) -> bool:
        """Prompt user for approval (blocking)"""
        from src.ui.approval_prompt import ApprovalPrompt

        prompt = ApprovalPrompt()
        approved = prompt.ask(
            operation=operation,
            details=details,
            safety_level="medium"  # or "high", "critical"
        )

        # Log decision
        await self.db_manager.log_approval(
            task_id=self.task_id,
            operation=operation,
            approved=approved,
            details=details
        )

        return approved
```

**Security Layers**:

1. **AST Scanning**: Static analysis before execution
2. **Bandit Integration**: Security vulnerability scanning
3. **User Approval**: Manual review for sensitive operations
4. **Docker Sandbox**: Containerized execution with resource limits
5. **Network Isolation**: No internet access by default
6. **Filesystem Restrictions**: Only workspace directory accessible