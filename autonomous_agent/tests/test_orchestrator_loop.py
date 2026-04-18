"""Tests for the core orchestration loop.

Tests the state machine: PLANNING → CODING → TESTING → REFLECTING → repeat.
All external dependencies (DB, vector store, LLM, agents) are mocked so
tests run without any infrastructure.
"""
import uuid
from unittest.mock import MagicMock, AsyncMock, call

import pytest

from src.orchestrator import Orchestrator, OrchestrationState
from src.utils.approval_manager import ApprovalDenied


# ---------------------------------------------------------------------------
# Minimal config — disables hooks and uses small token budget so tests
# run fast without triggering any infrastructure features.
# ---------------------------------------------------------------------------

async def _async_tracker(call_order, name, result):
    call_order.append(name)
    return result

CONFIG = {
    'prompts': {},
    'settings': {
        'sandbox': {'workspace_root': '/tmp/test-workspace'},
        'execution_hooks': {'enabled': False},
        'orchestrator': {'circuit_breaker': {'warning_threshold': 12, 'hard_stop': 15}},
        'context_hygiene': {
            'max_tokens': 128000,
            'warning_threshold': 0.50,
            'critical_threshold': 0.75,
            'overflow_threshold': 0.90,
        },
    },
    'openai': {'model': 'gpt-4'},
}

# Canned agent return values used across tests
PLAN_RESULT = {'plan': 'Step 1: write code', 'subtasks': [], 'dependencies': []}
CODE_RESULT = {'code_files': {'main.py': 'print("hello")'}, 'workspace': '/tmp/test'}
PASS_RESULT = {'passed': True, 'test_results': {}, 'error_message': None, 'test_file': ''}
FAIL_RESULT = {'passed': False, 'test_results': {}, 'error_message': 'AssertionError', 'test_file': ''}
REFLECT_RESULT = {
    'root_cause': 'Missing import statement',
    'error_signature': 'ImportError: no module named x',
    'error_type': 'ImportError',
    'full_error': 'ImportError: No module named x',
    'reflection': 'Need to add import at top of file',
    'hypothesis': 'Add `import x` at top of main.py',
}


def make_orchestrator(max_iterations=10, enable_code_review=False, enable_security_audit=False):
    """Create an Orchestrator with all I/O dependencies mocked.

    Agents are replaced with MagicMocks after construction so tests
    control exactly what each agent returns without needing a live LLM.
    """
    db = MagicMock()
    db.create_iteration = AsyncMock(return_value=uuid.uuid4())
    db.update_task_status = AsyncMock()
    db.update_iteration = AsyncMock()
    db.store_metric = AsyncMock()

    orch = Orchestrator(
        task_id=uuid.uuid4(),
        task_description='Write a hello world function',
        goal='Create a function that prints Hello World',
        config=CONFIG,
        db_manager=db,
        vector_store=MagicMock(),
        llm_client=MagicMock(),
        max_iterations=max_iterations,
        enable_code_review=enable_code_review,
        enable_security_audit=enable_security_audit,
    )

    # Replace real agents with controllable mocks
    orch.planner = AsyncMock()
    orch.coder = AsyncMock()
    orch.tester = AsyncMock()
    orch.reflector = AsyncMock()
    orch.metrics = AsyncMock()

    # Safe default for similarity search used in reflection phase
    orch.vector_store.find_similar_failures = AsyncMock(return_value=[])
    orch.vector_store.store_failure_with_embedding = AsyncMock()
    orch.vector_store.store_pattern_with_embedding = AsyncMock()

    # Default: everything succeeds on the first try
    orch.planner.execute.return_value = PLAN_RESULT
    orch.coder.execute.return_value = CODE_RESULT
    orch.tester.execute.return_value = PASS_RESULT
    orch.reflector.execute.return_value = REFLECT_RESULT

    return orch


# ---------------------------------------------------------------------------
# TestStateTransitions
# ---------------------------------------------------------------------------

class TestStateTransitions:
    """The state machine moves through phases in the correct order."""

    @pytest.mark.asyncio

    async def test_agent_call_order_on_success(self):
        """Planner runs before coder, coder before tester."""
        orch = make_orchestrator()
        call_order = []

        async def mock_planner(ctx):
            call_order.append('planner')
            return PLAN_RESULT

        async def mock_coder(ctx):
            call_order.append('coder')
            return CODE_RESULT

        async def mock_tester(ctx):
            call_order.append('tester')
            return PASS_RESULT

        orch.planner.execute.side_effect = mock_planner
        orch.coder.execute.side_effect = mock_coder
        orch.tester.execute.side_effect = mock_tester

        await orch.run()

        assert call_order == ['planner', 'coder', 'tester']

    @pytest.mark.asyncio

    async def test_reflector_runs_after_test_failure(self):
        """On test failure: coder → tester (fail) → reflector → coder → tester (pass)."""
        orch = make_orchestrator()
        call_order = []

        async def tracking_coder(ctx):
            call_order.append('coder')
            return CODE_RESULT

        async def tracking_tester(ctx):
            if call_order.count('tester') == 0:
                call_order.append('tester')
                return FAIL_RESULT
            call_order.append('tester')
            return PASS_RESULT

        async def tracking_reflector(ctx):
            call_order.append('reflector')
            return REFLECT_RESULT

        orch.coder.execute.side_effect = tracking_coder
        orch.tester.execute.side_effect = tracking_tester
        orch.reflector.execute.side_effect = tracking_reflector

        await orch.run()

        assert 'reflector' in call_order
        reflector_pos = call_order.index('reflector')
        # reflector follows the first failed tester
        assert call_order[reflector_pos - 1] == 'tester'
        # coder runs again after reflection
        assert call_order[reflector_pos + 1] == 'coder'

    @pytest.mark.asyncio

    async def test_planning_runs_only_once(self):
        """Planner is called exactly once, even across multiple retry cycles."""
        orch = make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, FAIL_RESULT, PASS_RESULT]

        await orch.run()

        orch.planner.execute.assert_called_once()

    @pytest.mark.asyncio

    async def test_coder_runs_again_after_reflection(self):
        """After reflection, coder gets another attempt before testing."""
        orch = make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]

        await orch.run()

        assert orch.coder.execute.call_count == 2

    @pytest.mark.asyncio

    async def test_final_state_is_success_on_pass(self):
        orch = make_orchestrator()
        await orch.run()
        assert orch.state == OrchestrationState.SUCCESS

    @pytest.mark.asyncio

    async def test_final_state_is_not_success_when_exhausted(self):
        orch = make_orchestrator(max_iterations=4)
        orch.tester.execute.return_value = FAIL_RESULT
        await orch.run()
        assert orch.state != OrchestrationState.SUCCESS


# ---------------------------------------------------------------------------
# TestContextPropagation
# ---------------------------------------------------------------------------

class TestContextPropagation:
    """Data written by one agent is visible to the next."""

    @pytest.mark.asyncio

    async def test_plan_is_in_context_when_coder_runs(self):
        """Planner output ('plan') must be in context when coder executes."""
        orch = make_orchestrator()
        await orch.run()

        coder_context = orch.coder.execute.call_args[0][0]
        assert coder_context['plan'] == 'Step 1: write code'

    @pytest.mark.asyncio

    async def test_code_files_in_context_when_tester_runs(self):
        """Coder output ('code_files') must be in context when tester executes."""
        orch = make_orchestrator()
        await orch.run()

        tester_context = orch.tester.execute.call_args[0][0]
        assert 'main.py' in tester_context['code_files']

    @pytest.mark.asyncio

    async def test_reflection_sets_previous_errors_for_coder(self):
        """Reflector's root_cause becomes previous_errors for the next coding attempt."""
        orch = make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]

        await orch.run()

        # Second coder call receives the reflector's root_cause
        second_coder_context = orch.coder.execute.call_args_list[1][0][0]
        assert second_coder_context['previous_errors'] == 'Missing import statement'

    @pytest.mark.asyncio

    async def test_previous_errors_empty_on_first_coding_attempt(self):
        """First coding attempt starts with no previous error context."""
        orch = make_orchestrator()
        await orch.run()

        first_coder_context = orch.coder.execute.call_args_list[0][0][0]
        assert first_coder_context['previous_errors'] == ''

    @pytest.mark.asyncio

    async def test_iteration_counter_increments_in_context(self):
        """Context 'iteration' key reflects the current iteration number."""
        iterations_seen = []

        orch = make_orchestrator()
        orch.tester.execute.side_effect = lambda ctx: (
            iterations_seen.append(ctx['iteration']), PASS_RESULT
        )[1]

        await orch.run()

        assert iterations_seen[0] >= 1


# ---------------------------------------------------------------------------
# TestLoopTermination
# ---------------------------------------------------------------------------

class TestLoopTermination:
    """The loop exits correctly under each termination condition."""

    @pytest.mark.asyncio

    async def test_success_result_when_tests_pass(self):
        orch = make_orchestrator()
        result = await orch.run()
        assert result['success'] is True

    @pytest.mark.asyncio

    async def test_success_result_contains_code_files(self):
        orch = make_orchestrator()
        result = await orch.run()
        assert 'code_files' in result
        assert 'main.py' in result['code_files']

    @pytest.mark.asyncio

    async def test_success_after_one_retry(self):
        """Fail once, pass on retry — still a successful result."""
        orch = make_orchestrator()
        orch.tester.execute.side_effect = [FAIL_RESULT, PASS_RESULT]
        result = await orch.run()
        assert result['success'] is True

    @pytest.mark.asyncio

    async def test_failed_result_when_max_iterations_exhausted(self):
        orch = make_orchestrator(max_iterations=4)
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result['success'] is False
        assert result['status'] == 'failed'

    @pytest.mark.asyncio

    async def test_failed_result_includes_iteration_count(self):
        orch = make_orchestrator(max_iterations=4)
        orch.tester.execute.return_value = FAIL_RESULT
        result = await orch.run()
        assert result['iterations'] == 4

    @pytest.mark.asyncio

    async def test_circuit_breaker_pauses_loop(self):
        """When circuit breaker fires, result is paused, not failed."""
        orch = make_orchestrator(max_iterations=20)
        orch.circuit_breaker.warning_threshold = 2
        orch.circuit_breaker.hard_stop = 3
        orch.tester.execute.return_value = FAIL_RESULT

        result = await orch.run()

        assert result['success'] is False
        assert result['status'] == 'paused'

    @pytest.mark.asyncio

    async def test_circuit_breaker_stops_before_max_iterations(self):
        """Circuit breaker should stop the loop earlier than max_iterations."""
        orch = make_orchestrator(max_iterations=20)
        orch.circuit_breaker.warning_threshold = 2
        orch.circuit_breaker.hard_stop = 3
        orch.tester.execute.return_value = FAIL_RESULT

        result = await orch.run()

        assert result['iterations'] < 20

    @pytest.mark.asyncio
    async def test_approval_denial_pauses_task(self):
        orch = make_orchestrator(max_iterations=10)
        orch.coder.execute.side_effect = ApprovalDenied("approval denied for protected file write")

        result = await orch.run()

        assert result["success"] is False
        assert result["status"] == "paused"
        assert "approval denied" in result["message"]
        assert orch.state == OrchestrationState.PAUSED


# ---------------------------------------------------------------------------
# TestOptionalPhases
# ---------------------------------------------------------------------------

class TestOptionalPhases:
    """Code review and security audit phases are called when enabled, skipped otherwise."""

    @pytest.mark.asyncio

    async def test_no_optional_phases_by_default(self):
        orch = make_orchestrator()
        assert orch.optional_phases == []

    @pytest.mark.asyncio

    async def test_code_reviewer_registered_when_enabled(self):
        orch = make_orchestrator(enable_code_review=True)
        assert len(orch.optional_phases) == 1

    @pytest.mark.asyncio

    async def test_security_auditor_registered_when_enabled(self):
        orch = make_orchestrator(enable_security_audit=True)
        assert len(orch.optional_phases) == 1

    @pytest.mark.asyncio

    async def test_both_optional_phases_registered(self):
        orch = make_orchestrator(enable_code_review=True, enable_security_audit=True)
        assert len(orch.optional_phases) == 2

    @pytest.mark.asyncio

    async def test_review_phase_called_after_coding(self):
        """Code reviewer runs after coder but before tester."""
        orch = make_orchestrator(enable_code_review=True)
        orch.code_reviewer = AsyncMock()
        orch.code_reviewer.execute.return_value = {'review': None}
        orch.optional_phases = [orch._execute_review_phase]

        call_order = []
        async def mock_coder(ctx):
            call_order.append('coder')
            return CODE_RESULT

        async def mock_reviewer(ctx):
            call_order.append('reviewer')
            return {'review': None}

        async def mock_tester(ctx):
            call_order.append('tester')
            return PASS_RESULT

        orch.coder.execute.side_effect = mock_coder
        orch.code_reviewer.execute.side_effect = mock_reviewer
        orch.tester.execute.side_effect = mock_tester

        await orch.run()

        assert call_order == ['coder', 'reviewer', 'tester']

    @pytest.mark.asyncio

    async def test_audit_phase_called_after_coding(self):
        """Security auditor runs after coder but before tester."""
        orch = make_orchestrator(enable_security_audit=True)
        orch.security_auditor = AsyncMock()
        orch.security_auditor.execute.return_value = {'audit': None}
        orch.optional_phases = [orch._execute_audit_phase]

        call_order = []

        async def mock_coder(ctx):
            call_order.append('coder')
            return CODE_RESULT

        async def mock_auditor(ctx):
            call_order.append('auditor')
            return {'audit': None}

        async def mock_tester(ctx):
            call_order.append('tester')
            return PASS_RESULT

        orch.coder.execute.side_effect = mock_coder
        orch.security_auditor.execute.side_effect = mock_auditor
        orch.tester.execute.side_effect = mock_tester

        await orch.run()

        assert call_order == ['coder', 'auditor', 'tester']

    @pytest.mark.asyncio

    async def test_no_review_agent_created_when_disabled(self):
        orch = make_orchestrator(enable_code_review=False)
        assert orch.code_reviewer is None

    @pytest.mark.asyncio

    async def test_no_audit_agent_created_when_disabled(self):
        orch = make_orchestrator(enable_security_audit=False)
        assert orch.security_auditor is None
