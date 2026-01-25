"""Agent module - exports and factory for all agents.

Provides a unified interface for creating and managing agents.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from src.agents.base_agent import BaseAgent
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.tester import TesterAgent
from src.agents.reflector import ReflectorAgent
from src.agents.code_reviewer import CodeReviewerAgent
from src.agents.security_auditor import SecurityAuditorAgent

# Export all agents
__all__ = [
    'BaseAgent',
    'PlannerAgent',
    'CoderAgent',
    'TesterAgent',
    'ReflectorAgent',
    'CodeReviewerAgent',
    'SecurityAuditorAgent',
    'AgentFactory',
    'create_agent',
]

# Agent type registry
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    'planner': PlannerAgent,
    'coder': CoderAgent,
    'tester': TesterAgent,
    'reflector': ReflectorAgent,
    'code_reviewer': CodeReviewerAgent,
    'security_auditor': SecurityAuditorAgent,
}


class AgentFactory:
    """Factory for creating agent instances.

    Provides a centralized way to create agents with consistent configuration.
    """

    def __init__(
        self,
        openai_client: Any,
        vector_store: Any,
        prompts: Dict[str, Any],
        workspace_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the agent factory.

        Args:
            openai_client: OpenAI client for LLM calls
            vector_store: Vector store for memory
            prompts: System prompts configuration
            workspace_path: Path to workspace directory
            config: Full configuration dictionary
        """
        self.openai_client = openai_client
        self.vector_store = vector_store
        self.prompts = prompts
        self.workspace_path = workspace_path
        self.config = config or {}
        self._instances: Dict[str, BaseAgent] = {}

    def create(self, agent_type: str, **kwargs) -> BaseAgent:
        """Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create (e.g., 'planner', 'coder')
            **kwargs: Additional arguments passed to agent constructor

        Returns:
            Agent instance

        Raises:
            ValueError: If agent_type is not registered
        """
        if agent_type not in AGENT_REGISTRY:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available types: {list(AGENT_REGISTRY.keys())}"
            )

        agent_class = AGENT_REGISTRY[agent_type]

        # Build constructor arguments
        init_kwargs = {
            'agent_type': agent_type,
            'openai_client': self.openai_client,
            'vector_store': self.vector_store,
            'prompts': self.prompts,
        }

        # Add workspace_path for agents that need it
        if agent_type in ('coder', 'tester'):
            init_kwargs['workspace_path'] = kwargs.get('workspace_path', self.workspace_path)

        # Add config for tester
        if agent_type == 'tester':
            init_kwargs['config'] = kwargs.get('config', self.config)

        # Override with any provided kwargs
        init_kwargs.update(kwargs)

        return agent_class(**init_kwargs)

    def get_or_create(self, agent_type: str, **kwargs) -> BaseAgent:
        """Get an existing agent instance or create a new one.

        Args:
            agent_type: Type of agent
            **kwargs: Additional arguments for creation

        Returns:
            Agent instance (cached if previously created)
        """
        if agent_type not in self._instances:
            self._instances[agent_type] = self.create(agent_type, **kwargs)
        return self._instances[agent_type]

    def create_all_core_agents(self) -> Dict[str, BaseAgent]:
        """Create all core agents (planner, coder, tester, reflector).

        Returns:
            Dictionary of agent_type -> agent instance
        """
        core_types = ['planner', 'coder', 'tester', 'reflector']
        return {t: self.get_or_create(t) for t in core_types}

    def create_review_agents(self) -> Dict[str, BaseAgent]:
        """Create code review and security audit agents.

        Returns:
            Dictionary of agent_type -> agent instance
        """
        review_types = ['code_reviewer', 'security_auditor']
        return {t: self.get_or_create(t) for t in review_types}


def create_agent(
    agent_type: str,
    openai_client: Any,
    vector_store: Any,
    prompts: Dict[str, Any],
    **kwargs
) -> BaseAgent:
    """Convenience function to create a single agent.

    Args:
        agent_type: Type of agent to create
        openai_client: OpenAI client
        vector_store: Vector store
        prompts: System prompts
        **kwargs: Additional arguments

    Returns:
        Agent instance
    """
    factory = AgentFactory(
        openai_client=openai_client,
        vector_store=vector_store,
        prompts=prompts,
        **kwargs
    )
    return factory.create(agent_type)
