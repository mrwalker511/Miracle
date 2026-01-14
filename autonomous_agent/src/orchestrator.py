"""Orchestrator - State machine controller for the autonomous agent."""

import time
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.tester import TesterAgent
from src.agents.reflector import ReflectorAgent
from src.memory.db_manager import DatabaseManager
from src.memory.vector_store import VectorStore
from src.llm.openai_client import OpenAIClient
from src.ui.logger import get_logger
from src.utils.circuit_breaker import CircuitBreaker


class OrchestrationState(Enum):
    """States in the orchestration state machine."""
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
        max_iterations: int = 15
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

        self.logger = get_logger('orchestrator')

        # Context shared across agents
        self.context = {
            'task_id': task_id,
            'task_description': task_description,
            'goal': goal,
            'plan': None,
            'code_files': {},
            'test_results': {},
            'previous_errors': '',
            'workspace': None
        }

        # Initialize agents
        prompts = config.get('prompts', {})
        self.planner = PlannerAgent('planner', openai_client, vector_store, prompts)
        self.coder = CoderAgent('coder', openai_client, vector_store, prompts)
        self.tester = TesterAgent('tester', openai_client, vector_store, prompts)
        self.reflector = ReflectorAgent('reflector', openai_client, vector_store, prompts)

        # Circuit breaker
        circuit_config = config.get('settings', {}).get('orchestrator', {}).get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            warning_threshold=circuit_config.get('warning_threshold', 12),
            hard_stop=circuit_config.get('hard_stop', 15)
        )

        self.logger.info(
            "orchestrator_initialized",
            task_id=str(task_id),
            max_iterations=max_iterations
        )

    def run(self) -> Dict[str, Any]:
        """Execute the main orchestration loop.

        Returns:
            Final results dictionary
        """
        self.logger.info("orchestration_started", task_id=str(self.task_id))

        # Set state to planning
        self.state = OrchestrationState.PLANNING
        self.db.update_task_status(self.task_id, 'running')

        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            iteration_start = time.time()

            self.logger.info(
                "iteration_started",
                iteration=self.current_iteration,
                state=self.state.value
            )

            # Check circuit breaker
            if self.circuit_breaker.should_stop(self.current_iteration):
                self.logger.warning(
                    "circuit_breaker_triggered",
                    iteration=self.current_iteration
                )
                self.state = OrchestrationState.PAUSED
                break

            # Create iteration record
            iteration_id = self.db.create_iteration(
                self.task_id,
                self.current_iteration,
                self.state.value
            )

            # Execute current state
            try:
                if self.state == OrchestrationState.PLANNING:
                    self._execute_planning_phase(iteration_id)
                    self.state = OrchestrationState.CODING

                elif self.state == OrchestrationState.CODING:
                    self._execute_coding_phase(iteration_id)
                    self.state = OrchestrationState.TESTING

                elif self.state == OrchestrationState.TESTING:
                    success = self._execute_testing_phase(iteration_id)
                    if success:
                        self.state = OrchestrationState.SUCCESS
                        break
                    else:
                        self.state = OrchestrationState.REFLECTING

                elif self.state == OrchestrationState.REFLECTING:
                    self._execute_reflection_phase(iteration_id)
                    self.state = OrchestrationState.CODING  # Loop back

            except Exception as e:
                self.logger.error(
                    "iteration_error",
                    iteration=self.current_iteration,
                    state=self.state.value,
                    error=str(e)
                )
                # Continue to next iteration
                continue

            # Log iteration completion
            iteration_duration = time.time() - iteration_start
            self.logger.info(
                "iteration_completed",
                iteration=self.current_iteration,
                duration=iteration_duration,
                state=self.state.value
            )

            # Store metric
            self.db.store_metric(
                self.task_id,
                'iteration_duration',
                iteration_duration
            )

            # Checkpoint every 5 iterations
            if self.current_iteration % 5 == 0:
                self._save_checkpoint()

        # Finalize
        return self._finalize()

    def _execute_planning_phase(self, iteration_id: UUID):
        """Execute planning phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("planning_phase_started")

        self.context['iteration'] = self.current_iteration
        result = self.planner.execute(self.context)

        self.context['plan'] = result['plan']
        self.context['subtasks'] = result.get('subtasks', [])
        self.context['dependencies'] = result.get('dependencies', [])

        # Update iteration with plan
        self.db.update_iteration(
            iteration_id,
            reflection=result['plan']
        )

        self.logger.info("planning_phase_completed")

    def _execute_coding_phase(self, iteration_id: UUID):
        """Execute coding phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("coding_phase_started")

        result = self.coder.execute(self.context)

        self.context['code_files'] = result['code_files']
        self.context['workspace'] = result.get('workspace')

        # Combine all code
        combined_code = "\n\n".join([
            f"# {filename}\n{content}"
            for filename, content in result['code_files'].items()
        ])

        # Update iteration with code
        self.db.update_iteration(
            iteration_id,
            code_snapshot=combined_code
        )

        self.logger.info(
            "coding_phase_completed",
            file_count=len(result['code_files'])
        )

    def _execute_testing_phase(self, iteration_id: UUID) -> bool:
        """Execute testing phase.

        Args:
            iteration_id: Current iteration ID

        Returns:
            True if tests passed, False otherwise
        """
        self.logger.info("testing_phase_started")

        result = self.tester.execute(self.context)

        self.context['test_results'] = result

        # Update iteration with test results
        self.db.update_iteration(
            iteration_id,
            test_code=result.get('test_file', ''),
            test_results=result.get('test_results', {}),
            test_passed=result.get('passed', False),
            error_message=result.get('error_message'),
            stack_trace=result.get('stack_trace')
        )

        passed = result.get('passed', False)

        self.logger.info(
            "testing_phase_completed",
            passed=passed
        )

        return passed

    def _execute_reflection_phase(self, iteration_id: UUID):
        """Execute reflection phase.

        Args:
            iteration_id: Current iteration ID
        """
        self.logger.info("reflection_phase_started")

        self.context['iteration'] = self.current_iteration
        result = self.reflector.execute(self.context)

        self.context['previous_errors'] = result.get('root_cause', '')

        # Store failure in memory
        if result.get('error_type') and result.get('error_signature'):
            self.vector_store.store_failure_with_embedding(
                task_id=self.task_id,
                iteration_id=iteration_id,
                error_signature=result['error_signature'],
                error_type=result['error_type'],
                full_error=result.get('full_error', ''),
                root_cause=result.get('root_cause'),
                code_context=str(self.context.get('code_files', {}))
            )

        # Update iteration with reflection
        self.db.update_iteration(
            iteration_id,
            reflection=result.get('reflection', ''),
            hypothesis=result.get('hypothesis', '')
        )

        self.logger.info("reflection_phase_completed")

    def _save_checkpoint(self):
        """Save orchestration state to database."""
        self.logger.info("checkpoint_saved", iteration=self.current_iteration)

        self.db.update_task_status(
            self.task_id,
            'running',
            total_iterations=self.current_iteration
        )

    def _finalize(self) -> Dict[str, Any]:
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

            self.vector_store.store_pattern_with_embedding(
                problem_type=self.context.get('problem_type', 'unknown'),
                description=self.task_description,
                code_template=combined_code,
                test_template=self.context.get('test_results', {}).get('test_file', ''),
                dependencies=self.context.get('dependencies', [])
            )

            # Update task
            self.db.update_task_status(
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
            self.db.update_task_status(
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
            self.db.update_task_status(
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
