"""Orchestrator - State machine controller for the autonomous agent.

Core loop:
    PLANNING → CODING → TESTING → REFLECTING → CODING (repeat)
                  ↓
         [optional phases run here: code_review, security_audit]

Exits with SUCCESS when tests pass, or FAILED after max_iterations.

Supporting features (non-loop):
- Context hygiene: token budget management to prevent context overflow
- Execution hooks: safety guardrails run before each iteration
- Structured failure logging: stores errors in DB + vector store for learning
"""

import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from src.agents import AgentFactory
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.tester import TesterAgent
from src.agents.reflector import ReflectorAgent
from src.agents.optional import CodeReviewerAgent, SecurityAuditorAgent
from src.memory.db_manager import DatabaseManager
from src.memory.vector_store import VectorStore
from src.memory.failure_analyzer import FailureAnalyzer, StructuredFailureLog
from src.llm.openai_client import OpenAIClient
from src.ui.logger import get_logger
from src.utils.circuit_breaker import CircuitBreaker
from src.utils.metrics_collector import MetricsCollector
from src.utils.state_saver import StateSaver
from src.utils.context_hygiene import (
    ContextHygieneManager,
    ContextThresholds,
    ContextHealthStatus,
)
from src.utils.execution_hooks import (
    HookRegistry,
    HookContext,
    HookResult,
    create_default_hook_registry,
)


class OrchestrationState(Enum):
    """States in the orchestration state machine.

    Core flow: PLANNING → CODING → TESTING → REFLECTING → CODING (repeat)
    """
    INIT = "init"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    REFLECTING = "reflecting"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class Orchestrator:
    """Main orchestration controller - coordinates the agent loop."""

    def __init__(
        self,
        task_id: UUID,
        task_description: str,
        goal: str,
        config: Dict[str, Any],
        db_manager: DatabaseManager,
        vector_store: VectorStore,
        openai_client: OpenAIClient,
        max_iterations: int = 15,
        problem_type: str = "general",
        language: str = "python",
        enable_code_review: bool = False,
        enable_security_audit: bool = False,
    ):
        """Initialize the orchestrator.

        Args:
            task_id: Task UUID
            task_description: User's task description
            goal: Structured goal
            config: Full configuration dictionary
            db_manager: Database manager
            vector_store: Vector store for memory
            openai_client: OpenAI client
            max_iterations: Maximum iterations allowed
            problem_type: Type of problem being solved
            language: Programming language
            enable_code_review: Enable code review phase
            enable_security_audit: Enable security audit phase
        """
        self.task_id = task_id
        self.task_description = task_description
        self.goal = goal
        self.config = config
        self.db = db_manager
        self.vector_store = vector_store
        self.openai = openai_client

        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.state = OrchestrationState.INIT

        # Optional phases — populated below, called after CODING before TESTING
        self.optional_phases = []

        self.logger = get_logger('orchestrator')

        # Context shared across agents
        self.context = {
            'task_id': task_id,
            'task_description': task_description,
            'goal': goal,
            'problem_type': problem_type,
            'language': language,
            'plan': None,
            'code_files': {},
            'test_results': {},
            'previous_errors': '',
            'workspace': None,
            'current_agent': '',
        }

        # Initialize agents
        prompts = config.get('prompts', {})
        workspace_root = (
            config.get('settings', {})
            .get('sandbox', {})
            .get('workspace_root', './sandbox/workspace')
        )

        # Create agent factory for centralized agent creation
        self.agent_factory = AgentFactory(
            openai_client=openai_client,
            vector_store=vector_store,
            prompts=prompts,
            workspace_path=workspace_root,
            config=config,
        )

        # Core agents
        self.planner = PlannerAgent('planner', openai_client, vector_store, prompts)
        self.coder = CoderAgent('coder', openai_client, vector_store, prompts, workspace_path=workspace_root)
        self.tester = TesterAgent(
            'tester',
            openai_client,
            vector_store,
            prompts,
            workspace_path=workspace_root,
            config=config,
        )
        self.reflector = ReflectorAgent('reflector', openai_client, vector_store, prompts)

        # Optional review agents — register their phase methods if enabled
        self.code_reviewer: Optional[CodeReviewerAgent] = None
        self.security_auditor: Optional[SecurityAuditorAgent] = None

        if enable_code_review:
            self.code_reviewer = CodeReviewerAgent('code_reviewer', openai_client, vector_store, prompts)
            self.optional_phases.append(self._execute_review_phase)

        if enable_security_audit:
            self.security_auditor = SecurityAuditorAgent('security_auditor', openai_client, vector_store, prompts)
            self.optional_phases.append(self._execute_audit_phase)

        # Circuit breaker
        circuit_config = config.get('settings', {}).get('orchestrator', {}).get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            warning_threshold=circuit_config.get('warning_threshold', 12),
            hard_stop=circuit_config.get('hard_stop', 15)
        )

        # Context hygiene manager for token management
        hygiene_config = config.get('settings', {}).get('context_hygiene', {})
        self.context_hygiene = ContextHygieneManager(
            thresholds=ContextThresholds(
                max_tokens=hygiene_config.get('max_tokens', 128000),
                warning_threshold=hygiene_config.get('warning_threshold', 0.50),
                critical_threshold=hygiene_config.get('critical_threshold', 0.75),
                overflow_threshold=hygiene_config.get('overflow_threshold', 0.90),
            ),
            model=config.get('openai', {}).get('model', 'gpt-4'),
        )

        # Execution hooks for safety
        hooks_config = config.get('settings', {}).get('execution_hooks', {})
        if hooks_config.get('enabled', True):
            self.hook_registry = create_default_hook_registry()
        else:
            self.hook_registry = HookRegistry()  # Empty registry

        # Failure analyzer for structured logging
        self.failure_analyzer = FailureAnalyzer()

        self.metrics = MetricsCollector(db=db_manager, openai_client=openai_client)
        self.state_saver = StateSaver()

        self.logger.info(
            "orchestrator_initialized",
            task_id=str(task_id),
            max_iterations=max_iterations,
            code_review_enabled=enable_code_review,
            security_audit_enabled=enable_security_audit,
        )

    async def run(self) -> Dict[str, Any]:
        """Execute the main orchestration loop.

        Returns:
            Final results dictionary
        """
        self.logger.info("orchestration_started", task_id=str(self.task_id))

        # Set state to planning
        self.state = OrchestrationState.PLANNING
        await self.db.update_task_status(self.task_id, 'running')

        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            iteration_start = time.time()

            await self.metrics.start_iteration()
            self.context['iteration'] = self.current_iteration

            self.logger.info(
                "iteration_started",
                iteration=self.current_iteration,
                state=self.state.value
            )

            # Check and manage context hygiene
            self._manage_context_hygiene()

            # Execute pre-iteration hooks
            hook_context = HookContext(
                operation='start_iteration',
                agent_type='orchestrator',
                iteration=self.current_iteration,
                target='iteration',
                content=self.context,
                metadata={'previous_error': self.context.get('previous_errors', '')}
            )
            hook_result, _, warnings = self.hook_registry.execute_pre_hooks(hook_context)

            for warning in warnings:
                self.logger.warning("hook_warning", message=warning)

            # Check circuit breaker
            if self.circuit_breaker.should_stop(self.current_iteration):
                self.logger.warning(
                    "circuit_breaker_triggered",
                    iteration=self.current_iteration
                )
                self.state = OrchestrationState.PAUSED
                break

            # Create iteration record
            iteration_id = await self.db.create_iteration(
                self.task_id,
                self.current_iteration,
                self.state.value
            )

            # Execute current state
            try:
                if self.state == OrchestrationState.PLANNING:
                    await self._execute_planning_phase(iteration_id)
                    self.state = OrchestrationState.CODING

                elif self.state == OrchestrationState.CODING:
                    await self._execute_coding_phase(iteration_id)
                    await self._run_optional_phases(iteration_id)
                    self.state = OrchestrationState.TESTING

                elif self.state == OrchestrationState.TESTING:
                    success = await self._execute_testing_phase(iteration_id)
                    if success:
                        self.state = OrchestrationState.SUCCESS
                        break
                    else:
                        self.state = OrchestrationState.REFLECTING

                elif self.state == OrchestrationState.REFLECTING:
                    await self._execute_reflection_phase(iteration_id)
                    self.state = OrchestrationState.CODING  # Loop back

            except Exception as e:
                self.logger.error(
                    "iteration_error",
                    iteration=self.current_iteration,
                    state=self.state.value,
                    error=str(e)
                )
                
                # Check for critical external API errors or exhaustion
                import openai
                from tenacity import RetryError
                is_api_error = isinstance(e, (openai.APIError, RetryError))
                if not is_api_error and hasattr(e, '__cause__') and isinstance(e.__cause__, openai.APIError):
                    is_api_error = True
                    
                if is_api_error:
                    self.logger.warning("api_limit_exhausted", message="Halting execution and saving checkpoint to prevent runaway failures.")
                    self.state = OrchestrationState.PAUSED
                    await self._save_checkpoint()
                    break

                # Continue to next iteration for local transient logic errors
                continue

            # Log iteration completion
            iteration_duration = time.time() - iteration_start
            self.logger.info(
                "iteration_completed",
                iteration=self.current_iteration,
                duration=iteration_duration,
                state=self.state.value
            )

            # Store metrics
            await self.db.store_metric(
                self.task_id,
                'iteration_duration',
                iteration_duration
            )
            await self.metrics.record_iteration_tokens(
                task_id=self.task_id,
                iteration=self.current_iteration,
            )

            # Checkpoint every 5 iterations
            if self.current_iteration % 5 == 0:
                await self._save_checkpoint()

        # Finalize
        return await self._finalize()

    async def _run_optional_phases(self, iteration_id: UUID) -> None:
        """Run any optional phases registered at init (code_review, security_audit)."""
        for phase_fn in self.optional_phases:
            await phase_fn(iteration_id)

    def _manage_context_hygiene(self):
        """Check context health and compact if necessary."""
        snapshot = self.context_hygiene.analyze(self.context)

        self.logger.debug(
            "context_health",
            status=snapshot.status.value,
            total_tokens=snapshot.total_tokens,
            recommendation=snapshot.recommendation
        )

        # Compact if critical or overflow
        if snapshot.status in [ContextHealthStatus.CRITICAL, ContextHealthStatus.OVERFLOW]:
            self.logger.info(
                "context_compaction_triggered",
                status=snapshot.status.value,
                tokens_before=snapshot.total_tokens
            )
            self.context = self.context_hygiene.compact(self.context)

        # Always apply recency bias for better LLM attention
        self.context = self.context_hygiene.apply_recency_bias(self.context)

    async def _execute_planning_phase(self, iteration_id: UUID):
        """Execute planning phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("planning_phase_started")

        self.context['iteration'] = self.current_iteration
        result = await self.planner.execute(self.context)

        self.context['plan'] = result['plan']
        self.context['subtasks'] = result.get('subtasks', [])
        self.context['dependencies'] = result.get('dependencies', [])

        # Update iteration with plan
        await self.db.update_iteration(
            iteration_id,
            reflection=result['plan']
        )

        self.logger.info("planning_phase_completed")

    async def _execute_coding_phase(self, iteration_id: UUID):
        """Execute coding phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("coding_phase_started")

        result = await self.coder.execute(self.context)

        self.context['code_files'] = result['code_files']
        self.context['workspace'] = result.get('workspace')

        # Combine all code
        combined_code = "\n\n".join([
            f"# {filename}\n{content}"
            for filename, content in result['code_files'].items()
        ])

        # Update iteration with code
        await self.db.update_iteration(
            iteration_id,
            code_snapshot=combined_code
        )

        self.logger.info(
            "coding_phase_completed",
            file_count=len(result['code_files'])
        )

    async def _execute_testing_phase(self, iteration_id: UUID) -> bool:
        """Execute testing phase.

        Args:
            iteration_id: Current iteration ID

        Returns:
            True if tests passed, False otherwise
        """
        self.logger.info("testing_phase_started")

        result = await self.tester.execute(self.context)

        self.context['test_results'] = result

        # Update iteration with test results
        await self.db.update_iteration(
            iteration_id,
            test_code=result.get('test_file', ''),
            test_results=result.get('test_results', {}),
            test_passed=result.get('passed', False),
            error_message=result.get('error_message'),
            stack_trace=result.get('stack_trace')
        )

        passed = result.get('passed', False)

        await self.metrics.record_test_pass_rate(
            task_id=self.task_id,
            passed=passed,
            iteration=self.current_iteration,
        )

        from src.testing.coverage_analyzer import parse_pytest_cov_output
        from rich.console import Console
        
        raw_output = result.get('test_results', {}).get('raw_output', '')
        cov_data = parse_pytest_cov_output(raw_output)
        if 'total_coverage_percent' in cov_data:
            cov_pct = cov_data['total_coverage_percent']
            Console().print(f"[cyan]Test Coverage:[/cyan] {cov_pct}%")
            self.context['coverage_percent'] = cov_pct
            await self.db.store_metric(self.task_id, 'coverage_percent', float(cov_pct))

        self.logger.info(
            "testing_phase_completed",
            passed=passed
        )

        return passed

    async def _execute_reflection_phase(self, iteration_id: UUID):
        """Execute reflection phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("reflection_phase_started")
        self.context['current_agent'] = 'reflector'

        self.context['iteration'] = self.current_iteration
        result = await self.reflector.execute(self.context)

        self.context['previous_errors'] = result.get('root_cause', '')

        # Create structured failure log for better learning
        structured_log = self.failure_analyzer.extract_structured(
            test_results=self.context.get('test_results', {}),
            context=self.context,
            triggering_prompt=self.context.get('plan', ''),
        )

        if structured_log:
            # Generate diagnosis
            similar_failures = await self.vector_store.find_similar_failures(
                error_signature=result.get('error_signature', ''),
                limit=3
            ) if result.get('error_signature') else []

            structured_log.diagnosis = self.failure_analyzer.generate_diagnosis(
                structured_log,
                similar_failures
            )
            structured_log.root_cause_hypothesis = result.get('root_cause', '')

            self.logger.info(
                "structured_failure_logged",
                failure_mode=structured_log.failure_mode.value,
                error_type=structured_log.error_type
            )

        # Store failure in memory
        if result.get('error_type') and result.get('error_signature'):
            await self.vector_store.store_failure_with_embedding(
                task_id=self.task_id,
                iteration_id=iteration_id,
                error_signature=result['error_signature'],
                error_type=result['error_type'],
                full_error=result.get('full_error', ''),
                root_cause=result.get('root_cause'),
                code_context=str(self.context.get('code_files', {}))
            )

        # Update iteration with reflection
        await self.db.update_iteration(
            iteration_id,
            reflection=result.get('reflection', ''),
            hypothesis=result.get('hypothesis', '')
        )

        self.logger.info("reflection_phase_completed")

    async def _execute_review_phase(self, iteration_id: UUID):
        """Execute code review phase (optional).

        Args:
            iteration_id: Current iteration ID
        """
        if not self.code_reviewer:
            return

        self.logger.info("review_phase_started")
        self.context['current_agent'] = 'code_reviewer'

        result = await self.code_reviewer.execute(self.context)

        review = result.get('review')
        if review and review.has_critical_issues:
            self.logger.warning(
                "code_review_found_critical_issues",
                blocking_count=review.blocking_count
            )
            # Add review feedback to context for coder to address
            self.context['code_review_feedback'] = result.get('review_xml', '')

        self.logger.info(
            "review_phase_completed",
            overall_quality=review.overall_quality if review else 'unknown',
            finding_count=len(review.findings) if review else 0
        )

    async def _execute_audit_phase(self, iteration_id: UUID):
        """Execute security audit phase (optional).

        Args:
            iteration_id: Current iteration ID
        """
        if not self.security_auditor:
            return

        self.logger.info("audit_phase_started")
        self.context['current_agent'] = 'security_auditor'

        result = await self.security_auditor.execute(self.context)

        audit = result.get('audit')
        if audit and audit.has_critical_vulnerabilities:
            self.logger.warning(
                "security_audit_found_vulnerabilities",
                risk_level=audit.risk_level,
                vulnerability_count=len(audit.findings)
            )
            # Add audit feedback to context for coder to address
            self.context['security_audit_feedback'] = result.get('audit_xml', '')

        self.logger.info(
            "audit_phase_completed",
            risk_level=audit.risk_level if audit else 'unknown',
            vulnerability_count=len(audit.findings) if audit else 0
        )

    async def _save_checkpoint(self):
        """Save orchestration state to database and workspace."""
        self.logger.info("checkpoint_saved", iteration=self.current_iteration)

        await self.db.update_task_status(
            self.task_id,
            'running',
            total_iterations=self.current_iteration
        )

        workspace = self.context.get('workspace')
        if workspace:
            try:
                self.state_saver.save(
                    workspace=Path(workspace),
                    state=self.state.value,
                    iteration=self.current_iteration,
                    context=self.context,
                )
            except Exception as e:
                self.logger.warning("checkpoint_write_failed", error=str(e))

    async def _finalize(self) -> Dict[str, Any]:
        """Finalize the orchestration and return results.

        Returns:
            Results dictionary
        """
        if self.state == OrchestrationState.SUCCESS:
            # Store successful pattern
            combined_code = "\n\n".join([
                f"# {filename}\n{content}"
                for filename, content in self.context.get('code_files', {}).items()
            ])

            await self.vector_store.store_pattern_with_embedding(
                problem_type=self.context.get('problem_type', 'unknown'),
                description=self.task_description,
                code_template=combined_code,
                test_template=self.context.get('test_results', {}).get('test_file', ''),
                dependencies=self.context.get('dependencies', [])
            )

            # Update task
            await self.db.update_task_status(
                self.task_id,
                'success',
                total_iterations=self.current_iteration,
                final_code=combined_code,
                final_tests=self.context.get('test_results', {}).get('test_file', '')
            )

            self.logger.info(
                "task_completed_successfully",
                iterations=self.current_iteration
            )

            return {
                'success': True,
                'iterations': self.current_iteration,
                'code_files': self.context.get('code_files', {}),
                'workspace': self.context.get('workspace')
            }

        elif self.state == OrchestrationState.PAUSED:
            await self.db.update_task_status(
                self.task_id,
                'paused',
                total_iterations=self.current_iteration
            )

            self.logger.info("task_paused", iterations=self.current_iteration)

            return {
                'success': False,
                'status': 'paused',
                'iterations': self.current_iteration,
                'message': 'Task paused by circuit breaker'
            }

        else:
            # Failed - max iterations reached
            await self.db.update_task_status(
                self.task_id,
                'failed',
                total_iterations=self.current_iteration
            )

            self.logger.info("task_failed", iterations=self.current_iteration)

            return {
                'success': False,
                'status': 'failed',
                'iterations': self.current_iteration,
                'message': f'Maximum iterations ({self.max_iterations}) reached'
            }
