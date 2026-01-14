"""Planner agent for task decomposition and planning."""

from typing import Any, Dict

from src.agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """Agent responsible for breaking down tasks into actionable subtasks."""

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed implementation plan.

        Args:
            context: Dictionary containing:
                - task_description: User's task description
                - goal: Structured goal statement
                - iteration: Current iteration number

        Returns:
            Dictionary with:
                - plan: Structured plan
                - subtasks: List of subtasks
                - dependencies: Required dependencies
                - challenges: Expected challenges
        """
        task_description = context.get('task_description', '')
        goal = context.get('goal', '')
        language = context.get('language')
        problem_type = context.get('problem_type')

        self.logger.info("planning_started", task=task_description)

        # Query similar patterns from memory
        pattern_matches = self.vector_store.find_similar_patterns(
            task_description=task_description,
            problem_type=problem_type,
            limit=3
        )

        # Format pattern matches for context
        pattern_context = self._format_pattern_matches(pattern_matches)

        # Build user message from template
        user_message = self.format_user_message(
            task_description=task_description,
            goal=goal,
            pattern_matches=pattern_context
        )

        if str(language).lower() in {"node", "javascript", "js"}:
            user_message = (
                "Runtime: Node.js (JavaScript).\n"
                "Plan should assume a Node project, include a package.json if needed, and prefer node:test for tests.\n\n"
                + user_message
            )

        # Call LLM
        messages = self.build_messages(user_message)
        response = self.call_llm(messages)

        # Extract and parse plan
        plan_text = self.extract_text_response(response)

        # Parse plan into structured format
        parsed_plan = self._parse_plan(plan_text)

        self.logger.info(
            "planning_completed",
            subtask_count=len(parsed_plan.get('subtasks', []))
        )

        return {
            'plan': plan_text,
            'subtasks': parsed_plan.get('subtasks', []),
            'dependencies': parsed_plan.get('dependencies', []),
            'challenges': parsed_plan.get('challenges', []),
            'pattern_matches': pattern_matches
        }

    def _format_pattern_matches(self, patterns: list) -> str:
        """Format pattern matches for inclusion in prompt.

        Args:
            patterns: List of similar patterns

        Returns:
            Formatted string
        """
        if not patterns:
            return "No similar patterns found in memory."

        formatted = []
        for i, pattern in enumerate(patterns, 1):
            formatted.append(
                f"{i}. {pattern.get('problem_type', 'Unknown')} "
                f"(similarity: {pattern.get('similarity', 0):.2f})\n"
                f"   Description: {pattern.get('description', 'N/A')}\n"
                f"   Success rate: {pattern.get('success_rate', 0):.1%}"
            )

        return "\n".join(formatted)

    def _parse_plan(self, plan_text: str) -> Dict[str, Any]:
        """Parse plan text into structured components.

        Args:
            plan_text: Raw plan text from LLM

        Returns:
            Dictionary with parsed components
        """
        # Simple parsing - look for numbered lists and sections
        lines = plan_text.split('\n')

        subtasks = []
        dependencies = []
        challenges = []

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            lower_line = line.lower()
            if 'subtask' in lower_line or 'step' in lower_line:
                current_section = 'subtasks'
            elif 'dependenc' in lower_line or 'requirement' in lower_line:
                current_section = 'dependencies'
            elif 'challenge' in lower_line or 'risk' in lower_line:
                current_section = 'challenges'

            # Extract numbered items
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering and bullets
                clean_line = line.lstrip('0123456789.-*) ').strip()

                if current_section == 'subtasks':
                    subtasks.append(clean_line)
                elif current_section == 'dependencies':
                    dependencies.append(clean_line)
                elif current_section == 'challenges':
                    challenges.append(clean_line)

        return {
            'subtasks': subtasks,
            'dependencies': dependencies,
            'challenges': challenges
        }
