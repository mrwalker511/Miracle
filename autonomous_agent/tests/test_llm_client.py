"""Tests for LiteLLM generic client.

Covers:
- Model selection per agent type
- Token usage tracking
- Fallback model sequence
- Retry behavior (mocked)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import LLMClient


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

CONFIG = {
    "llm": {
        "api_key": "test-api-key-12345",
        "base_url": "http://localhost:8081/v1",
        "models": {
            "planner": "openai/gpt-4-turbo-preview",
            "coder": "openai/gpt-4-turbo-preview",
            "tester": "openai/gpt-3.5-turbo",
            "reflector": "openai/gpt-4-turbo-preview",
            "embedding": "text-embedding-3-large",
        },
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "fallback": {
        "enabled": True,
        "sequence": ["openai/gpt-3.5-turbo", "openai/gpt-3.5-turbo-16k"],
    },
}


@pytest.fixture
def client():
    """Create an LLMClient."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key-12345"}):
        return LLMClient(CONFIG)


# ---------------------------------------------------------------------------
# TestModelSelection
# ---------------------------------------------------------------------------

class TestModelSelection:
    """get_model_for_agent retrieves correct model per agent type."""

    def test_planner_model(self, client):
        assert client.get_model_for_agent("planner") == "openai/gpt-4-turbo-preview"

    def test_tester_model(self, client):
        assert client.get_model_for_agent("tester") == "openai/gpt-3.5-turbo"

    def test_unknown_agent_gets_default(self, client):
        model = client.get_model_for_agent("unknown_agent")
        assert model == "openai/gpt-4-turbo-preview"  # Default fallback


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

    def test_log_token_usage_handles_dict(self, client):
        """LiteLLM sometimes passes dict-like usage objects."""
        usage = {"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50}
        client._log_token_usage("tester", usage)
        assert client.get_total_tokens_used() == 150

    def test_log_token_usage_handles_none(self, client):
        """None usage should not crash."""
        client._log_token_usage("planner", None)
        assert client.get_total_tokens_used() == 0


# ---------------------------------------------------------------------------
# TestChatCompletion
# ---------------------------------------------------------------------------

class TestChatCompletion:
    """chat_completion delegates to litellm.acompletion correctly."""

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.acompletion")
    async def test_basic_completion(self, mock_acompletion, client):
        """Mocked chat completion returns expected structure."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_acompletion.return_value = mock_response

        response = await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert response is mock_response
        assert client.get_total_tokens_used() == 150

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.acompletion")
    async def test_completion_uses_correct_model(self, mock_acompletion, client):
        """Model param matches what's configured for the agent type."""
        mock_response = MagicMock()
        mock_response.usage = None

        mock_acompletion.return_value = mock_response

        await client.chat_completion(
            agent_type="tester",
            messages=[{"role": "user", "content": "test"}],
        )

        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-3.5-turbo"
        assert call_kwargs["api_base"] == "http://localhost:8081/v1"

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.acompletion")
    async def test_tools_passed_through(self, mock_acompletion, client):
        mock_response = MagicMock()
        mock_response.usage = None

        mock_acompletion.return_value = mock_response

        tools = [{"type": "function", "function": {"name": "test_func"}}]
        await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "test"}],
            tools=tools,
        )

        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"


# ---------------------------------------------------------------------------
# TestEmbedding
# ---------------------------------------------------------------------------

class TestEmbedding:
    """create_embedding delegates to litellm.aembedding."""

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.aembedding")
    async def test_embedding_returns_vector(self, mock_aembedding, client):
        mock_response = MagicMock()
        # litellm returns a dict standard structure for embeddings
        mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 10

        mock_aembedding.return_value = mock_response

        result = await client.create_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        assert client.get_total_tokens_used() == 10

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.aembedding")
    async def test_embedding_uses_configured_model(self, mock_aembedding, client):
        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1]}]
        mock_response.usage = None

        mock_aembedding.return_value = mock_response

        await client.create_embedding("test text")

        call_kwargs = mock_aembedding.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-large"


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------

class TestFallback:
    """Fallback model sequence is tried on primary failure."""

    @pytest.mark.asyncio
    @patch("src.llm.client.litellm.acompletion")
    async def test_fallback_tried_on_failure(self, mock_acompletion, client):
        mock_response = MagicMock()
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 20

        # First model fails, fallback succeeds
        mock_acompletion.side_effect = [Exception("Model error"), mock_response]

        response = await client.chat_completion(
            agent_type="planner",
            messages=[{"role": "user", "content": "test"}],
        )

        assert response is mock_response
        # Should have been called twice: once for primary, once for first fallback
        assert mock_acompletion.call_count == 2
        
        # Second call kwargs
        call_kwargs = mock_acompletion.call_args_list[1][1]
        assert call_kwargs["model"] == "openai/gpt-3.5-turbo"

    def test_fallback_enabled(self, client):
        assert client.fallback_enabled is True

    def test_fallback_sequence(self, client):
        assert client.fallback_sequence == ["openai/gpt-3.5-turbo", "openai/gpt-3.5-turbo-16k"]


# ---------------------------------------------------------------------------
# TestClientInit
# ---------------------------------------------------------------------------

class TestClientInit:
    """Client initializes correctly with required config."""

    def test_init_api_key_from_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            config = {"llm": {"models": {}}}
            client = LLMClient(config)
            assert client.api_key == "env-key"
