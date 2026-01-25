"""Context Hygiene utilities for managing token usage and context quality.

Based on Claude Code Mastery patterns for:
- Context usage thresholds and warnings
- Context compaction to prevent rot
- Preservation rules for critical information
- "Lost in the middle" mitigation strategies
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.llm.token_counter import TokenCounter
from src.ui.logger import get_logger


class ContextHealthStatus(Enum):
    """Status indicators for context health."""
    HEALTHY = "healthy"           # < 50% of limit
    WARNING = "warning"           # 50-75% of limit
    CRITICAL = "critical"         # 75-90% of limit
    OVERFLOW = "overflow"         # > 90% of limit


@dataclass
class ContextThresholds:
    """Configurable thresholds for context management."""
    max_tokens: int = 128000          # Model context limit
    warning_threshold: float = 0.50   # 50% - start monitoring
    critical_threshold: float = 0.75  # 75% - consider compaction
    overflow_threshold: float = 0.90  # 90% - force compaction
    min_preserved_tokens: int = 4000  # Always keep this much for response


@dataclass
class PreservationRule:
    """Rule for preserving specific context across compaction."""
    name: str
    pattern: str  # Key pattern to match
    priority: int  # Higher = more important to preserve
    max_tokens: int = 2000  # Max tokens to preserve for this rule


@dataclass
class ContextSnapshot:
    """Snapshot of context state for tracking."""
    total_tokens: int
    status: ContextHealthStatus
    preserved_tokens: int
    compactable_tokens: int
    recommendation: str


class ContextHygieneManager:
    """Manages context health and prevents context rot.

    Key strategies implemented:
    1. Token counting and threshold monitoring
    2. Context compaction when thresholds exceeded
    3. Preservation rules for critical information
    4. Recency bias handling (keep recent context fresher)
    """

    def __init__(
        self,
        thresholds: Optional[ContextThresholds] = None,
        model: str = "gpt-4",
    ):
        """Initialize context hygiene manager.

        Args:
            thresholds: Custom thresholds or use defaults
            model: Model name for token counting
        """
        self.thresholds = thresholds or ContextThresholds()
        self.token_counter = TokenCounter(model)
        self.logger = get_logger('context_hygiene')

        # Default preservation rules (higher priority = must preserve)
        self.preservation_rules: List[PreservationRule] = [
            PreservationRule("task_description", "task_description", priority=100, max_tokens=500),
            PreservationRule("goal", "goal", priority=100, max_tokens=300),
            PreservationRule("current_error", "previous_errors", priority=90, max_tokens=1000),
            PreservationRule("plan", "plan", priority=80, max_tokens=800),
            PreservationRule("latest_code", "code_files", priority=70, max_tokens=4000),
            PreservationRule("test_results", "test_results", priority=60, max_tokens=1000),
        ]

        # Track context history for "lost in the middle" mitigation
        self._context_history: List[Dict[str, Any]] = []

    def analyze(self, context: Dict[str, Any]) -> ContextSnapshot:
        """Analyze current context health.

        Args:
            context: Current execution context

        Returns:
            ContextSnapshot with health status and recommendations
        """
        # Count total tokens
        context_str = json.dumps(context, default=str)
        total_tokens = self.token_counter.count_tokens(context_str)

        # Calculate preserved vs compactable
        preserved_tokens = self._count_preserved_tokens(context)
        compactable_tokens = total_tokens - preserved_tokens

        # Determine health status
        usage_ratio = total_tokens / self.thresholds.max_tokens
        if usage_ratio >= self.thresholds.overflow_threshold:
            status = ContextHealthStatus.OVERFLOW
            recommendation = "CRITICAL: Force context compaction immediately"
        elif usage_ratio >= self.thresholds.critical_threshold:
            status = ContextHealthStatus.CRITICAL
            recommendation = "Consider compacting context to prevent degradation"
        elif usage_ratio >= self.thresholds.warning_threshold:
            status = ContextHealthStatus.WARNING
            recommendation = "Monitor context size, approaching limits"
        else:
            status = ContextHealthStatus.HEALTHY
            recommendation = "Context size healthy"

        snapshot = ContextSnapshot(
            total_tokens=total_tokens,
            status=status,
            preserved_tokens=preserved_tokens,
            compactable_tokens=compactable_tokens,
            recommendation=recommendation,
        )

        self.logger.info(
            "context_analyzed",
            total_tokens=total_tokens,
            status=status.value,
            usage_percent=f"{usage_ratio*100:.1f}%"
        )

        return snapshot

    def compact(
        self,
        context: Dict[str, Any],
        target_reduction: float = 0.5,
        summarizer: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Any]:
        """Compact context to reduce token usage while preserving critical info.

        Args:
            context: Current context to compact
            target_reduction: Target reduction ratio (0.5 = reduce by 50%)
            summarizer: Optional function to summarize text (LLM call)

        Returns:
            Compacted context
        """
        self.logger.info("context_compaction_started", target_reduction=target_reduction)

        compacted = {}

        # Always preserve high-priority items
        for rule in sorted(self.preservation_rules, key=lambda r: -r.priority):
            if rule.pattern in context:
                value = context[rule.pattern]
                if isinstance(value, str):
                    # Truncate if exceeds rule limit
                    tokens = self.token_counter.count_tokens(value)
                    if tokens > rule.max_tokens:
                        # Truncate to fit
                        ratio = rule.max_tokens / tokens
                        truncate_at = int(len(value) * ratio)
                        value = value[:truncate_at] + "\n[...truncated...]"
                compacted[rule.pattern] = value

        # Handle code_files specially - keep latest version, summarize old
        if 'code_files' in context:
            compacted['code_files'] = self._compact_code_files(
                context['code_files'],
                summarizer
            )

        # Handle test_results - keep only latest failure info
        if 'test_results' in context:
            compacted['test_results'] = self._compact_test_results(
                context['test_results']
            )

        # Copy remaining small fields
        small_fields = ['task_id', 'iteration', 'problem_type', 'language', 'workspace']
        for field in small_fields:
            if field in context:
                compacted[field] = context[field]

        # Add compaction metadata
        compacted['_compaction_metadata'] = {
            'compacted_at_iteration': context.get('iteration', 0),
            'original_token_count': self.token_counter.count_tokens(
                json.dumps(context, default=str)
            ),
            'compacted_token_count': self.token_counter.count_tokens(
                json.dumps(compacted, default=str)
            ),
        }

        self.logger.info(
            "context_compaction_completed",
            original_tokens=compacted['_compaction_metadata']['original_token_count'],
            compacted_tokens=compacted['_compaction_metadata']['compacted_token_count'],
        )

        return compacted

    def apply_recency_bias(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply recency bias to mitigate "lost in the middle" phenomenon.

        LLMs tend to focus on the beginning and end of context, losing
        information in the middle. This method restructures context to
        put the most important/recent information at the boundaries.

        Args:
            context: Current context

        Returns:
            Restructured context with recency bias applied
        """
        # Structure: [GOAL/TASK] ... [OLD CONTEXT] ... [RECENT/IMPORTANT]
        restructured = {}

        # Beginning: Task definition (high attention)
        beginning_keys = ['goal', 'task_description', 'plan']
        for key in beginning_keys:
            if key in context:
                restructured[key] = context[key]

        # Middle: Less critical historical data
        middle_keys = ['dependencies', 'subtasks', '_compaction_metadata']
        for key in middle_keys:
            if key in context:
                restructured[key] = context[key]

        # End: Recent and actionable (high attention)
        end_keys = ['previous_errors', 'test_results', 'code_files', 'iteration']
        for key in end_keys:
            if key in context:
                restructured[key] = context[key]

        # Copy any remaining keys
        for key in context:
            if key not in restructured:
                restructured[key] = context[key]

        return restructured

    def suggest_compaction(self, snapshot: ContextSnapshot) -> bool:
        """Determine if compaction should be performed.

        Args:
            snapshot: Current context snapshot

        Returns:
            True if compaction is recommended
        """
        return snapshot.status in [
            ContextHealthStatus.CRITICAL,
            ContextHealthStatus.OVERFLOW
        ]

    def _count_preserved_tokens(self, context: Dict[str, Any]) -> int:
        """Count tokens in preserved (high-priority) context items."""
        preserved_tokens = 0

        for rule in self.preservation_rules:
            if rule.pattern in context:
                value = context[rule.pattern]
                value_str = json.dumps(value, default=str) if not isinstance(value, str) else value
                tokens = min(
                    self.token_counter.count_tokens(value_str),
                    rule.max_tokens
                )
                preserved_tokens += tokens

        return preserved_tokens

    def _compact_code_files(
        self,
        code_files: Dict[str, str],
        summarizer: Optional[Callable[[str], str]] = None
    ) -> Dict[str, str]:
        """Compact code files, keeping full latest version."""
        if not code_files:
            return {}

        compacted = {}

        for filename, content in code_files.items():
            # Truncate very large files
            tokens = self.token_counter.count_tokens(content)
            if tokens > 2000:
                # Keep first and last portions, truncate middle
                lines = content.split('\n')
                if len(lines) > 100:
                    kept_lines = lines[:50] + ['\n# [...middle truncated...]\n'] + lines[-50:]
                    compacted[filename] = '\n'.join(kept_lines)
                else:
                    compacted[filename] = content
            else:
                compacted[filename] = content

        return compacted

    def _compact_test_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compact test results, keeping only actionable information."""
        if not test_results:
            return {}

        # Keep only essential fields
        essential_fields = [
            'passed', 'error_message', 'error_type',
            'failed_tests', 'test_count'
        ]

        compacted = {
            k: v for k, v in test_results.items()
            if k in essential_fields
        }

        # Truncate long error messages
        if 'error_message' in compacted and isinstance(compacted['error_message'], str):
            if len(compacted['error_message']) > 500:
                compacted['error_message'] = compacted['error_message'][:500] + "..."

        return compacted


def create_context_hygiene_middleware(
    manager: ContextHygieneManager
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Create a middleware function for automatic context hygiene.

    This can be integrated into the orchestration loop to automatically
    manage context health.

    Args:
        manager: ContextHygieneManager instance

    Returns:
        Middleware function that processes context
    """
    def middleware(context: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = manager.analyze(context)

        if manager.suggest_compaction(snapshot):
            context = manager.compact(context)

        # Always apply recency bias for better LLM attention
        context = manager.apply_recency_bias(context)

        return context

    return middleware
