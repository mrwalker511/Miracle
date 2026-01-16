"""Tests for token counter."""

import pytest

from src.llm.token_counter import TokenCounter


class TestTokenCounter:
    """Test cases for TokenCounter."""

    def test_initialization_gpt4(self):
        """Test initialization with GPT-4 model."""
        counter = TokenCounter(model="gpt-4")
        assert counter.encoding is not None

    def test_initialization_gpt35(self):
        """Test initialization with GPT-3.5-turbo."""
        counter = TokenCounter(model="gpt-3.5-turbo")
        assert counter.encoding is not None

    def test_initialization_unknown_model(self):
        """Test initialization with unknown model (uses default)."""
        counter = TokenCounter(model="unknown-model")
        assert counter.encoding is not None

    def test_count_tokens_empty_string(self):
        """Test counting tokens in empty string."""
        counter = TokenCounter()
        count = counter.count_tokens("")
        assert count == 0

    def test_count_tokens_simple_text(self):
        """Test counting tokens in simple text."""
        counter = TokenCounter()
        count = counter.count_tokens("Hello, world!")
        assert count > 0

    def test_count_tokens_longer_text(self):
        """Test counting tokens in longer text."""
        counter = TokenCounter()
        text = "This is a longer text to test token counting with more words."
        short_count = counter.count_tokens("Short text.")
        long_count = counter.count_tokens(text)
        assert long_count > short_count

    def test_count_tokens_code(self):
        """Test counting tokens in code."""
        counter = TokenCounter()
        code = """
def hello_world():
    print("Hello, World!")

hello_world()
        """.strip()

        count = counter.count_tokens(code)
        assert count > 0

    def test_count_messages_empty(self):
        """Test counting tokens in empty messages list."""
        counter = TokenCounter()
        count = counter.count_messages_tokens([])
        # Every reply is primed with <im_start>assistant
        assert count == 2

    def test_count_messages_single(self):
        """Test counting tokens in single message."""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]

        count = counter.count_messages_tokens(messages)
        assert count > 2  # More than just the base tokens

    def test_count_messages_multiple(self):
        """Test counting tokens in multiple messages."""
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        count = counter.count_messages_tokens(messages)
        assert count > 0

    def test_count_messages_with_name(self):
        """Test counting tokens with named messages."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "name": "Alice", "content": "Hello"}
        ]

        count = counter.count_messages_tokens(messages)
        assert count > 0

    def test_estimate_cost_gpt4_turbo(self):
        """Test cost estimation for GPT-4-turbo."""
        counter = TokenCounter()
        cost = counter.estimate_cost(1000, 1000, "gpt-4-turbo-preview")

        # Cost should be positive and reasonable
        assert cost > 0
        # GPT-4-turbo costs roughly $0.04 for 1000 tokens total
        assert 0.01 < cost < 0.1

    def test_estimate_cost_gpt35(self):
        """Test cost estimation for GPT-3.5-turbo."""
        counter = TokenCounter()
        cost = counter.estimate_cost(1000, 1000, "gpt-3.5-turbo")

        # Should be cheaper than GPT-4
        gpt4_cost = counter.estimate_cost(1000, 1000, "gpt-4")
        assert cost < gpt4_cost

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation with unknown model."""
        counter = TokenCounter()
        cost = counter.estimate_cost(1000, 1000, "unknown-model")

        # Should default to GPT-4 pricing
        default_cost = counter.estimate_cost(1000, 1000, "gpt-4")
        assert cost == default_cost

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        counter = TokenCounter()
        cost = counter.estimate_cost(0, 0, "gpt-4-turbo-preview")
        assert cost == 0

    def test_estimate_cost_completions_more_expensive(self):
        """Test that completion tokens cost more than prompt."""
        counter = TokenCounter()

        prompt_cost = counter.estimate_cost(1000, 0, "gpt-4")
        completion_cost = counter.estimate_cost(0, 1000, "gpt-4")

        # For GPT-4, completions are 2x more expensive
        assert completion_cost > prompt_cost

    def test_count_tokens_special_characters(self):
        """Test counting tokens with special characters."""
        counter = TokenCounter()
        text = "Testing 🎉 special @#$%^&*() characters!"

        count = counter.count_tokens(text)
        assert count > 0

    def test_count_tokens_multiline(self):
        """Test counting tokens in multiline text."""
        counter = TokenCounter()
        text = """Line 1
Line 2
Line 3"""

        count = counter.count_tokens(text)
        assert count > 0
