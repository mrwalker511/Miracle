"""Safety checker for code analysis using AST and Bandit."""

import ast
from typing import Dict, List, Tuple, Any
from pathlib import Path

from src.ui.logger import get_logger


class SafetyChecker:
    """Checks code safety using AST analysis and Bandit."""

    BLOCKED_OPERATIONS = [
        'eval', 'exec', 'compile', '__import__'
    ]

    REQUIRE_APPROVAL = [
        'requests.get', 'requests.post', 'requests.put', 'requests.delete',
        'urllib.request.urlopen', 'socket.connect', 'subprocess.run',
        'subprocess.Popen', 'subprocess.call'
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize safety checker.

        Args:
            config: Safety configuration
        """
        self.config = config.get('safety', {})
        self.logger = get_logger('safety_checker')

        self.blocked_ops = self.config.get('block_operations', self.BLOCKED_OPERATIONS)
        self.require_approval = self.config.get('require_approval', [])

    def check_code(
        self,
        code: str,
        sandbox_path: str = "/sandbox"
    ) -> Tuple[bool, List[str], List[str]]:
        """Check code for safety issues.

        Args:
            code: Code string to check
            sandbox_path: Allowed sandbox path

        Returns:
            Tuple of (is_safe, issues, approval_needed)
        """
        issues = []
        approval_needed = []

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.logger.error("syntax_error", error=str(e))
            return False, [f"Syntax error: {e}"], []

        # Walk the AST
        for node in ast.walk(tree):
            # Check function calls
            if isinstance(node, ast.Call):
                func_name = self._get_func_name(node)

                # Blocked operations
                if func_name in self.blocked_ops:
                    issues.append(f"Blocked operation: {func_name}()")
                    self.logger.warning("blocked_operation_found", function=func_name)

                # Operations requiring approval
                if any(func_name.startswith(req) for req in self.REQUIRE_APPROVAL):
                    approval_needed.append(f"Network/subprocess operation: {func_name}")
                    self.logger.info("approval_required", function=func_name)

                # Check file operations
                if func_name == 'open':
                    if not self._check_file_path_safe(node, sandbox_path):
                        issues.append("File operation outside sandbox detected")

            # Check imports
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self._check_imports(node, issues, approval_needed)

        is_safe = len(issues) == 0

        self.logger.info(
            "safety_check_completed",
            is_safe=is_safe,
            issue_count=len(issues),
            approval_count=len(approval_needed)
        )

        return is_safe, issues, approval_needed

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from call node.

        Args:
            node: AST Call node

        Returns:
            Function name as string
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle module.function calls
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return 'unknown'

    def _check_file_path_safe(self, node: ast.Call, sandbox_path: str) -> bool:
        """Check if file path is within sandbox.

        Args:
            node: AST Call node for open()
            sandbox_path: Allowed sandbox path

        Returns:
            True if safe, False otherwise
        """
        # Simple heuristic: check if first argument is a string literal
        if node.args and isinstance(node.args[0], ast.Constant):
            path_str = node.args[0].value
            if isinstance(path_str, str):
                # Check for absolute paths outside sandbox
                if path_str.startswith('/') and not path_str.startswith(sandbox_path):
                    return False
        return True

    def _check_imports(
        self,
        node: ast.AST,
        issues: List[str],
        approval_needed: List[str]
    ):
        """Check import statements.

        Args:
            node: Import node
            issues: List to append issues to
            approval_needed: List to append approval requests to
        """
        dangerous_modules = ['os', 'subprocess', 'pickle', 'marshal']

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_modules:
                    approval_needed.append(f"Import of dangerous module: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module in dangerous_modules:
                approval_needed.append(f"Import from dangerous module: {node.module}")

    def run_bandit(self, code_path: Path) -> List[Dict[str, Any]]:
        """Run Bandit security scanner on code.

        Args:
            code_path: Path to code file

        Returns:
            List of Bandit findings
        """
        try:
            import subprocess
            import json

            result = subprocess.run(
                ['bandit', '-f', 'json', str(code_path)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                data = json.loads(result.stdout)
                findings = data.get('results', [])

                self.logger.info(
                    "bandit_scan_completed",
                    finding_count=len(findings)
                )

                return findings

        except Exception as e:
            self.logger.error("bandit_scan_failed", error=str(e))

        return []
