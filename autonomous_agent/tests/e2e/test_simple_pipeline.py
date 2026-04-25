"""End-to-end tests for the Miracle Agent orchestration pipeline.

All external dependencies (LLM API, database, Docker) are replaced with
deterministic mocks so these tests run in CI without any live infrastructure.
They validate the full Orchestrator path: INIT → PLANNING → CODING → TESTING
→ SUCCESS, including retry cycles and optional phases.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator import Orchestrator, OrchestrationState


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CONFIG = {
    "prompts": {},
    "settings": {
        "sandbox": {"workspace_root": "/tmp/e2e-workspace"},
        "execution_hooks": {"enabled": False},
        "orchestrator": {"circuit_breaker": {"warning_threshold": 12, "hard_stop": 15}},
        "context_hygiene": {
            "max_tokens": 128000,
            "warning_threshold": 0.50,
            "critical_threshold": 0.75,
            "overflow_threshold": 0.90,
        },
    },
    "openai": {"model": "gpt-4"},
}

PLAN_RESULT = {"plan": "Step 1: write hello world", "subtasks": [], "dependencies": []}
CODE_RESULT = {
    "code_files": {"main.py": 'def hello():\n    return "Hello, World!"\n'},
    "workspace": "/tmp/e2e-workspace",
}
PASS_RESULT = {
    "passed": True,
    "test_results": {},
    "error_message": None,
    "test_file": "def test_hello(): assert hello() == 'Hello, World!'",
}
FAIL_RESULT = {
    "passed": False,
    "test_results": {},
    "error_message": "AssertionError: expected 'Hello, World!' got 'hello'",
    "test_file": "",
}
REFLECT_RESULT = {
    "root_cause": "Function returned lowercase string",
    "error_signature": "AssertionError: wrong return value",
    "error_type": "AssertionError",
    "full_error": "AssertionError: expected 'Hello, World!' got 'hello'",
    "reflection": "Fix capitalisation in hello()",
    "hypothesis": "Change return value to 'Hello, World!'",
}


def _make_db() -> MagicMock:
    db = MagicMock()
    db.create_iteration = AsyncMock(return_value=uuid.uuid4())
    db.update_task_status = AsyncMock()
    db.update_iteration = AsyncMock()
    db.store_metric = AsyncMock()
    return db


def _make_orchestrator(**kwargs) -> Orchestrator:
    orch = Orchestrator(
        task_id=uuid.uuid4(),
        task_description="Write a hello world function",
        goal="Create a function that returns 'Hello, World!'",
        config=CONFIG,
        db_manager=_make_db(),
        vector_store=MagicMock(),
        llm_client=MagicMock(),
        max_iterations=kwargs.pop("max_iterations", 10),
        **kwargs,
    )

    orch.planner = AsyncMock()
    orch.coder = AsyncMock()
    orch.tester = AsyncMock()
    orch.reflector = AsyncMock()
    orch.metrics = AsyncMock()

    orch.vector_store.find_similar_failures = AsyncMock(return_value=[])
    orch.vector_store.store_failure_with_embedding = AsyncMock()
    orch.vector_store.store_pattern_with_embedding = AsyncMock()

    orch.planner.execute.return_value = PLAN_RESULT
    orch.coder.execute.return_value = CODE_RESULT
    orch.tester.execute.return_value = PASS_RESULT
    orch.reflector.execute.return_value = REFLECT_RESULT

    return orch


# ---------------------------------------------------------------------------
# Happy path: task succeeds on the first attempt
# ---------------------------------------------------------------------------

class TestHappyPath:

    @pytest.mark.asyncio
    async def test_result_success_flag_is_true(self):
        orch = _make_orchestrator()
        result = await orch.run()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_final_state_is_success(self):
        orch = _make_orchestrator()
        await orch.run()
        assert orch.state == OrchestrationState.SUCCESS

    @pytest.mark.asyncio
    async def test_result_contains_code_files(self):
        orch = _make_orchestrator()
        result = await orch.run()
        assert "code_files" in result
        assert "main.py" in result["code_files"]

    @pytest.mark.asyncio
    async def test_result_contains_iteration_count(self):
        orch = _make_orchestrator()
        result = await orch.run()
        assert result["iterations"] >= 1

    @pytest.mark.asyncio
    async def test_planner_called_exactly_once(self):
        orch = _make_orchestrator()
        await orch.run()
        orch.planner.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_sequence_is_plan_code_test(self):
        orch = _make_orchestrator()
        order = []
        orch.planner.execute.side_effect = lambda ctx: (order.append("plan"), PLAN_RESULT)[1]
        orch.coder.execute.side_effect = lambda ctx: (order.append("code"), CODE_RESULT)[1]
        orch.tester.execute.side_effect = lambda ctx: (order.append("test"), PASS_RESULT)[1]

        await orch.run()

        assert order == ["plan", "code", "test"]


# ---------------------------------------------------------------------------
# Retry path: one failure, then success
# ---------------------------------------------------------------------------

class TestRetryPath:

    @pytest.mark.asyncio
    async def test_result_still_success_after_one_failure(self):
        orch = _make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]
        result = await orch.run()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_reflector_called_after_failure(self):
        orch = _make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]
        await orch.run()
        orch.reflector.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_coder_called_twice_after_one_failure(self):
        orch = _make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]
        await orch.run()
        assert orch.coder.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_reflection_root_cause_passed_to_coder(self):
        orch = _make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]
        await orch.run()
        second_call_ctx = orch.coder.execute.call_args_list[1][0][0]
        assert "lowercase" in second_call_ctx["previous_errors"]

    @pytest.mark.asyncio
    async def test_multiple_retries_then_success(self):
        # 3 failures + 1 pass: needs more iterations because plan/reflect/code each
        # consume one slot. Use max_iterations=20 to give the loop enough room.
        orch = _make_orchestrator(max_iterations=20)
        orch.tester.execute.side_effect = [FAIL_RESULT, FAIL_RESULT, FAIL_RESULT, PASS_RESULT]
        result = await orch.run()
        assert result["success"] is True
        assert orch.coder.execute.call_count == 4


# ---------------------------------------------------------------------------
# Exhaustion path: max iterations reached without passing
# ---------------------------------------------------------------------------

class TestExhaustionPath:

    @pytest.mark.asyncio
    async def test_result_success_false_when_exhausted(self):
        orch = _make_orchestrator(max_iterations=3)
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_result_status_failed_when_exhausted(self):
        orch = _make_orchestrator(max_iterations=3)
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_iteration_count_matches_max(self):
        orch = _make_orchestrator(max_iterations=3)
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result["iterations"] == 3


# ---------------------------------------------------------------------------
# Circuit breaker: stops early to protect against runaway loops
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    @pytest.mark.asyncio
    async def test_circuit_breaker_stops_loop_early(self):
        orch = _make_orchestrator(max_iterations=20)
        orch.circuit_breaker.warning_threshold = 2
        orch.circuit_breaker.hard_stop = 3
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result["iterations"] < 20

    @pytest.mark.asyncio
    async def test_circuit_breaker_returns_paused_status(self):
        orch = _make_orchestrator(max_iterations=20)
        orch.circuit_breaker.warning_threshold = 2
        orch.circuit_breaker.hard_stop = 3
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result["status"] == "paused"
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Optional phases: code review and security audit
# ---------------------------------------------------------------------------

class TestOptionalPhases:

    @pytest.mark.asyncio
    async def test_review_phase_runs_between_coder_and_tester(self):
        orch = _make_orchestrator(enable_code_review=True)
        orch.code_reviewer = AsyncMock()
        orch.code_reviewer.execute.return_value = {"review": None}
        orch.optional_phases = [orch._execute_review_phase]

        order = []
        orch.coder.execute.side_effect = lambda ctx: (order.append("coder"), CODE_RESULT)[1]
        orch.code_reviewer.execute.side_effect = lambda ctx: (order.append("reviewer"), {"review": None})[1]
        orch.tester.execute.side_effect = lambda ctx: (order.append("tester"), PASS_RESULT)[1]

        await orch.run()

        assert order == ["coder", "reviewer", "tester"]

    @pytest.mark.asyncio
    async def test_audit_phase_runs_between_coder_and_tester(self):
        orch = _make_orchestrator(enable_security_audit=True)
        orch.security_auditor = AsyncMock()
        orch.security_auditor.execute.return_value = {"audit": None}
        orch.optional_phases = [orch._execute_audit_phase]

        order = []
        orch.coder.execute.side_effect = lambda ctx: (order.append("coder"), CODE_RESULT)[1]
        orch.security_auditor.execute.side_effect = lambda ctx: (order.append("auditor"), {"audit": None})[1]
        orch.tester.execute.side_effect = lambda ctx: (order.append("tester"), PASS_RESULT)[1]

        await orch.run()

        assert order == ["coder", "auditor", "tester"]

    @pytest.mark.asyncio
    async def test_task_still_succeeds_with_optional_phases_enabled(self):
        orch = _make_orchestrator(enable_code_review=True, enable_security_audit=True)
        orch.code_reviewer = AsyncMock()
        orch.code_reviewer.execute.return_value = {"review": None}
        orch.security_auditor = AsyncMock()
        orch.security_auditor.execute.return_value = {"audit": None}
        orch.optional_phases = [orch._execute_review_phase, orch._execute_audit_phase]

        result = await orch.run()
        assert result["success"] is True
