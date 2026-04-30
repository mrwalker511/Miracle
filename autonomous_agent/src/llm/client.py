"""Generic LLM client using LiteLLM for flexible provider support and retry logic."""

import os
from typing import Any, Dict, List, Optional

import litellm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.ui.logger import get_logger

# Optional: drop litellm diagnostics spam
litellm.suppress_debug_info = True


class LLMClient:
    """Flexible LLM client supporting arbitrary providers via LiteLLM."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM client.

        Args:
            config: Full configuration dictionary containing the 'llm' key
        """
        self.config = config.get('llm', {})
        self.api_key = os.getenv("OPENAI_API_KEY") or self.config.get('api_key') or None
        self.base_url = os.getenv("LLM_BASE_URL") or self.config.get('base_url')

        self.models = self.config.get('models', {})
        self.temperature = self.config.get('temperature', 0.2)
        self.max_tokens = self.config.get('max_tokens', 4096)
        
        # Parent fallback block if mapped
        fallback_cfg = config.get('fallback', {})
        self.fallback_enabled = fallback_cfg.get('enabled', False)
        self.fallback_sequence = fallback_cfg.get('sequence', [])

        self.logger = get_logger('llm_client')
        self.total_tokens_used = 0

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the configured model for a specific agent type.

        Args:
            agent_type: Agent type ('planner', 'coder', 'tester', 'reflector')

        Returns:
            Model string in LiteLLM generic format (e.g., 'openai/gpt-4-turbo', 'ollama/llama3')
        """
        return self.models.get(agent_type, "openai/gpt-4-turbo-preview")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            litellm.exceptions.RateLimitError,
            litellm.exceptions.Timeout,
            litellm.exceptions.APIConnectionError
        ))
    )
    async def chat_completion(
        self,
        agent_type: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Any:
        """Generate a chat completion with retry logic.

        Args:
            agent_type: Type of agent ('planner', 'coder', 'tester', 'reflector')
            messages: List of message dictionaries
            tools: Optional tool/function definitions
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            LiteLLM ChatCompletion response (OpenAI schema compatible)
        """
        model = self.get_model_for_agent(agent_type)

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["api_base"] = self.base_url

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
            response = await litellm.acompletion(**params)
            self._log_token_usage(agent_type, getattr(response, 'usage', None))
            return response

        except (litellm.exceptions.RateLimitError, litellm.exceptions.Timeout, litellm.exceptions.APIConnectionError) as e:
            self.logger.warning(
                "llm_api_timeout_or_limit",
                error_type=type(e).__name__,
                message=str(e),
                agent_type=agent_type
            )
            raise

        except Exception as e:
            # Try fallback models if configured
            if self.fallback_enabled and self.fallback_sequence:
                return await self._try_fallback_models(params, agent_type, messages, tools)
            
            self.logger.error("llm_api_critical_failure", error=str(e))
            raise

    async def _try_fallback_models(
        self,
        params: Dict[str, Any],
        agent_type: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]]
    ) -> Any:
        """Try fallback models in sequence.

        Args:
            params: Original request parameters
            agent_type: Type of agent
            messages: List of messages
            tools: Optional tools

        Returns:
            ChatCompletion response

        Raises:
            Exception: If all fallback models fail
        """
        original_model = params.get('model')
        for fallback_model in self.fallback_sequence:
            try:
                self.logger.info(
                    "trying_fallback_model",
                    original_model=original_model,
                    fallback_model=fallback_model,
                    agent_type=agent_type
                )

                params['model'] = fallback_model
                response = await litellm.acompletion(**params)
                self._log_token_usage(agent_type, getattr(response, 'usage', None))
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
            litellm.exceptions.RateLimitError,
            litellm.exceptions.Timeout,
            litellm.exceptions.APIConnectionError
        ))
    )
    async def create_embedding(self, text: str) -> List[float]:
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
        
        params = {"model": model, "input": [text]}
        if self.base_url and not model.startswith('openai'):
            # Specific behavior: Only forward custom api_base if local model, 
            # or forward it broadly depending on litellm overrides.
            params["api_base"] = self.base_url

        response = await litellm.aembedding(**params)

        # Track token usage
        if hasattr(response, 'usage') and response.usage:
            self.total_tokens_used += response.usage.total_tokens

        return response.data[0]['embedding']

    def _log_token_usage(self, agent_type: str, usage: Any):
        """Log token usage from API response.

        Args:
            agent_type: Type of agent
            usage: Usage object from OpenAI/LiteLLM response
        """
        if usage:
            # handle both dot notation or dict format natively wrapped by litellm
            total_tokens = getattr(usage, 'total_tokens', usage.get('total_tokens', 0) if isinstance(usage, dict) else 0)
            prompt_tokens = getattr(usage, 'prompt_tokens', usage.get('prompt_tokens', 0) if isinstance(usage, dict) else 0)
            completion_tokens = getattr(usage, 'completion_tokens', usage.get('completion_tokens', 0) if isinstance(usage, dict) else 0)
            
            self.total_tokens_used += total_tokens

            self.logger.info(
                "token_usage",
                agent_type=agent_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cumulative_tokens=self.total_tokens_used
            )

    def get_total_tokens_used(self) -> int:
        """Get total tokens used in this session."""
        return self.total_tokens_used

    def reset_token_counter(self):
        """Reset the token counter."""
        self.total_tokens_used = 0
        self.logger.info("token_counter_reset")
