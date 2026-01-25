"""Failure analysis helpers.

The reflection agent already performs error extraction and normalization, but
this module provides reusable logic (e.g. for post-processing test output).

Enhanced with structured error logging patterns from Claude Code Mastery guide:
- Context state capture for debugging
- Triggering prompt tracking
- Failure mode classification
- Diagnosis information
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class FailureMode(Enum):
    """Classification of failure modes for better diagnosis."""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    RUNTIME_ERROR = "runtime_error"
    ASSERTION_FAILURE = "assertion_failure"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    DEPENDENCY_MISSING = "dependency_missing"
    LOGIC_ERROR = "logic_error"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class FailureInfo:
    """Basic failure information extracted from test results."""
    error_message: str
    error_type: str
    error_signature: str
    stack_trace: str


@dataclass
class StructuredFailureLog:
    """Enhanced failure log with full context for debugging and learning.

    Based on Claude Code Mastery error logging patterns:
    - Captures triggering context/prompt
    - Records full state at failure time
    - Classifies failure modes
    - Includes diagnosis and suggested fixes
    """
    # Core failure info
    error_message: str
    error_type: str
    error_signature: str
    stack_trace: str
    failure_mode: FailureMode

    # Context at failure time
    triggering_prompt: str = ""
    context_state: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    agent_type: str = ""

    # Code context
    code_files: Dict[str, str] = field(default_factory=dict)
    test_files: Dict[str, str] = field(default_factory=dict)

    # Diagnosis
    diagnosis: str = ""
    root_cause_hypothesis: str = ""
    suggested_fix: str = ""
    similar_failures: List[str] = field(default_factory=list)

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    task_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['failure_mode'] = self.failure_mode.value
        return data

    def to_json(self) -> str:
        """Serialize to JSON for logging."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_xml(self) -> str:
        """Generate XML-tagged format for LLM context.

        XML tagging helps LLMs parse structured failure information
        more reliably than plain text.
        """
        return f"""<failure_log>
  <error>
    <type>{self.error_type}</type>
    <message>{self._escape_xml(self.error_message)}</message>
    <signature>{self._escape_xml(self.error_signature)}</signature>
    <mode>{self.failure_mode.value}</mode>
  </error>
  <context>
    <iteration>{self.iteration}</iteration>
    <agent>{self.agent_type}</agent>
    <triggering_prompt>{self._escape_xml(self.triggering_prompt[:500])}</triggering_prompt>
  </context>
  <diagnosis>
    <root_cause>{self._escape_xml(self.root_cause_hypothesis)}</root_cause>
    <suggested_fix>{self._escape_xml(self.suggested_fix)}</suggested_fix>
  </diagnosis>
  <stack_trace>{self._escape_xml(self.stack_trace[:2000])}</stack_trace>
</failure_log>"""

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


class FailureAnalyzer:
    """Analyzes test failures and extracts structured information.

    Enhanced with failure mode classification and structured logging
    for better learning from past failures.
    """

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
        "TimeoutError",
        "MemoryError",
        "RecursionError",
    ]

    # Map error types to failure modes for classification
    ERROR_TO_MODE: Dict[str, FailureMode] = {
        "SyntaxError": FailureMode.SYNTAX_ERROR,
        "IndentationError": FailureMode.SYNTAX_ERROR,
        "ImportError": FailureMode.IMPORT_ERROR,
        "ModuleNotFoundError": FailureMode.DEPENDENCY_MISSING,
        "TypeError": FailureMode.TYPE_ERROR,
        "AttributeError": FailureMode.TYPE_ERROR,
        "ValueError": FailureMode.RUNTIME_ERROR,
        "KeyError": FailureMode.RUNTIME_ERROR,
        "IndexError": FailureMode.RUNTIME_ERROR,
        "NameError": FailureMode.RUNTIME_ERROR,
        "RuntimeError": FailureMode.RUNTIME_ERROR,
        "FileNotFoundError": FailureMode.RUNTIME_ERROR,
        "AssertionError": FailureMode.ASSERTION_FAILURE,
        "TimeoutError": FailureMode.TIMEOUT,
        "MemoryError": FailureMode.RESOURCE_LIMIT,
        "RecursionError": FailureMode.RESOURCE_LIMIT,
    }

    def extract(self, test_results: Dict[str, Any]) -> Optional[FailureInfo]:
        """Extract basic failure information from test results.

        Args:
            test_results: Dictionary containing test execution results

        Returns:
            FailureInfo if an error was found, None otherwise
        """
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

    def extract_structured(
        self,
        test_results: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        triggering_prompt: str = "",
    ) -> Optional[StructuredFailureLog]:
        """Extract structured failure log with full context.

        This enhanced extraction captures the full context at failure time,
        enabling better learning from failures and more effective debugging.

        Args:
            test_results: Dictionary containing test execution results
            context: Full execution context at failure time
            triggering_prompt: The prompt that led to the failing code

        Returns:
            StructuredFailureLog if an error was found, None otherwise
        """
        basic_info = self.extract(test_results)
        if not basic_info:
            return None

        context = context or {}
        failure_mode = self._classify_failure_mode(
            basic_info.error_type,
            basic_info.error_message
        )

        return StructuredFailureLog(
            error_message=basic_info.error_message,
            error_type=basic_info.error_type,
            error_signature=basic_info.error_signature,
            stack_trace=basic_info.stack_trace,
            failure_mode=failure_mode,
            triggering_prompt=triggering_prompt,
            context_state=self._sanitize_context(context),
            iteration=context.get('iteration', 0),
            agent_type=context.get('current_agent', ''),
            code_files=context.get('code_files', {}),
            test_files={'test': test_results.get('test_file', '')},
            task_id=str(context.get('task_id', '')),
        )

    def _classify_failure_mode(self, error_type: str, error_message: str) -> FailureMode:
        """Classify the failure into a mode for better diagnosis.

        Args:
            error_type: The type of error (e.g., 'TypeError')
            error_message: The full error message

        Returns:
            Classified FailureMode
        """
        # Check direct mapping first
        if error_type in self.ERROR_TO_MODE:
            return self.ERROR_TO_MODE[error_type]

        # Check for timeout patterns
        if any(word in error_message.lower() for word in ['timeout', 'timed out', 'exceeded']):
            return FailureMode.TIMEOUT

        # Check for resource limit patterns
        if any(word in error_message.lower() for word in ['memory', 'oom', 'killed', 'limit']):
            return FailureMode.RESOURCE_LIMIT

        # Check for dependency patterns
        if any(word in error_message.lower() for word in ['no module', 'not found', 'missing']):
            return FailureMode.DEPENDENCY_MISSING

        return FailureMode.UNKNOWN

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context for storage, removing large/sensitive data.

        Args:
            context: Raw execution context

        Returns:
            Sanitized context safe for logging
        """
        # Keys to preserve (small, useful for debugging)
        safe_keys = [
            'task_id', 'task_description', 'goal', 'problem_type',
            'language', 'iteration', 'plan', 'dependencies', 'subtasks'
        ]

        sanitized = {}
        for key in safe_keys:
            if key in context:
                value = context[key]
                # Truncate long strings
                if isinstance(value, str) and len(value) > 500:
                    sanitized[key] = value[:500] + "..."
                else:
                    sanitized[key] = value

        return sanitized

    def generate_diagnosis(
        self,
        failure_log: StructuredFailureLog,
        similar_failures: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a diagnosis for the failure based on patterns.

        Args:
            failure_log: The structured failure log
            similar_failures: Similar past failures from vector search

        Returns:
            Diagnosis string with suggested fixes
        """
        diagnosis_parts = []

        # Mode-specific diagnosis
        mode_diagnoses = {
            FailureMode.SYNTAX_ERROR: "Syntax error detected. Check for missing colons, parentheses, or incorrect indentation.",
            FailureMode.IMPORT_ERROR: "Import error. Verify the module exists and is properly installed.",
            FailureMode.TYPE_ERROR: "Type mismatch. Check argument types and return values.",
            FailureMode.ASSERTION_FAILURE: "Test assertion failed. Review expected vs actual values.",
            FailureMode.TIMEOUT: "Execution timed out. Check for infinite loops or inefficient algorithms.",
            FailureMode.RESOURCE_LIMIT: "Resource limit exceeded. Optimize memory usage or reduce data size.",
            FailureMode.DEPENDENCY_MISSING: "Missing dependency. Add to requirements or install package.",
        }

        if failure_log.failure_mode in mode_diagnoses:
            diagnosis_parts.append(mode_diagnoses[failure_log.failure_mode])

        # Add similar failure insights
        if similar_failures:
            diagnosis_parts.append(f"\nSimilar past failures ({len(similar_failures)} found):")
            for i, sf in enumerate(similar_failures[:3]):
                if sf.get('root_cause'):
                    diagnosis_parts.append(f"  {i+1}. {sf['root_cause'][:100]}")

        return "\n".join(diagnosis_parts) if diagnosis_parts else "No specific diagnosis available."

    def _extract_error_type(self, error_text: str) -> str:
        """Extract the error type from error text.

        Args:
            error_text: Raw error text

        Returns:
            Error type string
        """
        for et in self.COMMON_ERROR_TYPES:
            if et in error_text:
                return et
        return "UnknownError"

    def _create_error_signature(self, error_text: str, error_type: str) -> str:
        """Create a normalized error signature for matching.

        Args:
            error_text: Raw error text
            error_type: Extracted error type

        Returns:
            Normalized error signature
        """
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
