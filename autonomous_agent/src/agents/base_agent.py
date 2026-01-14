"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.llm.openai_client import OpenAIClient
from src.memory.vector_store import VectorStore
from src.ui.logger import get_logger


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        agent_type: str,
        openai_client: OpenAIClient,
        vector_store: VectorStore,
        prompts: Dict[str, Any]
    ):
        """Initialize base agent.

        Args:
            agent_type: Type of agent ('planner', 'coder', 'tester', 'reflector')
            openai_client: OpenAI client instance
            vector_store: Vector store for memory
            prompts: System prompts from configuration
        """
        self.agent_type = agent_type
        self.openai = openai_client
        self.vector_store = vector_store
        self.prompts = prompts.get(agent_type, {})
        self.logger = get_logger(agent_type)

        self.system_prompt = self.prompts.get('system', '')
        self.user_template = self.prompts.get('user_template', '{input}')

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's primary function.

        Args:
            context: Execution context with task details

        Returns:
            Dictionary with execution results
        """
        pass

    def build_messages(
        self,
        user_content: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Build message list for LLM completion.

        Args:
            user_content: User message content
            conversation_history: Optional previous messages

        Returns:
            List of message dictionaries
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_content})

        return messages

    def call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None
    ) -> Any:
        """Call the LLM with retry logic.

        Args:
            messages: Message list
            tools: Optional tool definitions
            temperature: Optional temperature override

        Returns:
            OpenAI completion response
        """
        try:
            response = self.openai.chat_completion(
                agent_type=self.agent_type,
                messages=messages,
                tools=tools,
                temperature=temperature
            )

            self.logger.info(
                "llm_call_successful",
                agent_type=self.agent_type,
                finish_reason=response.choices[0].finish_reason
            )

            return response

        except Exception as e:
            self.logger.error(
                "llm_call_failed",
                agent_type=self.agent_type,
                error=str(e)
            )
            raise

    def format_user_message(self, **kwargs) -> str:
        """Format user message using template.

        Args:
            **kwargs: Template variables

        Returns:
            Formatted message string
        """
        try:
            return self.user_template.format(**kwargs)
        except KeyError as e:
            self.logger.warning(
                "template_formatting_error",
                missing_key=str(e),
                template=self.user_template[:100]
            )
            # Fallback to simple concatenation
            return str(kwargs)

    def extract_text_response(self, response: Any) -> str:
        """Extract text content from LLM response.

        Args:
            response: OpenAI completion response

        Returns:
            Response text content
        """
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message.content:
                return message.content
        return ""

    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response.

        Args:
            response: OpenAI completion response

        Returns:
            List of tool call dictionaries
        """
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                return [
                    {
                        'id': tc.id,
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                    for tc in message.tool_calls
                ]
        return []
