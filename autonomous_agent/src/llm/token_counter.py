"""Token counting utilities using tiktoken."""

from typing import List, Dict
import tiktoken


class TokenCounter:
    """Count tokens for OpenAI models using tiktoken."""

    def __init__(self, model: str = "gpt-4"):
        """Initialize token counter.

        Args:
            model: Model name for encoding (e.g., 'gpt-4', 'gpt-3.5-turbo')
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Default to cl100k_base encoding for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of chat messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Approximate token count for messages
        """
        # Based on OpenAI's token counting for chat completions
        tokens = 0

        for message in messages:
            tokens += 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                tokens += self.count_tokens(str(value))
                if key == "name":
                    tokens += -1  # Role is always 1 token, name is variable

        tokens += 2  # Every reply is primed with <im_start>assistant

        return tokens

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4-turbo-preview"
    ) -> float:
        """Estimate cost for a completion.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name

        Returns:
            Estimated cost in USD
        """
        # Pricing as of early 2024 (update as needed)
        pricing = {
            "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
        }

        # Default to gpt-4 pricing if model not found
        rates = pricing.get(model, pricing["gpt-4"])

        prompt_cost = (prompt_tokens / 1000) * rates["prompt"]
        completion_cost = (completion_tokens / 1000) * rates["completion"]

        return prompt_cost + completion_cost
