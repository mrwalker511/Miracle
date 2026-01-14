"""Vector store for similarity search using pgvector and OpenAI embeddings."""

from typing import List, Dict, Any, Optional
from uuid import UUID

from src.memory.db_manager import DatabaseManager
from src.llm.openai_client import OpenAIClient
from src.ui.logger import get_logger


class VectorStore:
    """Manages vector embeddings and similarity search."""

    def __init__(self, db_manager: DatabaseManager, openai_client: OpenAIClient):
        """Initialize vector store.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI client for embeddings
        """
        self.db = db_manager
        self.openai = openai_client
        self.logger = get_logger('vector_store')

    def find_similar_failures(
        self,
        error_message: str,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar past failures using vector similarity.

        Args:
            error_message: Current error message
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar failures with similarity scores
        """
        # Generate embedding for the error message
        try:
            query_embedding = self.openai.create_embedding(error_message)
        except Exception as e:
            self.logger.error("embedding_generation_failed", error=str(e))
            return []

        # Vector similarity search using cosine distance
        # pgvector: <=> operator computes cosine distance (0 = identical, 2 = opposite)
        # Similarity = 1 - (distance / 2)
        query = """
            SELECT
                failure_id,
                error_signature,
                error_type,
                root_cause,
                solution,
                code_context,
                1 - (embedding <=> %s::vector) / 2 AS similarity
            FROM failures
            WHERE fixed = TRUE
                AND embedding IS NOT NULL
                AND 1 - (embedding <=> %s::vector) / 2 >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        results = self.db.execute_query(
            query,
            (query_embedding, query_embedding, similarity_threshold, query_embedding, limit)
        )

        self.logger.info(
            "similar_failures_found",
            count=len(results) if results else 0,
            threshold=similarity_threshold
        )

        return results or []

    def find_similar_patterns(
        self,
        task_description: str,
        problem_type: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Find similar successful patterns.

        Args:
            task_description: Description of current task
            problem_type: Optional problem type filter
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of similar patterns with similarity scores
        """
        try:
            query_embedding = self.openai.create_embedding(task_description)
        except Exception as e:
            self.logger.error("embedding_generation_failed", error=str(e))
            return []

        # Build query with optional problem type filter
        query = """
            SELECT
                pattern_id,
                problem_type,
                description,
                code_template,
                test_template,
                dependencies,
                usage_count,
                success_rate,
                1 - (embedding <=> %s::vector) / 2 AS similarity
            FROM patterns
            WHERE embedding IS NOT NULL
                AND 1 - (embedding <=> %s::vector) / 2 >= %s
        """

        params = [query_embedding, query_embedding, similarity_threshold]

        if problem_type:
            query += " AND problem_type = %s"
            params.append(problem_type)

        query += """
            ORDER BY
                (1 - (embedding <=> %s::vector) / 2) * 0.7 +
                (success_rate * 0.2) +
                (LEAST(usage_count, 10) / 10.0 * 0.1) DESC
            LIMIT %s
        """

        params.extend([query_embedding, limit])

        results = self.db.execute_query(query, tuple(params))

        self.logger.info(
            "similar_patterns_found",
            count=len(results) if results else 0,
            problem_type=problem_type,
            threshold=similarity_threshold
        )

        return results or []

    def store_failure_with_embedding(
        self,
        task_id: UUID,
        iteration_id: UUID,
        error_signature: str,
        error_type: str,
        full_error: str,
        root_cause: Optional[str] = None,
        code_context: Optional[str] = None
    ) -> UUID:
        """Store a failure with its embedding.

        Args:
            task_id: Task UUID
            iteration_id: Iteration UUID
            error_signature: Normalized error pattern
            error_type: Error type
            full_error: Complete error message
            root_cause: LLM's analysis
            code_context: Relevant code

        Returns:
            Failure UUID
        """
        # Generate embedding from error signature + error type
        embedding_text = f"{error_type}: {error_signature}"

        try:
            embedding = self.openai.create_embedding(embedding_text)
        except Exception as e:
            self.logger.warning(
                "failure_embedding_failed",
                error=str(e),
                error_type=error_type
            )
            embedding = None

        return self.db.store_failure(
            task_id=task_id,
            iteration_id=iteration_id,
            error_signature=error_signature,
            error_type=error_type,
            full_error=full_error,
            root_cause=root_cause,
            code_context=code_context,
            embedding=embedding
        )

    def store_pattern_with_embedding(
        self,
        problem_type: str,
        description: str,
        code_template: str,
        test_template: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> UUID:
        """Store a pattern with its embedding.

        Args:
            problem_type: Type of problem
            description: Pattern description
            code_template: Code template
            test_template: Test template
            dependencies: Required dependencies

        Returns:
            Pattern UUID
        """
        # Generate embedding from problem type + description
        embedding_text = f"{problem_type}: {description}"

        try:
            embedding = self.openai.create_embedding(embedding_text)
        except Exception as e:
            self.logger.warning(
                "pattern_embedding_failed",
                error=str(e),
                problem_type=problem_type
            )
            embedding = None

        return self.db.store_pattern(
            problem_type=problem_type,
            description=description,
            code_template=code_template,
            test_template=test_template,
            dependencies=dependencies,
            embedding=embedding
        )

    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored failures.

        Returns:
            Dictionary with failure statistics
        """
        query = """
            SELECT
                COUNT(*) as total_failures,
                COUNT(*) FILTER (WHERE fixed = TRUE) as fixed_failures,
                COUNT(DISTINCT error_type) as unique_error_types,
                AVG(CASE WHEN fixed THEN fix_iteration - iteration_number ELSE NULL END) as avg_iterations_to_fix
            FROM failures f
            LEFT JOIN iterations i ON f.iteration_id = i.iteration_id
        """

        results = self.db.execute_query(query)
        return results[0] if results else {}

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored patterns.

        Returns:
            Dictionary with pattern statistics
        """
        query = """
            SELECT
                COUNT(*) as total_patterns,
                COUNT(DISTINCT problem_type) as unique_problem_types,
                AVG(success_rate) as avg_success_rate,
                SUM(usage_count) as total_usage_count
            FROM patterns
        """

        results = self.db.execute_query(query)
        return results[0] if results else {}
