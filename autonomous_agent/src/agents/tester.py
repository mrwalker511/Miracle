"""Tester agent for test generation and execution."""

import subprocess
import json
from typing import Any, Dict
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.llm.tools import get_testing_tools


class TesterAgent(BaseAgent):
    """Agent responsible for generating and executing tests."""

    def __init__(self, *args, workspace_path: str = "./sandbox/workspace", **kwargs):
        """Initialize tester agent.

        Args:
            workspace_path: Path to sandbox workspace
            *args, **kwargs: Arguments for BaseAgent
        """
        super().__init__(*args, **kwargs)
        self.workspace_path = Path(workspace_path)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and execute tests.

        Args:
            context: Dictionary containing:
                - code_files: Dictionary of code files
                - task_id: Task UUID
                - workspace: Workspace path

        Returns:
            Dictionary with:
                - test_file: Test file path
                - test_results: pytest results
                - passed: Whether tests passed
                - error_message: Error message if failed
        """
        code_files = context.get('code_files', {})
        task_id = str(context.get('task_id', ''))
        workspace = Path(context.get('workspace', self.workspace_path / task_id))

        self.logger.info("testing_started", workspace=str(workspace))

        # Generate test file
        test_generation_result = self._generate_tests(code_files, workspace)

        if not test_generation_result.get('success'):
            return {
                'passed': False,
                'error_message': 'Test generation failed',
                'test_results': {}
            }

        test_file = test_generation_result['test_file']

        # Execute tests
        test_results = self._execute_tests(workspace, test_file)

        self.logger.info(
            "testing_completed",
            passed=test_results.get('passed', False),
            test_count=test_results.get('total', 0)
        )

        return test_results

    def _generate_tests(
        self,
        code_files: Dict[str, str],
        workspace: Path
    ) -> Dict[str, Any]:
        """Generate pytest tests for the code.

        Args:
            code_files: Dictionary of filename -> content
            workspace: Workspace path

        Returns:
            Dictionary with test generation results
        """
        # Extract function signatures from code
        signatures = self._extract_function_signatures(code_files)

        # Build code context
        code_context = "\n\n".join([
            f"# {filename}\n{content}"
            for filename, content in code_files.items()
        ])

        # Build user message
        user_message = self.format_user_message(
            code=code_context,
            signatures=signatures
        )

        # Call LLM
        messages = self.build_messages(user_message)
        tools = get_testing_tools()
        response = self.call_llm(messages, tools=tools)

        # Extract test code
        tool_calls = self.extract_tool_calls(response)
        test_file = None

        for tool_call in tool_calls:
            if tool_call['name'] == 'create_test_file':
                args = json.loads(tool_call['arguments'])
                test_path = workspace / args['path']
                test_path.write_text(args['content'], encoding='utf-8')
                test_file = args['path']
                break

        # Fallback: extract from text
        if not test_file:
            text_response = self.extract_text_response(response)
            test_file = self._extract_test_from_text(text_response, workspace)

        return {
            'success': test_file is not None,
            'test_file': test_file
        }

    def _extract_function_signatures(self, code_files: Dict[str, str]) -> str:
        """Extract function signatures from code.

        Args:
            code_files: Dictionary of code files

        Returns:
            String with function signatures
        """
        signatures = []

        for filename, content in code_files.items():
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def ') or stripped.startswith('async def '):
                    signatures.append(f"# From {filename}\n{stripped}")

        return "\n".join(signatures) if signatures else "No functions found"

    def _extract_test_from_text(self, text: str, workspace: Path) -> str:
        """Extract test code from text response.

        Args:
            text: LLM response text
            workspace: Workspace path

        Returns:
            Test filename
        """
        # Look for code blocks
        in_code = False
        code_lines = []

        for line in text.split('\n'):
            if line.strip().startswith('```'):
                if in_code:
                    # End of code block
                    break
                in_code = True
            elif in_code:
                code_lines.append(line)

        if code_lines:
            test_content = '\n'.join(code_lines)
            test_file = 'test_generated.py'
            (workspace / test_file).write_text(test_content, encoding='utf-8')
            return test_file

        return None

    def _execute_tests(self, workspace: Path, test_file: str) -> Dict[str, Any]:
        """Execute pytest tests.

        Args:
            workspace: Workspace path
            test_file: Test file name

        Returns:
            Test results dictionary
        """
        try:
            # Run pytest with JSON output
            result = subprocess.run(
                ['pytest', test_file, '-v', '--tb=short', '--json-report', '--json-report-file=results.json'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Try to load JSON results
            results_file = workspace / 'results.json'
            if results_file.exists():
                with open(results_file) as f:
                    results = json.load(f)

                return {
                    'passed': result.returncode == 0,
                    'test_file': test_file,
                    'total': results.get('summary', {}).get('total', 0),
                    'passed_count': results.get('summary', {}).get('passed', 0),
                    'failed_count': results.get('summary', {}).get('failed', 0),
                    'error_message': result.stderr if result.returncode != 0 else None,
                    'test_results': results
                }

            # Fallback: parse stdout/stderr
            return self._parse_pytest_output(result, test_file)

        except subprocess.TimeoutExpired:
            self.logger.error("test_execution_timeout", test_file=test_file)
            return {
                'passed': False,
                'test_file': test_file,
                'error_message': 'Test execution timed out after 5 minutes',
                'test_results': {}
            }

        except Exception as e:
            self.logger.error("test_execution_failed", error=str(e))
            return {
                'passed': False,
                'test_file': test_file,
                'error_message': str(e),
                'stack_trace': result.stderr if 'result' in locals() else None,
                'test_results': {}
            }

    def _parse_pytest_output(
        self,
        result: subprocess.CompletedProcess,
        test_file: str
    ) -> Dict[str, Any]:
        """Parse pytest output when JSON report is unavailable.

        Args:
            result: Subprocess result
            test_file: Test file name

        Returns:
            Parsed test results
        """
        output = result.stdout + result.stderr

        return {
            'passed': result.returncode == 0,
            'test_file': test_file,
            'error_message': result.stderr if result.returncode != 0 else None,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'test_results': {'raw_output': output}
        }
