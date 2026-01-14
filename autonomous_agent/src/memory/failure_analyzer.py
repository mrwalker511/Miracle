"""Failure analysis helpers.

The reflection agent already performs error extraction and normalization, but
this module provides reusable logic (e.g. for post-processing test output).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class FailureInfo:
    error_message: str
    error_type: str
    error_signature: str
    stack_trace: str


class FailureAnalyzer:
    COMMON_ERROR_TYPES = [
        "ImportError",
        "ModuleNotFoundError",
        "AttributeError",
        "TypeError",
        "ValueError",
        "KeyError",
        "IndexError",
        "NameError",
        "RuntimeError",
        "SyntaxError",
        "IndentationError",
        "FileNotFoundError",
        "AssertionError",
    ]

    def extract(self, test_results: Dict[str, Any]) -> Optional[FailureInfo]:
        error_message = test_results.get("error_message") or test_results.get("stderr")
        stack_trace = test_results.get("stack_trace") or test_results.get("stderr") or ""

        if not error_message:
            raw = test_results.get("test_results")
            error_message = str(raw) if raw else ""

        if not error_message:
            return None

        error_type = self._extract_error_type(str(error_message))
        error_signature = self._create_error_signature(str(error_message), error_type)

        return FailureInfo(
            error_message=str(error_message),
            error_type=error_type,
            error_signature=error_signature,
            stack_trace=str(stack_trace),
        )

    def _extract_error_type(self, error_text: str) -> str:
        for et in self.COMMON_ERROR_TYPES:
            if et in error_text:
                return et
        return "UnknownError"

    def _create_error_signature(self, error_text: str, error_type: str) -> str:
        lines = error_text.split("\n")
        for line in lines:
            if error_type in line:
                normalized = re.sub(r'File ".*?", line \d+', "", line)
                normalized = re.sub(r"'[^']*?'", "'X'", normalized)
                return normalized.strip()

        for line in lines:
            if line.strip():
                return f"{error_type}: {line.strip()[:100]}"

        return f"{error_type}: Unknown error"
