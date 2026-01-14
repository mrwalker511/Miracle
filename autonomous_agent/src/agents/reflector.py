"""Reflector agent for error analysis and hypothesis generation."""

import re
from typing import Any, Dict, List

from src.agents.base_agent import BaseAgent


class ReflectorAgent(BaseAgent):
    """Agent responsible for analyzing failures and generating fixes."""

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test failure and propose a fix.

        Args:
            context: Dictionary containing:
                - test_results: Test execution results
                - code_files: Dictionary of code files
                - iteration: Current iteration number

        Returns:
            Dictionary with:
                - error_type: Type of error
                - error_signature: Normalized error pattern
                - root_cause: Root cause analysis
                - hypothesis: Proposed fix
                - similar_failures: Similar past failures
        """
        test_results = context.get('test_results', {})
        code_files = context.get('code_files', {})
        iteration = context.get('iteration', 1)

        self.logger.info("reflection_started", iteration=iteration)

        # Extract error information
        error_info = self._extract_error_info(test_results)

        if not error_info['error_message']:
            self.logger.warning("no_error_found_in_test_results")
            return {
                'error_type': 'Unknown',
                'error_signature': 'No error message found',
                'root_cause': 'Unable to determine',
                'hypothesis': 'Re-run tests to get error details',
                'similar_failures': []
            }

        # Search for similar failures
        similar_failures = self.vector_store.find_similar_failures(
            error_message=error_info['error_signature'],
            limit=3
        )

        # Format similar failures for context
        similar_context = self._format_similar_failures(similar_failures)

        # Build code context
        code_context = "\n\n".join([
            f"# {filename}\n{content}"
            for filename, content in code_files.items()
        ])

        # Build user message
        user_message = self.format_user_message(
            test_results=str(test_results),
            error_message=error_info['error_message'],
            stack_trace=error_info['stack_trace'],
            code=code_context,
            similar_failures=similar_context
        )

        # Call LLM
        messages = self.build_messages(user_message)
        response = self.call_llm(messages)

        # Parse reflection
        reflection_text = self.extract_text_response(response)
        parsed_reflection = self._parse_reflection(reflection_text)

        self.logger.info(
            "reflection_completed",
            error_type=error_info['error_type'],
            similar_found=len(similar_failures)
        )

        return {
            'error_type': error_info['error_type'],
            'error_signature': error_info['error_signature'],
            'full_error': error_info['error_message'],
            'stack_trace': error_info['stack_trace'],
            'root_cause': parsed_reflection.get('root_cause', ''),
            'hypothesis': parsed_reflection.get('hypothesis', ''),
            'reflection': reflection_text,
            'similar_failures': similar_failures,
            'code_changes': parsed_reflection.get('code_changes', [])
        }

    def _extract_error_info(self, test_results: Dict[str, Any]) -> Dict[str, str]:
        """Extract error information from test results.

        Args:
            test_results: Test execution results

        Returns:
            Dictionary with error details
        """
        error_message = test_results.get('error_message', '')
        stderr = test_results.get('stderr', '')
        stack_trace = test_results.get('stack_trace', '')

        # Combine all error sources
        full_error = error_message or stderr or str(test_results.get('test_results', {}))

        # Extract error type (e.g., ImportError, AttributeError)
        error_type = self._extract_error_type(full_error)

        # Create error signature (normalized pattern)
        error_signature = self._create_error_signature(full_error, error_type)

        return {
            'error_message': full_error,
            'error_type': error_type,
            'error_signature': error_signature,
            'stack_trace': stack_trace or stderr
        }

    def _extract_error_type(self, error_text: str) -> str:
        """Extract error type from error message.

        Args:
            error_text: Error message text

        Returns:
            Error type (e.g., 'ImportError', 'AttributeError')
        """
        # Common Python error types
        error_types = [
            'ImportError', 'ModuleNotFoundError', 'AttributeError',
            'TypeError', 'ValueError', 'KeyError', 'IndexError',
            'NameError', 'RuntimeError', 'SyntaxError',
            'IndentationError', 'FileNotFoundError', 'AssertionError'
        ]

        for error_type in error_types:
            if error_type in error_text:
                return error_type

        return 'UnknownError'

    def _create_error_signature(self, error_text: str, error_type: str) -> str:
        """Create a normalized error signature for similarity matching.

        Args:
            error_text: Error message
            error_type: Type of error

        Returns:
            Normalized error signature
        """
        # Extract the most relevant line
        lines = error_text.split('\n')

        for line in lines:
            if error_type in line:
                # Remove file paths and line numbers
                normalized = re.sub(r'File ".*?", line \d+', '', line)
                # Remove specific variable names in quotes
                normalized = re.sub(r"'[^']*?'", "'X'", normalized)
                return normalized.strip()

        # Fallback: use first non-empty line
        for line in lines:
            if line.strip():
                return f"{error_type}: {line.strip()[:100]}"

        return f"{error_type}: Unknown error"

    def _format_similar_failures(self, failures: List[Dict[str, Any]]) -> str:
        """Format similar failures for inclusion in prompt.

        Args:
            failures: List of similar failures

        Returns:
            Formatted string
        """
        if not failures:
            return "No similar past failures found."

        formatted = []
        for i, failure in enumerate(failures, 1):
            formatted.append(
                f"{i}. {failure.get('error_type', 'Unknown')} "
                f"(similarity: {failure.get('similarity', 0):.2f})\n"
                f"   Signature: {failure.get('error_signature', 'N/A')}\n"
                f"   Root cause: {failure.get('root_cause', 'Not analyzed')}\n"
                f"   Solution: {failure.get('solution', 'Not documented')}"
            )

        return "\n\n".join(formatted)

    def _parse_reflection(self, reflection_text: str) -> Dict[str, Any]:
        """Parse reflection text into structured components.

        Args:
            reflection_text: Raw reflection from LLM

        Returns:
            Dictionary with parsed components
        """
        lines = reflection_text.split('\n')

        root_cause = []
        hypothesis = []
        code_changes = []

        current_section = None

        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue

            lower_line = line_strip.lower()

            # Detect sections
            if 'root cause' in lower_line or 'cause:' in lower_line:
                current_section = 'root_cause'
            elif 'hypothesis' in lower_line or 'fix:' in lower_line or 'solution:' in lower_line:
                current_section = 'hypothesis'
            elif 'code change' in lower_line or 'modification' in lower_line:
                current_section = 'code_changes'
            elif current_section:
                # Add content to current section
                if current_section == 'root_cause':
                    root_cause.append(line_strip)
                elif current_section == 'hypothesis':
                    hypothesis.append(line_strip)
                elif current_section == 'code_changes':
                    code_changes.append(line_strip)

        return {
            'root_cause': ' '.join(root_cause) if root_cause else reflection_text[:200],
            'hypothesis': ' '.join(hypothesis) if hypothesis else 'Fix the identified issue',
            'code_changes': code_changes
        }
