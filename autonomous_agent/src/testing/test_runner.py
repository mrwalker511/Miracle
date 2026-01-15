"""Test execution utilities.

The main agent uses :class:`~src.sandbox.sandbox_manager.SandboxManager` directly,
but these helpers provide a stable interface for running tests across multiple
runtimes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.sandbox.sandbox_manager import SandboxManager


class TestRunner:
    def __init__(self, config: Dict[str, Any]):
        self.sandbox = SandboxManager(config)

    def run(self, *, workspace: Path, language: str, test_file: Optional[str] = None) -> Dict[str, Any]:
        language_norm = str(language).lower()
        if language_norm in {"node", "javascript", "js"}:
            return self.sandbox.run_node_tests(workspace=workspace, test_file=test_file)

        if not test_file:
            return {
                "passed": False,
                "error_message": "No test file specified for Python runtime",
                "test_results": {},
            }

        return self.sandbox.run_python_tests(workspace=workspace, test_file=test_file)
