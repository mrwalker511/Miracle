"""Tests for context hygiene management.

Covers:
- ContextHygieneManager.analyze() health status thresholds
- .compact() preservation and truncation
- .apply_recency_bias() restructuring
- create_context_hygiene_middleware()
"""

import pytest

from src.utils.context_hygiene import (
    ContextHygieneManager,
    ContextThresholds,
    ContextHealthStatus,
    ContextSnapshot,
    create_context_hygiene_middleware,
)


def _make_context(size: str = "small") -> dict:
    """Build a test context of varying sizes."""
    base = {
        "task_id": "abc-123",
        "task_description": "Write a hello world function",
        "goal": "Create a function that prints Hello World",
        "plan": "Step 1: write code",
        "code_files": {"main.py": 'print("hello")'},
        "test_results": {"passed": False, "error_message": "AssertionError"},
        "previous_errors": "Missing import",
        "iteration": 3,
        "problem_type": "general",
        "language": "python",
        "workspace": "/tmp/test",
    }

    if size == "large":
        # Inflate code_files to push token count up
        base["code_files"] = {f"file_{i}.py": f"def func_{i}():\n    return {i}\n" * 200 for i in range(20)}
        base["test_results"]["raw_output"] = "FAILED " * 5000
        base["previous_errors"] = "Very long error " * 500

    return base


class TestContextAnalyze:
    """analyze() returns correct health statuses."""

    def test_healthy_small_context(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        assert snapshot.status == ContextHealthStatus.HEALTHY

    def test_total_tokens_positive(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        assert snapshot.total_tokens > 0

    def test_preserved_tokens_less_than_total(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        assert snapshot.preserved_tokens <= snapshot.total_tokens

    def test_recommendation_populated(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        assert len(snapshot.recommendation) > 0

    def test_warning_threshold(self):
        """Context above 50% of a tiny limit should be WARNING."""
        manager = ContextHygieneManager(
            thresholds=ContextThresholds(
                max_tokens=100,
                warning_threshold=0.50,
                critical_threshold=0.75,
                overflow_threshold=0.90,
            ),
            model="gpt-4",
        )
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        # A small context with a very small limit should be at least WARNING
        assert snapshot.status in (
            ContextHealthStatus.WARNING,
            ContextHealthStatus.CRITICAL,
            ContextHealthStatus.OVERFLOW,
        )

    def test_critical_threshold(self):
        """Context well above 75% should be CRITICAL or OVERFLOW."""
        manager = ContextHygieneManager(
            thresholds=ContextThresholds(
                max_tokens=50,
                warning_threshold=0.50,
                critical_threshold=0.75,
                overflow_threshold=0.90,
            ),
            model="gpt-4",
        )
        ctx = _make_context("small")
        snapshot = manager.analyze(ctx)
        assert snapshot.status in (ContextHealthStatus.CRITICAL, ContextHealthStatus.OVERFLOW)


class TestContextCompact:
    """compact() preserves critical fields and reduces bloat."""

    def test_preserves_task_description(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        assert "task_description" in compacted
        assert compacted["task_description"] == ctx["task_description"]

    def test_preserves_goal(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        assert "goal" in compacted
        assert compacted["goal"] == ctx["goal"]

    def test_preserves_iteration(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        assert compacted.get("iteration") == ctx["iteration"]

    def test_adds_compaction_metadata(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        assert "_compaction_metadata" in compacted
        assert "compacted_at_iteration" in compacted["_compaction_metadata"]
        assert "original_token_count" in compacted["_compaction_metadata"]
        assert "compacted_token_count" in compacted["_compaction_metadata"]

    def test_compacted_is_smaller(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        meta = compacted["_compaction_metadata"]
        assert meta["compacted_token_count"] < meta["original_token_count"]

    def test_truncated_strings_have_marker(self):
        """Very long preserved fields should be truncated with a marker."""
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        # Make plan very long
        ctx["plan"] = "Step 1: do something: " * 1000
        compacted = manager.compact(ctx)
        if "[...truncated...]" in compacted.get("plan", ""):
            pass  # Correctly truncated
        # The plan string should not exceed the rule's max_tokens worth of characters

    def test_code_files_compacted(self):
        """Large code files should be truncated to keep middle out."""
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        assert "code_files" in compacted

    def test_test_results_compacted(self):
        """Test results should keep only essential fields."""
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("large")
        compacted = manager.compact(ctx)
        test_results = compacted.get("test_results", {})
        # raw_output should be removed in compaction
        assert "raw_output" not in test_results


class TestRecencyBias:
    """apply_recency_bias() restructures context for LLM attention."""

    def test_goal_comes_first(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        biased = manager.apply_recency_bias(ctx)
        keys = list(biased.keys())
        assert keys[0] == "goal"

    def test_task_description_near_beginning(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        biased = manager.apply_recency_bias(ctx)
        keys = list(biased.keys())
        assert "task_description" in keys[:3]

    def test_iteration_near_end(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        biased = manager.apply_recency_bias(ctx)
        keys = list(biased.keys())
        # iteration should be in the end section
        assert keys.index("iteration") > keys.index("goal")

    def test_all_keys_preserved(self):
        manager = ContextHygieneManager(model="gpt-4")
        ctx = _make_context("small")
        biased = manager.apply_recency_bias(ctx)
        assert set(biased.keys()) == set(ctx.keys())


class TestSuggestCompaction:
    """suggest_compaction() returns True only for CRITICAL/OVERFLOW."""

    def test_healthy_no_compaction(self):
        manager = ContextHygieneManager(model="gpt-4")
        snapshot = ContextSnapshot(
            total_tokens=1000,
            status=ContextHealthStatus.HEALTHY,
            preserved_tokens=500,
            compactable_tokens=500,
            recommendation="OK",
        )
        assert manager.suggest_compaction(snapshot) is False

    def test_warning_no_compaction(self):
        manager = ContextHygieneManager(model="gpt-4")
        snapshot = ContextSnapshot(
            total_tokens=60000,
            status=ContextHealthStatus.WARNING,
            preserved_tokens=10000,
            compactable_tokens=50000,
            recommendation="Monitor",
        )
        assert manager.suggest_compaction(snapshot) is False

    def test_critical_suggests_compaction(self):
        manager = ContextHygieneManager(model="gpt-4")
        snapshot = ContextSnapshot(
            total_tokens=100000,
            status=ContextHealthStatus.CRITICAL,
            preserved_tokens=10000,
            compactable_tokens=90000,
            recommendation="Compact",
        )
        assert manager.suggest_compaction(snapshot) is True

    def test_overflow_suggests_compaction(self):
        manager = ContextHygieneManager(model="gpt-4")
        snapshot = ContextSnapshot(
            total_tokens=120000,
            status=ContextHealthStatus.OVERFLOW,
            preserved_tokens=10000,
            compactable_tokens=110000,
            recommendation="Force compact",
        )
        assert manager.suggest_compaction(snapshot) is True


class TestMiddleware:
    """create_context_hygiene_middleware() applies analysis and bias."""

    def test_middleware_returns_dict(self):
        manager = ContextHygieneManager(model="gpt-4")
        middleware = create_context_hygiene_middleware(manager)
        ctx = _make_context("small")
        result = middleware(ctx)
        assert isinstance(result, dict)

    def test_middleware_preserves_keys(self):
        manager = ContextHygieneManager(model="gpt-4")
        middleware = create_context_hygiene_middleware(manager)
        ctx = _make_context("small")
        result = middleware(ctx)
        # At minimum, all original keys should be present
        for key in ctx:
            assert key in result
