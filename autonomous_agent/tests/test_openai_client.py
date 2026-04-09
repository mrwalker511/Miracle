"""Tests for OpenAI client.

Covers:
- Model selection per agent type
- Token usage tracking
- Fallback model sequence
- Retry behavior (mocked)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.openai_client import OpenAIClient


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

CONFIG = {
    "openai": {
        "api_key": "test-api-key-12345",
        "organization": None,
        "models": {
            "planner": "gpt-4-turbo-preview",
            "coder": "gpt-4-turbo-preview",
            "tester": "gpt-3.5-turbo",
            "reflector": "gpt-4-turbo-preview",
            "embedding": "text-embedding-3-large",
        },
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "fallback": {
        "enabled": True,
        "sequence": ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"],
    },
}


@pytest.fixture
def client():
    """Create an OpenAIClient with mocked API key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key-12345"}):
        with patch("src.llm.openai_client.openai.AsyncOpenAI"):
            return OpenAIClient(CONFIG)


# ---------------------------------------------------------------------------
# TestModelSelection
# ---------------------------------------------------------------------------

class TestModelSelection:
    """get_model_for_agent retrieves correct model per agent type."""

    def test_planner_model(self, client):
        assert client.get_model_for_agent("planner") == "gpt-4-turbo-preview"

    def test_tester_model(self, client):
        assert client.get_model_for_agent("tester") == "gpt-3.5-turbo"

    def test_unknown_agent_gets_default(self, client):
        model = client.get_model_for_agent("unknown_agent")
        assert model == "gpt-4-turbo-preview"  # Default fallback


# ---------------------------------------------------------------------------
# TestTokenTracking
# ---------------------------------------------------------------------------

class TestTokenTracking:
    """Token usage accumulates and resets correctly."""

    def test_initial_tokens_zero(self, client):
        assert client.get_total_tokens_used() == 0

    def test_token_counter_reset(self, client):
        client.total_tokens_used = 500
        client.reset_token_counter()
        assert client.get_total_tokens_used() == 0

    def test_log_token_usage_accumulates(self, client):
        usage = MagicMock()
        usage.total_tokens = 100
        usage.prompt_tokens = 60
        usage.completion_tokens = 40

        client._log_token_usage("planner", usage)
        assert client.get_total_tokens_used() == 100

        client._log_token_usage("coder", usage)
        assert client.get_total_tokens_used() == 200

    def test_log_token_usage_handles_none(self, client):
        """None usage should not crash."""
        client._log_token_usage("planner", None)
        assert client.get_total_tokens_used() == 0


# ---------------------------------------------------------------------------
# TestChatCompletion
# ---------------------------------------------------------------------------

class TestChatCompletion:
    """chat_completion delegates to AsyncOpenAI correctly."""

    @pytest.mark.asyncio
    async def test_basic_completion(self, client):
        """Mocked chat completion returns expected structure."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert response is mock_response
        assert client.get_total_tokens_used() == 150

    @pytest.mark.asyncio
    async def test_completion_uses_correct_model(self, client):
        """Model param matches what's configured for the agent type."""
        mock_response = MagicMock()
        mock_response.usage = None

        client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await client.chat_completion(
            agent_type="tester",
            messages=[{"role": "user", "content": "test"}],
        )

        call_kwargs = client.client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_tools_passed_through(self, client):
        mock_response = MagicMock()
        mock_response.usage = None

        client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        tools = [{"type": "function", "function": {"name": "test_func"}}]
        await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "test"}],
            tools=tools,
        )

        call_kwargs = client.client.chat.completions.create.call_args[1]
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"


# ---------------------------------------------------------------------------
# TestEmbedding
# ---------------------------------------------------------------------------

class TestEmbedding:
    """create_embedding delegates to the embeddings API."""

    @pytest.mark.asyncio
    async def test_embedding_returns_vector(self, client):
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_data]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10

        client.client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await client.create_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        assert client.get_total_tokens_used() == 10

    @pytest.mark.asyncio
    async def test_embedding_uses_configured_model(self, client):
        mock_data = MagicMock()
        mock_data.embedding = [0.1]

        mock_response = MagicMock()
        mock_response.data = [mock_data]
        mock_response.usage = None

        client.client.embeddings.create = AsyncMock(return_value=mock_response)

        await client.create_embedding("test text")

        call_kwargs = client.client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-large"


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------

class TestFallback:
    """Fallback model sequence is tried on primary failure."""

    @pytest.mark.asyncio
    async def test_fallback_tried_on_failure(self, client):
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 20

        # First model fails, fallback succeeds
        client.client.chat.completions.create = AsyncMock(
            side_effect=[Exception("Model error"), mock_response]
        )

        response = await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "test"}],
        )

        assert response is mock_response
        # Should have been called twice: once for primary, once for first fallback
        assert client.client.chat.completions.create.call_count == 2

    def test_fallback_enabled(self, client):
        assert client.fallback_enabled is True

    def test_fallback_sequence(self, client):
        assert client.fallback_sequence == ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]


# ---------------------------------------------------------------------------
# TestClientInit
# ---------------------------------------------------------------------------

class TestClientInit:
    """Client initializes correctly with required config."""

    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            config = {"openai": {"models": {}}}
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIClient(config)

    def test_env_key_overrides_config(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            with patch("src.llm.openai_client.openai.AsyncOpenAI"):
                config = {"openai": {"api_key": "config-key", "models": {}}}
                client = OpenAIClient(config)
                assert client.api_key == "env-key"
