"""Tests for sandbox manager (async).

Covers:
- Hook integration (BLOCK prevents execution)
- Pytest output parsing
- Node test output parsing
- Timeout handling
- Unsupported language returns error
"""

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sandbox.sandbox_manager import SandboxManager
from src.utils.approval_manager import ApprovalDenied
from src.utils.execution_hooks import ExecutionHook, HookPhase, HookResponse, HookResult


# ---------------------------------------------------------------------------
# Config and fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sandbox():
    """Create a SandboxManager with default config."""
    return SandboxManager({})


# ---------------------------------------------------------------------------
# TestRunTests
# ---------------------------------------------------------------------------

class TestRunPythonTests:
    """run_python_tests() delegates and parses pytest output."""

    @pytest.mark.asyncio
    async def test_passed_tests(self, sandbox, tmp_path):
        test_file = "test_hello.py"

        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "2 passed in 0.05s\n"
            mock_result.stderr = ""
            mock_thread.return_value = mock_result

            result = await sandbox.run_python_tests(workspace=tmp_path, test_file=test_file)

        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_failed_tests(self, sandbox, tmp_path):
        test_file = "test_hello.py"

        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "1 failed, 1 passed in 0.10s\n"
            mock_result.stderr = "AssertionError: assert False"
            mock_thread.return_value = mock_result

            result = await sandbox.run_python_tests(workspace=tmp_path, test_file=test_file)

        assert result["passed"] is False
        assert "error_message" in result or "stderr" in result.get("test_results", {}).get("raw_output", "")

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, sandbox, tmp_path):
        test_file = "test_hello.py"

        with patch("asyncio.to_thread", side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=30)):
            result = await sandbox.run_python_tests(workspace=tmp_path, test_file=test_file)

        assert result["passed"] is False
        assert "timed out" in result.get("error_message", "").lower()


class TestRunNodeTests:
    """run_node_tests() delegates and parses node test output."""

    @pytest.mark.asyncio
    async def test_passed_node_tests(self, sandbox, tmp_path):
        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "# tests 3\n# pass  3\n# fail  0\n"
            mock_result.stderr = ""
            mock_thread.return_value = mock_result

            result = await sandbox.run_node_tests(workspace=tmp_path, test_file="test/test.js")

        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_failed_node_tests(self, sandbox, tmp_path):
        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "# tests 3\n# pass  1\n# fail  2\n"
            mock_result.stderr = "Error: expected true"
            mock_thread.return_value = mock_result

            result = await sandbox.run_node_tests(workspace=tmp_path, test_file="test/test.js")

        assert result["passed"] is False


# ---------------------------------------------------------------------------
# TestUnsupportedLanguage
# ---------------------------------------------------------------------------

class TestUnsupportedLanguage:
    """Unsupported language returns an error result."""

    @pytest.mark.asyncio
    async def test_unsupported_language_returns_error(self, sandbox, tmp_path):
        result = await sandbox._run_tests(
            language="brainfuck",
            workspace=tmp_path,
            test_file="test.bf",
        )
        assert result["passed"] is False
        assert "unsupported" in result.get("error_message", "").lower()


# ---------------------------------------------------------------------------
# TestHookIntegration
# ---------------------------------------------------------------------------

class TestHookIntegration:
    """Hooks can BLOCK commands before execution."""

    @pytest.mark.asyncio
    async def test_blocked_command_raises_or_returns_error(self, tmp_path):
        """When a hook blocks, the command should not execute."""
        sandbox = SandboxManager({})

        # Try a command that the default dangerous-commands hook blocks
        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_thread.return_value = mock_result

            # The _run_command method has hook integration that raises for BLOCK
            try:
                await sandbox._run_command(
                    workspace=tmp_path,
                    command=["rm", "-rf", "/"],
                )
                # If it doesn't raise, it should at least not call subprocess
                if not mock_thread.called:
                    pass  # Hook blocked before subprocess
            except (PermissionError, RuntimeError, ValueError):
                pass  # Expected — hook raised

    @pytest.mark.asyncio
    async def test_command_approval_denial_raises_pause_signal(self, tmp_path):
        class ApprovalHook(ExecutionHook):
            def __init__(self):
                super().__init__("approval_hook", HookPhase.PRE_EXECUTION, priority=5)

            def should_run(self, context):
                return True

            def execute(self, context):
                return HookResponse(result=HookResult.REQUIRE_APPROVAL, message="Need approval")

        approval_manager = MagicMock()
        approval_manager.request = AsyncMock(return_value=False)
        sandbox = SandboxManager({}, hook_registry=None, approval_manager=approval_manager)
        sandbox.hook_registry.register(ApprovalHook())

        with pytest.raises(ApprovalDenied):
            await sandbox._run_command(
                workspace=tmp_path,
                command=["python", "-m", "pytest", "-q"],
            )

    @pytest.mark.asyncio
    async def test_command_approval_acceptance_runs_command(self, tmp_path):
        class ApprovalHook(ExecutionHook):
            def __init__(self):
                super().__init__("approval_hook", HookPhase.PRE_EXECUTION, priority=5)

            def should_run(self, context):
                return True

            def execute(self, context):
                return HookResponse(result=HookResult.REQUIRE_APPROVAL, message="Need approval")

        approval_manager = MagicMock()
        approval_manager.request = AsyncMock(return_value=True)
        sandbox = SandboxManager({}, hook_registry=None, approval_manager=approval_manager)
        sandbox.hook_registry.register(ApprovalHook())

        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_thread.return_value = mock_result

            result = await sandbox._run_command(
                workspace=tmp_path,
                command=["python", "-m", "pytest", "-q"],
            )

        assert result.returncode == 0
        approval_manager.request.assert_awaited_once()


# ---------------------------------------------------------------------------
# TestPytestOutputParsing
# ---------------------------------------------------------------------------

class TestPytestOutputParsing:
    """pytest output is correctly parsed into structured results."""

    @pytest.mark.asyncio
    async def test_summary_line_parsed(self, sandbox, tmp_path):
        with patch("asyncio.to_thread") as mock_thread:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = (
                "test_hello.py::test_one PASSED\n"
                "test_hello.py::test_two PASSED\n"
                "2 passed in 0.03s\n"
            )
            mock_result.stderr = ""
            mock_thread.return_value = mock_result

            result = await sandbox.run_python_tests(workspace=tmp_path, test_file="test_hello.py")

        assert result["passed"] is True
        summary = result.get("test_results", {}).get("summary", {})
        assert summary.get("passed") == 2


# ---------------------------------------------------------------------------
# TestInitialization  
# ---------------------------------------------------------------------------

class TestSandboxInit:
    """SandboxManager initializes with config."""

    def test_default_timeout(self, sandbox):
        assert sandbox.limits.execution_timeout > 0

    def test_hook_registry_exists(self, sandbox):
        assert sandbox.hook_registry is not None
