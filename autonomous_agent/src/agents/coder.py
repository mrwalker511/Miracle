"""Coder agent for code generation with tool use."""

import json
from typing import Any, Dict, List
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.llm.tools import get_coding_tools


class CoderAgent(BaseAgent):
    """Agent responsible for generating code."""

    def __init__(self, *args, workspace_path: str = "./sandbox/workspace", **kwargs):
        """Initialize coder agent.

        Args:
            workspace_path: Path to sandbox workspace
            *args, **kwargs: Arguments for BaseAgent
        """
        super().__init__(*args, **kwargs)
        self.workspace_path = Path(workspace_path)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on plan.

        Args:
            context: Dictionary containing:
                - plan: Implementation plan
                - iteration: Current iteration
                - previous_errors: Errors from previous attempts
                - task_id: Task UUID

        Returns:
            Dictionary with:
                - code_files: Dictionary of filename -> content
                - tool_calls: List of tool calls made
                - success: Whether code generation succeeded
        """
        plan = context.get('plan', '')
        iteration = context.get('iteration', 1)
        previous_errors = context.get('previous_errors', '')
        task_id = str(context.get('task_id', ''))

        self.logger.info("coding_started", iteration=iteration)

        # Create task workspace
        task_workspace = self.workspace_path / task_id
        task_workspace.mkdir(parents=True, exist_ok=True)

        # Build user message
        user_message = self.format_user_message(
            plan=plan,
            iteration=iteration,
            previous_errors=previous_errors or "None"
        )

        # Get coding tools
        tools = get_coding_tools()

        # Call LLM with tools
        messages = self.build_messages(user_message)
        response = self.call_llm(messages, tools=tools)

        # Extract tool calls and execute them
        tool_calls = self.extract_tool_calls(response)
        code_files = {}

        for tool_call in tool_calls:
            result = self._execute_tool(tool_call, task_workspace)
            if result.get('file_created'):
                code_files[result['filename']] = result['content']

        # If no tool calls, extract code from response text
        if not code_files:
            text_response = self.extract_text_response(response)
            code_files = self._extract_code_from_text(text_response, task_workspace)

        self.logger.info(
            "coding_completed",
            file_count=len(code_files),
            iteration=iteration
        )

        return {
            'code_files': code_files,
            'tool_calls': tool_calls,
            'success': len(code_files) > 0,
            'workspace': str(task_workspace)
        }

    def _execute_tool(
        self,
        tool_call: Dict[str, Any],
        workspace: Path
    ) -> Dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_call: Tool call dictionary
            workspace: Workspace path

        Returns:
            Execution result
        """
        tool_name = tool_call['name']
        arguments = json.loads(tool_call['arguments'])

        self.logger.debug("executing_tool", tool=tool_name, args=arguments)

        if tool_name == 'create_file':
            return self._create_file(
                workspace,
                arguments.get('path'),
                arguments.get('content')
            )
        elif tool_name == 'read_file':
            return self._read_file(workspace, arguments.get('path'))
        elif tool_name == 'list_files':
            return self._list_files(workspace)

        return {'error': f'Unknown tool: {tool_name}'}

    def _create_file(self, workspace: Path, path: str, content: str) -> Dict[str, Any]:
        """Create a file in the workspace.

        Args:
            workspace: Workspace path
            path: File path (relative to workspace)
            content: File content

        Returns:
            Result dictionary
        """
        file_path = workspace / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_text(content, encoding='utf-8')
            self.logger.info("file_created", path=str(file_path))

            return {
                'file_created': True,
                'filename': path,
                'content': content,
                'path': str(file_path)
            }
        except Exception as e:
            self.logger.error("file_creation_failed", path=path, error=str(e))
            return {'error': str(e)}

    def _read_file(self, workspace: Path, path: str) -> Dict[str, Any]:
        """Read a file from the workspace.

        Args:
            workspace: Workspace path
            path: File path

        Returns:
            File content
        """
        file_path = workspace / path

        try:
            content = file_path.read_text(encoding='utf-8')
            return {'content': content, 'filename': path}
        except Exception as e:
            self.logger.error("file_read_failed", path=path, error=str(e))
            return {'error': str(e)}

    def _list_files(self, workspace: Path) -> Dict[str, Any]:
        """List files in the workspace.

        Args:
            workspace: Workspace path

        Returns:
            List of files
        """
        try:
            files = [str(f.relative_to(workspace)) for f in workspace.rglob('*') if f.is_file()]
            return {'files': files}
        except Exception as e:
            self.logger.error("file_listing_failed", error=str(e))
            return {'error': str(e)}

    def _extract_code_from_text(
        self,
        text: str,
        workspace: Path
    ) -> Dict[str, str]:
        """Extract code blocks from markdown-formatted text.

        Args:
            text: Response text
            workspace: Workspace path

        Returns:
            Dictionary of filename -> content
        """
        code_files = {}
        lines = text.split('\n')

        current_file = None
        current_code = []
        in_code_block = False

        for line in lines:
            # Detect filename (e.g., "# app.py" or "File: app.py")
            if line.strip().startswith('#') or 'file:' in line.lower():
                potential_filename = line.strip().lstrip('#').strip()
                if potential_filename.endswith('.py') or '/' in potential_filename:
                    current_file = potential_filename.split(':')[-1].strip()

            # Detect code block start/end
            if line.strip().startswith('```'):
                if in_code_block and current_code:
                    # End of code block
                    content = '\n'.join(current_code)
                    if current_file:
                        code_files[current_file] = content
                        self._create_file(workspace, current_file, content)
                    current_code = []
                    current_file = None
                in_code_block = not in_code_block
            elif in_code_block:
                current_code.append(line)

        return code_files
