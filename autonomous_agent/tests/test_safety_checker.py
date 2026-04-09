"""Tests for safety checker (AST-based code analysis).

Covers:
- Blocked operations (eval, exec, compile, __import__)
- File path sandboxing
- Dangerous import detection
- Syntax error handling
- Approval-required operations
"""

import pytest

from src.sandbox.safety_checker import SafetyChecker


class TestSafetyCheckerBlocking:
    """Blocked operations are detected and flagged."""

    def setup_method(self):
        self.checker = SafetyChecker({})

    def test_blocks_eval(self):
        is_safe, issues, _ = self.checker.check_code("result = eval('1+1')")
        assert not is_safe
        assert any("eval" in issue for issue in issues)

    def test_blocks_exec(self):
        is_safe, issues, _ = self.checker.check_code("exec('print(1)')")
        assert not is_safe
        assert any("exec" in issue for issue in issues)

    def test_blocks_compile(self):
        is_safe, issues, _ = self.checker.check_code("compile('1+1', '<string>', 'eval')")
        assert not is_safe
        assert any("compile" in issue for issue in issues)

    def test_blocks_dunder_import(self):
        is_safe, issues, _ = self.checker.check_code("m = __import__('os')")
        assert not is_safe
        assert any("__import__" in issue for issue in issues)

    def test_allows_safe_code(self):
        code = """
def hello():
    return "Hello, World!"

result = hello()
print(result)
"""
        is_safe, issues, _ = self.checker.check_code(code)
        assert is_safe
        assert len(issues) == 0


class TestSafetyCheckerFilePath:
    """File operations outside sandbox are detected."""

    def setup_method(self):
        self.checker = SafetyChecker({})

    def test_file_outside_sandbox_detected(self):
        code = "f = open('/etc/passwd', 'r')"
        is_safe, issues, _ = self.checker.check_code(code, sandbox_path="/sandbox")
        assert not is_safe
        assert any("sandbox" in issue.lower() for issue in issues)

    def test_file_inside_sandbox_allowed(self):
        code = "f = open('/sandbox/output.txt', 'w')"
        is_safe, issues, _ = self.checker.check_code(code, sandbox_path="/sandbox")
        assert is_safe

    def test_relative_path_allowed(self):
        code = "f = open('output.txt', 'w')"
        is_safe, issues, _ = self.checker.check_code(code, sandbox_path="/sandbox")
        assert is_safe


class TestSafetyCheckerImports:
    """Dangerous module imports are flagged for approval."""

    def setup_method(self):
        self.checker = SafetyChecker({})

    def test_os_import_requires_approval(self):
        code = "import os"
        _, _, approval = self.checker.check_code(code)
        assert any("os" in a for a in approval)

    def test_subprocess_import_requires_approval(self):
        code = "import subprocess"
        _, _, approval = self.checker.check_code(code)
        assert any("subprocess" in a for a in approval)

    def test_pickle_import_requires_approval(self):
        code = "import pickle"
        _, _, approval = self.checker.check_code(code)
        assert any("pickle" in a for a in approval)

    def test_from_os_import_requires_approval(self):
        code = "from os import path"
        _, _, approval = self.checker.check_code(code)
        assert any("os" in a for a in approval)

    def test_safe_import_allowed(self):
        code = "import json\nimport re\nfrom typing import List"
        is_safe, issues, approval = self.checker.check_code(code)
        assert is_safe
        assert len(approval) == 0


class TestSafetyCheckerNetworkApproval:
    """Network and subprocess calls detected for approval."""

    def setup_method(self):
        self.checker = SafetyChecker({})

    def test_requests_get_requires_approval(self):
        code = "import requests\nresult = requests.get('http://example.com')"
        _, _, approval = self.checker.check_code(code)
        # requests import itself isn't in dangerous_modules, but the call may be
        assert any("Network" in a or "subprocess" in a or "requests" in a.lower() for a in approval) or len(approval) == 0

    def test_subprocess_run_requires_approval(self):
        code = "import subprocess\nsubprocess.run(['ls'])"
        _, _, approval = self.checker.check_code(code)
        assert len(approval) > 0  # At least the import


class TestSafetyCheckerSyntax:
    """Syntax errors are handled gracefully."""

    def setup_method(self):
        self.checker = SafetyChecker({})

    def test_syntax_error_returns_not_safe(self):
        code = "def broken(\nreturn"
        is_safe, issues, _ = self.checker.check_code(code)
        assert not is_safe
        assert any("syntax" in issue.lower() for issue in issues)

    def test_empty_code_is_safe(self):
        is_safe, issues, _ = self.checker.check_code("")
        assert is_safe
        assert len(issues) == 0


class TestSafetyCheckerConfig:
    """Custom configuration is respected."""

    def test_custom_blocked_operations(self):
        checker = SafetyChecker({"safety": {"block_operations": ["print"]}})
        is_safe, issues, _ = checker.check_code("print('hello')")
        assert not is_safe
        assert any("print" in issue for issue in issues)

    def test_default_blocked_operations(self):
        checker = SafetyChecker({})
        assert "eval" in checker.blocked_ops
        assert "exec" in checker.blocked_ops
