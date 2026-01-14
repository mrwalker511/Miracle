"""Lightweight (non-LLM) test generation.

The system's primary test generation comes from the LLM-based Testing Agent.
This module provides a minimal fallback generator that can be used when the LLM
is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict


class TestGenerator:
    def generate_python_smoke_test(self, *, workspace: Path) -> str:
        test_file = "test_smoke.py"
        (workspace / test_file).write_text(
            "def test_smoke():\n    assert True\n",
            encoding="utf-8",
        )
        return test_file

    def generate_node_smoke_test(self, *, workspace: Path) -> str:
        test_dir = workspace / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = "test/smoke.test.js"
        (workspace / test_file).write_text(
            "const test = require('node:test');\n"
            "const assert = require('node:assert/strict');\n\n"
            "test('smoke', () => {\n  assert.equal(1 + 1, 2);\n});\n",
            encoding="utf-8",
        )
        return test_file

    def generate(self, *, workspace: Path, language: str) -> str:
        lang = str(language).lower()
        if lang in {"node", "javascript", "js"}:
            return self.generate_node_smoke_test(workspace=workspace)
        return self.generate_python_smoke_test(workspace=workspace)
