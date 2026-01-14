"""Database manager for PostgreSQL with pgvector support."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from pgvector.psycopg2 import register_vector

from src.ui.logger import get_logger


class DatabaseManager:
    """Manages PostgreSQL database operations with pgvector support."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize database connection pool.

        Args:
            config: Database configuration from config/database.yaml
        """
        self.config = config['database']
        self.logger = get_logger('db_manager')

        # Create connection pool
        self.pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=self.config.get('pool_size', 10),
            host=self.config['host'],
            port=self.config['port'],
            database=self.config['name'],
            user=self.config['user'],
            password=self.config['password']
        )

        self.logger.info("database_pool_created", database=self.config['name'])

    def get_connection(self):
        """Get a connection from the pool.

        Returns:
            psycopg2 connection
        """
        conn = self.pool.getconn()
        register_vector(conn)  # Register pgvector types
        return conn

    def return_connection(self, conn):
        """Return a connection to the pool.

        Args:
            conn: Connection to return
        """
        self.pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results as list of dicts, or None if fetch=False
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                else:
                    conn.commit()
                    return None

        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(
                "database_query_error",
                query=query[:100],
                error=str(e)
            )
            raise

        finally:
            if conn:
                self.return_connection(conn)

    # ==================== TASK OPERATIONS ====================

    def create_task(
        self,
        description: str,
        goal: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Create a new task.

        Args:
            description: User's original task description
            goal: Structured goal statement
            metadata: Additional metadata (e.g., problem_type, subtasks)

        Returns:
            Task UUID
        """
        query = """
            INSERT INTO tasks (description, goal, status, metadata)
            VALUES (%s, %s, 'planning', %s)
            RETURNING task_id
        """
        result = self.execute_query(
            query,
            (description, goal, Json(metadata or {})),
            fetch=True
        )

        task_id = result[0]['task_id']
        self.logger.info("task_created", task_id=str(task_id))
        return task_id

    def update_task_status(
        self,
        task_id: UUID,
        status: str,
        total_iterations: Optional[int] = None,
        final_code: Optional[str] = None,
        final_tests: Optional[str] = None
    ):
        """Update task status.

        Args:
            task_id: Task UUID
            status: New status
            total_iterations: Optional iteration count
            final_code: Optional final code
            final_tests: Optional final tests
        """
        updates = ["status = %s"]
        params = [status]

        if total_iterations is not None:
            updates.append("total_iterations = %s")
            params.append(total_iterations)

        if final_code is not None:
            updates.append("final_code = %s")
            params.append(final_code)

        if final_tests is not None:
            updates.append("final_tests = %s")
            params.append(final_tests)

        if status in ('success', 'failed'):
            updates.append("completed_at = NOW()")

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = %s"
        params.append(str(task_id))

        self.execute_query(query, tuple(params), fetch=False)
        self.logger.info("task_status_updated", task_id=str(task_id), status=status)

    def get_task(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task dictionary or None
        """
        query = "SELECT * FROM tasks WHERE task_id = %s"
        results = self.execute_query(query, (str(task_id),))
        return results[0] if results else None

    # ==================== ITERATION OPERATIONS ====================

    def create_iteration(
        self,
        task_id: UUID,
        iteration_number: int,
        phase: str
    ) -> UUID:
        """Create a new iteration record.

        Args:
            task_id: Task UUID
            iteration_number: Iteration number
            phase: Current phase

        Returns:
            Iteration UUID
        """
        query = """
            INSERT INTO iterations (task_id, iteration_number, phase)
            VALUES (%s, %s, %s)
            RETURNING iteration_id
        """
        result = self.execute_query(
            query,
            (str(task_id), iteration_number, phase),
            fetch=True
        )

        iteration_id = result[0]['iteration_id']
        self.logger.info(
            "iteration_created",
            task_id=str(task_id),
            iteration=iteration_number,
            iteration_id=str(iteration_id)
        )
        return iteration_id

    def update_iteration(
        self,
        iteration_id: UUID,
        code_snapshot: Optional[str] = None,
        test_code: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None,
        test_passed: Optional[bool] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        reflection: Optional[str] = None,
        hypothesis: Optional[str] = None,
        tokens_used: Optional[int] = None,
        duration_seconds: Optional[float] = None
    ):
        """Update iteration with results.

        Args:
            iteration_id: Iteration UUID
            code_snapshot: Generated code
            test_code: Generated tests
            test_results: Test execution results
            test_passed: Whether tests passed
            error_message: Error message if failed
            stack_trace: Stack trace if failed
            reflection: LLM's reflection
            hypothesis: Next hypothesis
            tokens_used: Tokens consumed
            duration_seconds: Duration in seconds
        """
        updates = []
        params = []

        fields = {
            'code_snapshot': code_snapshot,
            'test_code': test_code,
            'test_results': Json(test_results) if test_results else None,
            'test_passed': test_passed,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'reflection': reflection,
            'hypothesis': hypothesis,
            'tokens_used': tokens_used,
            'duration_seconds': duration_seconds
        }

        for field, value in fields.items():
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)

        if updates:
            query = f"UPDATE iterations SET {', '.join(updates)} WHERE iteration_id = %s"
            params.append(str(iteration_id))
            self.execute_query(query, tuple(params), fetch=False)

    # ==================== FAILURE OPERATIONS ====================

    def store_failure(
        self,
        task_id: UUID,
        iteration_id: UUID,
        error_signature: str,
        error_type: str,
        full_error: str,
        root_cause: Optional[str] = None,
        code_context: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> UUID:
        """Store a failure for learning.

        Args:
            task_id: Task UUID
            iteration_id: Iteration UUID
            error_signature: Normalized error pattern
            error_type: Error type (e.g., ImportError)
            full_error: Complete error message
            root_cause: LLM's root cause analysis
            code_context: Relevant code snippet
            embedding: Vector embedding

        Returns:
            Failure UUID
        """
        query = """
            INSERT INTO failures (
                task_id, iteration_id, error_signature, error_type,
                full_error, root_cause, code_context, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING failure_id
        """

        result = self.execute_query(
            query,
            (
                str(task_id),
                str(iteration_id),
                error_signature,
                error_type,
                full_error,
                root_cause,
                code_context,
                embedding
            ),
            fetch=True
        )

        failure_id = result[0]['failure_id']
        self.logger.info(
            "failure_stored",
            failure_id=str(failure_id),
            error_type=error_type
        )
        return failure_id

    def mark_failure_fixed(
        self,
        failure_id: UUID,
        fix_iteration: int,
        solution: str
    ):
        """Mark a failure as fixed.

        Args:
            failure_id: Failure UUID
            fix_iteration: Iteration where it was fixed
            solution: How it was fixed
        """
        query = """
            UPDATE failures
            SET fixed = TRUE, fix_iteration = %s, solution = %s
            WHERE failure_id = %s
        """
        self.execute_query(query, (fix_iteration, solution, str(failure_id)), fetch=False)

    # ==================== PATTERN OPERATIONS ====================

    def store_pattern(
        self,
        problem_type: str,
        description: str,
        code_template: str,
        test_template: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None
    ) -> UUID:
        """Store a successful pattern.

        Args:
            problem_type: Type of problem solved
            description: Description of the pattern
            code_template: Code template
            test_template: Test template
            dependencies: Required dependencies
            embedding: Vector embedding

        Returns:
            Pattern UUID
        """
        query = """
            INSERT INTO patterns (
                problem_type, description, code_template,
                test_template, dependencies, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING pattern_id
        """

        result = self.execute_query(
            query,
            (
                problem_type,
                description,
                code_template,
                test_template,
                Json(dependencies or []),
                embedding
            ),
            fetch=True
        )

        pattern_id = result[0]['pattern_id']
        self.logger.info("pattern_stored", pattern_id=str(pattern_id))
        return pattern_id

    def update_pattern_usage(self, pattern_id: UUID, success: bool):
        """Update pattern usage statistics.

        Args:
            pattern_id: Pattern UUID
            success: Whether usage was successful
        """
        query = """
            UPDATE patterns
            SET usage_count = usage_count + 1,
                success_rate = (
                    (success_rate * usage_count + %s) / (usage_count + 1)
                ),
                last_used = NOW()
            WHERE pattern_id = %s
        """
        self.execute_query(query, (1.0 if success else 0.0, str(pattern_id)), fetch=False)

    # ==================== METRICS OPERATIONS ====================

    def store_metric(
        self,
        task_id: UUID,
        metric_type: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store a metric.

        Args:
            task_id: Task UUID
            metric_type: Type of metric
            value: Metric value
            metadata: Additional metadata
        """
        query = """
            INSERT INTO metrics (task_id, metric_type, value, metadata)
            VALUES (%s, %s, %s, %s)
        """
        self.execute_query(
            query,
            (str(task_id), metric_type, value, Json(metadata or {})),
            fetch=False
        )

    # ==================== APPROVAL OPERATIONS ====================

    def store_approval(
        self,
        task_id: UUID,
        iteration_id: UUID,
        approval_type: str,
        request_details: Dict[str, Any],
        approved: bool,
        reasoning: Optional[str] = None
    ) -> UUID:
        """Store an approval decision.

        Args:
            task_id: Task UUID
            iteration_id: Iteration UUID
            approval_type: Type of approval
            request_details: What was requested
            approved: User's decision
            reasoning: Optional reasoning

        Returns:
            Approval UUID
        """
        query = """
            INSERT INTO approvals (
                task_id, iteration_id, approval_type,
                request_details, approved, reasoning
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING approval_id
        """

        result = self.execute_query(
            query,
            (
                str(task_id),
                str(iteration_id),
                approval_type,
                Json(request_details),
                approved,
                reasoning
            ),
            fetch=True
        )

        return result[0]['approval_id']

    def close(self):
        """Close all database connections."""
        if self.pool:
            self.pool.closeall()
            self.logger.info("database_pool_closed")
