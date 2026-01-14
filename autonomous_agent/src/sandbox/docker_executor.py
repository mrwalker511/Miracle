"""Docker-based command execution for sandboxing.

This module is intentionally minimal: it provides a safe-ish execution wrapper that
can be used when a Docker daemon is available, while gracefully falling back to
non-Docker execution elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.ui.logger import get_logger


class DockerUnavailableError(RuntimeError):
    pass


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class DockerExecutor:
    """Executes commands inside a Docker container with a mounted workspace."""

    def __init__(self):
        self.logger = get_logger("docker_executor")

        try:
            import docker  # type: ignore

            self.client = docker.from_env()
        except Exception as e:  # pragma: no cover
            raise DockerUnavailableError(str(e)) from e

    def run(
        self,
        *,
        image: str,
        command: List[str],
        workspace: Path,
        env: Optional[Dict[str, str]] = None,
        network_enabled: bool = False,
        mem_limit_mb: int = 1024,
        cpu_count: float = 1.0,
        timeout_seconds: int = 300,
    ) -> CommandResult:
        workspace = workspace.resolve()
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace does not exist: {workspace}")

        self.logger.info(
            "docker_run_start",
            image=image,
            command=command,
            workspace=str(workspace),
            network_enabled=network_enabled,
        )

        volumes = {str(workspace): {"bind": "/workspace", "mode": "rw"}}
        mem_limit = f"{mem_limit_mb}m"
        nano_cpus = int(cpu_count * 1_000_000_000)

        try:
            container = self.client.containers.run(
                image=image,
                command=command,
                working_dir="/workspace",
                volumes=volumes,
                network_disabled=not network_enabled,
                mem_limit=mem_limit,
                nano_cpus=nano_cpus,
                detach=True,
                environment=env or {},
            )
        except Exception as e:  # pragma: no cover
            self.logger.error("docker_container_start_failed", error=str(e))
            raise

        try:
            result = container.wait(timeout=timeout_seconds)
            exit_code = int(result.get("StatusCode", 1))
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            self.logger.info(
                "docker_run_complete",
                exit_code=exit_code,
                stdout_len=len(stdout),
                stderr_len=len(stderr),
            )

            return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)

        finally:
            try:
                container.remove(force=True)
            except Exception:  # pragma: no cover
                pass
