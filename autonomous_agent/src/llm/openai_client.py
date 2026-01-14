"""OpenAI API client with flexible model support and retry logic."""

import os
from typing import Any, Dict, List, Optional

import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.ui.logger import get_logger


class OpenAIClient:
    """Flexible OpenAI client supporting any model via configuration."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the OpenAI client.

        Args:
            config: OpenAI configuration dictionary from config/openai.yaml
        """
        self.config = config['openai']
        self.api_key = os.getenv("OPENAI_API_KEY") or self.config.get('api_key')
        self.organization = os.getenv("OPENAI_ORG_ID") or self.config.get('organization')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or config")

        self.client = openai.OpenAI(
            api_key=self.api_key,
            organization=self.organization
        )

        self.models = self.config.get('models', {})
        self.temperature = self.config.get('temperature', 0.2)
        self.max_tokens = self.config.get('max_tokens', 4096)
        self.fallback_enabled = config.get('fallback', {}).get('enabled', False)
        self.fallback_sequence = config.get('fallback', {}).get('sequence', [])

        self.logger = get_logger('openai_client')
        self.total_tokens_used = 0

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the configured model for a specific agent type.

        Args:
            agent_type: Agent type ('planner', 'coder', 'tester', 'reflector')

        Returns:
            Model name (e.g., 'gpt-4-turbo-preview')
        """
        return self.models.get(agent_type, "gpt-4-turbo-preview")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError
        ))
    )
    def chat_completion(
        self,
        agent_type: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> openai.types.chat.ChatCompletion:
        """Generate a chat completion with retry logic.

        Args:
            agent_type: Type of agent ('planner', 'coder', 'tester', 'reflector')
            messages: List of message dictionaries
            tools: Optional tool/function definitions
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            OpenAI ChatCompletion response

        Raises:
            openai.OpenAIError: If all retries fail
        """
        model = self.get_model_for_agent(agent_type)

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        self.logger.info(
            "chat_completion_request",
            agent_type=agent_type,
            model=model,
            message_count=len(messages),
            has_tools=tools is not None
        )

        try:
            response = self.client.chat.completions.create(**params)
            self._log_token_usage(agent_type, response.usage)
            return response

        except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
            self.logger.warning(
                "openai_api_error",
                error_type=type(e).__name__,
                message=str(e),
                agent_type=agent_type
            )
            raise

        except Exception as e:
            # Try fallback models if configured
            if self.fallback_enabled and self.fallback_sequence:
                return self._try_fallback_models(params, agent_type, messages, tools)
            raise

    def _try_fallback_models(
        self,
        params: Dict[str, Any],
        agent_type: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]]
    ) -> openai.types.chat.ChatCompletion:
        """Try fallback models in sequence.

        Args:
            params: Original request parameters
            agent_type: Type of agent
            messages: List of messages
            tools: Optional tools

        Returns:
            OpenAI ChatCompletion response

        Raises:
            Exception: If all fallback models fail
        """
        for fallback_model in self.fallback_sequence:
            try:
                self.logger.info(
                    "trying_fallback_model",
                    original_model=params['model'],
                    fallback_model=fallback_model,
                    agent_type=agent_type
                )

                params['model'] = fallback_model
                response = self.client.chat.completions.create(**params)
                self._log_token_usage(agent_type, response.usage)
                return response

            except Exception as e:
                self.logger.warning(
                    "fallback_model_failed",
                    model=fallback_model,
                    error=str(e)
                )
                continue

        raise Exception("All fallback models failed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError
        ))
    )
    def create_embedding(self, text: str) -> List[float]:
        """Generate an embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)
        """
        model = self.models.get("embedding", "text-embedding-3-large")

        self.logger.debug(
            "embedding_request",
            model=model,
            text_length=len(text)
        )

        response = self.client.embeddings.create(
            model=model,
            input=text
        )

        # Track token usage
        if hasattr(response, 'usage') and response.usage:
            self.total_tokens_used += response.usage.total_tokens

        return response.data[0].embedding

    def _log_token_usage(self, agent_type: str, usage: Any):
        """Log token usage from API response.

        Args:
            agent_type: Type of agent
            usage: Usage object from OpenAI response
        """
        if usage:
            tokens_used = usage.total_tokens
            self.total_tokens_used += tokens_used

            self.logger.info(
                "token_usage",
                agent_type=agent_type,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=tokens_used,
                cumulative_tokens=self.total_tokens_used
            )

    def get_total_tokens_used(self) -> int:
        """Get total tokens used in this session.

        Returns:
            Total token count
        """
        return self.total_tokens_used

    def reset_token_counter(self):
        """Reset the token counter."""
        self.total_tokens_used = 0
        self.logger.info("token_counter_reset")
