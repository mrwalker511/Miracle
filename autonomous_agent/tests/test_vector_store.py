"""Tests for vector store (async).

Covers:
- find_similar_failures delegates to DB with embedding
- find_similar_patterns builds correct SQL
- store_failure_with_embedding delegates to DB
- store_pattern_with_embedding delegates to DB
- Graceful fallback when embedding generation fails
- Statistics queries
"""

from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.vector_store import VectorStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Create a mock DatabaseManager."""
    db = MagicMock()
    db.execute_query = AsyncMock(return_value=[])
    db.store_failure = AsyncMock(return_value=uuid4())
    db.store_pattern = AsyncMock(return_value=uuid4())
    return db


@pytest.fixture
def mock_openai():
    """Create a mock OpenAIClient."""
    client = MagicMock()
    client.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 512)
    return client


@pytest.fixture
def vector_store(mock_db, mock_openai):
    """Create a VectorStore with mocked dependencies."""
    return VectorStore(mock_db, mock_openai)


# ---------------------------------------------------------------------------
# TestFindSimilarFailures
# ---------------------------------------------------------------------------

class TestFindSimilarFailures:
    """find_similar_failures uses embeddings to search."""

    @pytest.mark.asyncio
    async def test_calls_create_embedding(self, vector_store, mock_openai):
        await vector_store.find_similar_failures("ImportError: no module named x")
        mock_openai.create_embedding.assert_awaited_once_with("ImportError: no module named x")

    @pytest.mark.asyncio
    async def test_calls_execute_query(self, vector_store, mock_db):
        await vector_store.find_similar_failures("TypeError")
        mock_db.execute_query.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_no_results(self, vector_store, mock_db):
        mock_db.execute_query.return_value = None
        result = await vector_store.find_similar_failures("unknown error")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_results_when_found(self, vector_store, mock_db):
        mock_db.execute_query.return_value = [
            {"failure_id": "1", "error_signature": "TypeError: X", "similarity": 0.9}
        ]
        result = await vector_store.find_similar_failures("TypeError: Y")
        assert len(result) == 1
        assert result[0]["similarity"] == 0.9

    @pytest.mark.asyncio
    async def test_returns_empty_on_embedding_failure(self, vector_store, mock_openai):
        mock_openai.create_embedding.side_effect = Exception("API error")
        result = await vector_store.find_similar_failures("error")
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_limit_and_threshold(self, vector_store, mock_db):
        await vector_store.find_similar_failures("error", limit=3, similarity_threshold=0.8)
        call_args = mock_db.execute_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert params[-1] == 3  # limit
        assert 0.8 in params  # threshold


# ---------------------------------------------------------------------------
# TestFindSimilarPatterns
# ---------------------------------------------------------------------------

class TestFindSimilarPatterns:
    """find_similar_patterns searches with optional problem_type filter."""

    @pytest.mark.asyncio
    async def test_calls_create_embedding(self, vector_store, mock_openai):
        await vector_store.find_similar_patterns("build a REST API")
        mock_openai.create_embedding.assert_awaited_once_with("build a REST API")

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self, vector_store, mock_db):
        mock_db.execute_query.return_value = None
        result = await vector_store.find_similar_patterns("task")
        assert result == []

    @pytest.mark.asyncio
    async def test_problem_type_filter_included(self, vector_store, mock_db):
        await vector_store.find_similar_patterns("task", problem_type="api")
        call_args = mock_db.execute_query.call_args
        query = call_args[0][0]
        assert "problem_type = %s" in query

    @pytest.mark.asyncio
    async def test_no_problem_type_filter_when_none(self, vector_store, mock_db):
        await vector_store.find_similar_patterns("task", problem_type=None)
        call_args = mock_db.execute_query.call_args
        query = call_args[0][0]
        assert "problem_type = %s" not in query

    @pytest.mark.asyncio
    async def test_returns_empty_on_embedding_failure(self, vector_store, mock_openai):
        mock_openai.create_embedding.side_effect = Exception("API error")
        result = await vector_store.find_similar_patterns("task")
        assert result == []


# ---------------------------------------------------------------------------
# TestStoreFailure
# ---------------------------------------------------------------------------

class TestStoreFailure:
    """store_failure_with_embedding generates embedding and stores."""

    @pytest.mark.asyncio
    async def test_delegates_to_db(self, vector_store, mock_db):
        task_id = uuid4()
        iteration_id = uuid4()

        result = await vector_store.store_failure_with_embedding(
            task_id=task_id,
            iteration_id=iteration_id,
            error_signature="TypeError: X",
            error_type="TypeError",
            full_error="TypeError: X at line 42",
        )

        mock_db.store_failure.assert_awaited_once()
        assert isinstance(result, UUID)

    @pytest.mark.asyncio
    async def test_generates_embedding(self, vector_store, mock_openai):
        await vector_store.store_failure_with_embedding(
            task_id=uuid4(),
            iteration_id=uuid4(),
            error_signature="ImportError: X",
            error_type="ImportError",
            full_error="ImportError: X",
        )

        mock_openai.create_embedding.assert_awaited_once()
        # Embedding text should combine error_type and signature
        call_args = mock_openai.create_embedding.call_args[0][0]
        assert "ImportError" in call_args

    @pytest.mark.asyncio
    async def test_stores_without_embedding_on_failure(self, vector_store, mock_openai, mock_db):
        mock_openai.create_embedding.side_effect = Exception("API error")

        await vector_store.store_failure_with_embedding(
            task_id=uuid4(),
            iteration_id=uuid4(),
            error_signature="TypeError",
            error_type="TypeError",
            full_error="TypeError",
        )

        # Should still store, but with embedding=None
        call_kwargs = mock_db.store_failure.call_args[1]
        assert call_kwargs["embedding"] is None

    @pytest.mark.asyncio
    async def test_passes_optional_fields(self, vector_store, mock_db):
        await vector_store.store_failure_with_embedding(
            task_id=uuid4(),
            iteration_id=uuid4(),
            error_signature="E",
            error_type="E",
            full_error="full error",
            root_cause="bad logic",
            code_context="x = 1",
        )

        call_kwargs = mock_db.store_failure.call_args[1]
        assert call_kwargs["root_cause"] == "bad logic"
        assert call_kwargs["code_context"] == "x = 1"


# ---------------------------------------------------------------------------
# TestStorePattern
# ---------------------------------------------------------------------------

class TestStorePattern:
    """store_pattern_with_embedding generates embedding and stores."""

    @pytest.mark.asyncio
    async def test_delegates_to_db(self, vector_store, mock_db):
        result = await vector_store.store_pattern_with_embedding(
            problem_type="api",
            description="REST API pattern",
            code_template="from flask import Flask",
        )

        mock_db.store_pattern.assert_awaited_once()
        assert isinstance(result, UUID)

    @pytest.mark.asyncio
    async def test_stores_without_embedding_on_failure(self, vector_store, mock_openai, mock_db):
        mock_openai.create_embedding.side_effect = Exception("API failed")

        await vector_store.store_pattern_with_embedding(
            problem_type="api",
            description="test",
            code_template="pass",
        )

        call_kwargs = mock_db.store_pattern.call_args[1]
        assert call_kwargs["embedding"] is None


# ---------------------------------------------------------------------------
# TestStatistics
# ---------------------------------------------------------------------------

class TestStatistics:
    """Statistics queries return results from DB."""

    @pytest.mark.asyncio
    async def test_failure_statistics(self, vector_store, mock_db):
        mock_db.execute_query.return_value = [
            {"total_failures": 10, "fixed_failures": 7}
        ]
        result = await vector_store.get_failure_statistics()
        assert result["total_failures"] == 10

    @pytest.mark.asyncio
    async def test_failure_statistics_empty(self, vector_store, mock_db):
        mock_db.execute_query.return_value = None
        result = await vector_store.get_failure_statistics()
        assert result == {}

    @pytest.mark.asyncio
    async def test_pattern_statistics(self, vector_store, mock_db):
        mock_db.execute_query.return_value = [
            {"total_patterns": 5, "avg_success_rate": 0.85}
        ]
        result = await vector_store.get_pattern_statistics()
        assert result["total_patterns"] == 5

    @pytest.mark.asyncio
    async def test_pattern_statistics_empty(self, vector_store, mock_db):
        mock_db.execute_query.return_value = None
        result = await vector_store.get_pattern_statistics()
        assert result == {}
