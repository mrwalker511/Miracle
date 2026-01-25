"""Sandbox manager for executing generated code.

The project is designed to execute code in a Docker sandbox, but in many
environments (including CI) a Docker daemon may be unavailable. This module
supports both Docker and local subprocess execution.

Enhanced with execution hooks for safety guardrails:
- Pre-execution hooks validate commands before running
- Post-execution hooks process results
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.sandbox.docker_executor import DockerExecutor, DockerUnavailableError
from src.sandbox.resource_limits import ResourceLimits
from src.ui.logger import get_logger
from src.utils.execution_hooks import (
    HookRegistry,
    HookContext,
    HookResult,
    create_default_hook_registry,
)


class SandboxManager:
    """Execute tests and commands with optional sandboxing.

    Integrates execution hooks for safety:
    - Pre-execution: Validates commands, blocks dangerous operations
    - Post-execution: Processes output, auto-formats results
    """

    def __init__(self, config: Dict[str, Any], hook_registry: Optional[HookRegistry] = None):
        self.logger = get_logger("sandbox_manager")

        settings = (config or {}).get("settings", {})
        self.sandbox_config = settings.get("sandbox", {})

        self.engine = self.sandbox_config.get("engine", "local")
        self.limits = ResourceLimits.from_config(self.sandbox_config)

        network_cfg = self.sandbox_config.get("network", {})
        self.network_enabled = bool(network_cfg.get("enabled", False))

        self._docker: Optional[DockerExecutor] = None
        self._docker_capabilities: Dict[str, bool] = {}

        docker_cfg = self.sandbox_config.get("docker", {})
        self._python_image = docker_cfg.get("python_image", "python:3.11-slim")
        self._node_image = docker_cfg.get("node_image", "node:20-slim")

        # Execution hooks for safety guardrails
        hooks_config = settings.get("execution_hooks", {})
        if hook_registry is not None:
            self.hook_registry = hook_registry
        elif hooks_config.get("enabled", True):
            self.hook_registry = create_default_hook_registry()
        else:
            self.hook_registry = HookRegistry()  # Empty registry

        if self.engine == "docker":
            try:
                self._docker = DockerExecutor()
            except DockerUnavailableError as e:
                self.logger.warning("docker_unavailable_falling_back_to_local", error=str(e))
                self._docker = None

    def run_python_tests(self, *, workspace: Path, test_file: str) -> Dict[str, Any]:
        return self._run_tests(
            language="python",
            workspace=workspace,
            test_file=test_file,
        )

    def run_node_tests(self, *, workspace: Path, test_file: Optional[str] = None) -> Dict[str, Any]:
        return self._run_tests(
            language="node",
            workspace=workspace,
            test_file=test_file,
        )

    def _run_tests(
        self,
        *,
        language: str,
        workspace: Path,
        test_file: Optional[str],
    ) -> Dict[str, Any]:
        workspace = workspace.resolve()
        if not workspace.exists():
            return {
                "passed": False,
                "error_message": f"Workspace not found: {workspace}",
                "test_results": {},
            }

        if language == "python":
            if not test_file:
                return {
                    "passed": False,
                    "error_message": "No test file provided for Python execution",
                    "test_results": {},
                }
            cmd = ["python", "-m", "pytest", test_file, "-q", "--tb=short"]
            return self._run_command_and_parse_pytest(workspace, cmd, test_file)

        if language in {"node", "javascript", "js"}:
            if test_file:
                cmd = ["node", "--test", test_file]
            else:
                cmd = ["node", "--test"]
            return self._run_command_and_parse_node_test(workspace, cmd, test_file)

        return {
            "passed": False,
            "error_message": f"Unsupported language: {language}",
            "test_results": {},
        }

    def _run_command(self, *, workspace: Path, command: List[str]) -> subprocess.CompletedProcess:
        # Execute pre-execution hooks
        command_str = " ".join(command)
        hook_context = HookContext(
            operation='execute_command',
            agent_type='sandbox',
            iteration=0,
            target=str(workspace),
            content=command_str,
            metadata={'workspace': str(workspace), 'engine': 'docker' if self._docker else 'local'}
        )

        hook_result, modified_context, warnings = self.hook_registry.execute_pre_hooks(hook_context)

        # Log any warnings from hooks
        for warning in warnings:
            self.logger.warning("execution_hook_warning", message=warning)

        # Check if hook blocked the command
        if hook_result == HookResult.BLOCK:
            self.logger.error(
                "command_blocked_by_hook",
                command=command_str[:100],
            )
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="Command blocked by safety hook",
            )

        # Check if hook requires approval (for now, log and continue)
        if hook_result == HookResult.REQUIRE_APPROVAL:
            self.logger.warning(
                "command_requires_approval",
                command=command_str[:100],
            )
            # In a full implementation, this would pause for user approval
            # For now, we continue but log the warning

        self.logger.info(
            "sandbox_command_start",
            engine="docker" if self._docker else "local",
            command=command,
            workspace=str(workspace),
        )

        if self._docker:
            is_python = bool(command) and command[0] == "python"
            image = self._python_image if is_python else self._node_image

            if is_python and not self._docker_supports_pytest(image=image, workspace=workspace):
                self.logger.warning("docker_image_missing_pytest_falling_back_to_local", image=image)
            else:
                result = self._docker.run(
                    image=image,
                    command=command,
                    workspace=workspace,
                    network_enabled=self.network_enabled,
                    mem_limit_mb=self.limits.memory_mb,
                    cpu_count=self.limits.cpu_count,
                    timeout_seconds=self.limits.execution_timeout,
                )
                completed = subprocess.CompletedProcess(
                    args=command,
                    returncode=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                return self._execute_post_hooks(completed, workspace)

        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=self.limits.execution_timeout,
        )
        return self._execute_post_hooks(completed, workspace)

    def _execute_post_hooks(
        self,
        result: subprocess.CompletedProcess,
        workspace: Path
    ) -> subprocess.CompletedProcess:
        """Execute post-execution hooks on the result."""
        hook_context = HookContext(
            operation='command_completed',
            agent_type='sandbox',
            iteration=0,
            target=str(workspace),
            content={'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode},
            metadata={'workspace': str(workspace)}
        )

        _, modified_context, warnings = self.hook_registry.execute_post_hooks(hook_context)

        for warning in warnings:
            self.logger.info("post_execution_hook", message=warning)

        return result

    def _docker_supports_pytest(self, *, image: str, workspace: Path) -> bool:
        if image in self._docker_capabilities:
            return self._docker_capabilities[image]

        if not self._docker:
            self._docker_capabilities[image] = False
            return False

        try:
            result = self._docker.run(
                image=image,
                command=["python", "-c", "import pytest"],
                workspace=workspace,
                network_enabled=self.network_enabled,
                mem_limit_mb=self.limits.memory_mb,
                cpu_count=self.limits.cpu_count,
                timeout_seconds=30,
            )
            ok = result.exit_code == 0
        except Exception as e:  # pragma: no cover
            self.logger.warning("docker_pytest_probe_failed", image=image, error=str(e))
            ok = False

        self._docker_capabilities[image] = ok
        return ok

    def _run_command_and_parse_pytest(
        self,
        workspace: Path,
        command: List[str],
        test_file: str,
    ) -> Dict[str, Any]:
        try:
            result = self._run_command(workspace=workspace, command=command)
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "test_file": test_file,
                "error_message": f"Test execution timed out after {self.limits.execution_timeout} seconds",
                "test_results": {},
            }
        except Exception as e:
            return {
                "passed": False,
                "test_file": test_file,
                "error_message": str(e),
                "test_results": {},
            }

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        summary = self._parse_pytest_summary(output)

        return {
            "passed": result.returncode == 0,
            "test_file": test_file,
            "total": summary.get("total"),
            "passed_count": summary.get("passed"),
            "failed_count": summary.get("failed"),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error_message": result.stderr.strip() if result.returncode != 0 else None,
            "test_results": {"raw_output": output, "summary": summary},
        }

    def _run_command_and_parse_node_test(
        self,
        workspace: Path,
        command: List[str],
        test_file: Optional[str],
    ) -> Dict[str, Any]:
        try:
            result = self._run_command(workspace=workspace, command=command)
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "test_file": test_file,
                "error_message": f"Test execution timed out after {self.limits.execution_timeout} seconds",
                "test_results": {},
            }
        except Exception as e:
            return {
                "passed": False,
                "test_file": test_file,
                "error_message": str(e),
                "test_results": {},
            }

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return {
            "passed": result.returncode == 0,
            "test_file": test_file,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error_message": result.stderr.strip() if result.returncode != 0 else None,
            "test_results": {"raw_output": output},
        }

    def _parse_pytest_summary(self, output: str) -> Dict[str, int]:
        # Example summary lines:
        #  "1 passed in 0.01s"
        #  "2 failed, 1 passed in 0.05s"
        summary_line = None
        for line in reversed(output.splitlines()):
            if re.search(r"\bpassed\b|\bfailed\b|\berror\b", line) and "in" in line:
                summary_line = line.strip()
                break

        if not summary_line:
            return {}

        counts: Dict[str, int] = {}
        for part in summary_line.split(","):
            part = part.strip()
            m = re.match(r"(?P<count>\d+)\s+(?P<kind>passed|failed|error|errors|skipped|xfailed|xpassed)", part)
            if not m:
                continue
            kind = m.group("kind")
            if kind == "errors":
                kind = "error"
            counts[kind] = int(m.group("count"))

        if counts:
            counts["total"] = sum(v for k, v in counts.items() if k in {"passed", "failed", "error"})

        return counts
