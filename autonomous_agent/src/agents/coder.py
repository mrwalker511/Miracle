"""Coder agent for code generation with tool use."""

import json
from typing import Any, Dict, List
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.llm.tools import get_coding_tools
from src.projects.scaffolder import ProjectScaffolder


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
        self.scaffolder = ProjectScaffolder()

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

        language = context.get('language', 'python')
        problem_type = context.get('problem_type', 'general')

        # Create task workspace
        task_workspace = self.workspace_path / task_id
        task_workspace.mkdir(parents=True, exist_ok=True)

        self.scaffolder.ensure_scaffold(
            workspace=task_workspace,
            language=language,
            project_type=problem_type,
        )

        # Build user message
        user_message = self.format_user_message(
            plan=plan,
            iteration=iteration,
            previous_errors=previous_errors or "None"
        )

        # Add language-specific context to the user message
        language_context = self._get_language_context(language)
        if language_context:
            user_message = language_context + "\n" + user_message

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
        tool_name = tool_call.get('name')

        arguments_raw = tool_call.get('arguments', {})
        if isinstance(arguments_raw, str):
            try:
                arguments = json.loads(arguments_raw) if arguments_raw else {}
            except json.JSONDecodeError:
                arguments = {}
        elif isinstance(arguments_raw, dict):
            arguments = arguments_raw
        else:
            arguments = {}

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

    def _resolve_in_workspace(self, workspace: Path, path: str) -> Path:
        """Resolve a user-provided path within the workspace."""
        if not path:
            raise ValueError('Path is required')

        workspace_root = workspace.resolve()
        candidate = (workspace_root / path).resolve()

        if candidate == workspace_root or workspace_root in candidate.parents:
            return candidate

        raise ValueError(f'Path escapes workspace: {path}')

    def _create_file(self, workspace: Path, path: str, content: str) -> Dict[str, Any]:
        """Create a file in the workspace.

        Args:
            workspace: Workspace path
            path: File path (relative to workspace)
            content: File content

        Returns:
            Result dictionary
        """
        if not path:
            return {'error': 'Path is required'}
        if content is None:
            return {'error': 'Content is required'}

        try:
            file_path = self._resolve_in_workspace(workspace, path)
        except ValueError as e:
            self.logger.error("file_creation_failed", path=path, error=str(e))
            return {'error': str(e)}

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
        if not path:
            return {'error': 'Path is required'}

        try:
            file_path = self._resolve_in_workspace(workspace, path)
        except ValueError as e:
            self.logger.error("file_read_failed", path=path, error=str(e))
            return {'error': str(e)}

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

    def _get_language_context(self, language: str) -> str:
        """Get language-specific context for code generation."""
        language = str(language).lower()
        
        contexts = {
            "node": "Runtime: Node.js (JavaScript).\nPrefer built-in Node APIs (no external dependencies unless required).",
            "javascript": "Runtime: Node.js (JavaScript).\nPrefer built-in Node APIs (no external dependencies unless required).",
            "js": "Runtime: Node.js (JavaScript).\nPrefer built-in Node APIs (no external dependencies unless required).",
            "typescript": "Runtime: Node.js (TypeScript).\nUse modern TypeScript features. Prefer built-in Node APIs.\nInclude type annotations for public functions.",
            "ts": "Runtime: Node.js (TypeScript).\nUse modern TypeScript features. Prefer built-in Node APIs.\nInclude type annotations for public functions.",
            "java": "Runtime: Java (JVM).\nUse modern Java features (var, records, sealed classes).\nFollow standard Java naming conventions.\nInclude Javadoc for public methods.",
            "csharp": "Runtime: C# (.NET).\nUse modern C# features (records, pattern matching, nullable reference types).\nFollow .NET naming conventions.\nInclude XML documentation for public members.",
            "c#": "Runtime: C# (.NET).\nUse modern C# features (records, pattern matching, nullable reference types).\nFollow .NET naming conventions.\nInclude XML documentation for public members.",
            "go": "Runtime: Go.\nUse idiomatic Go patterns.\nFollow Go naming conventions (camelCase for variables, PascalCase for exported).\nInclude godoc comments for exported functions.",
            "golang": "Runtime: Go.\nUse idiomatic Go patterns.\nFollow Go naming conventions (camelCase for variables, PascalCase for exported).\nInclude godoc comments for exported functions.",
            "rust": "Runtime: Rust.\nUse idiomatic Rust patterns (Result, Option, iterators).\nFollow Rust naming conventions (snake_case).\nInclude rustdoc comments for public items.",
            "ruby": "Runtime: Ruby.\nUse idiomatic Ruby patterns.\nFollow Ruby naming conventions (snake_case for methods, PascalCase for classes).\nInclude RDoc comments for public methods.",
            "php": "Runtime: PHP.\nUse modern PHP features (typed properties, named arguments).\nFollow PSR-12 coding style.\nInclude PHPDoc for public methods.",
            "swift": "Runtime: Swift.\nUse idiomatic Swift patterns.\nFollow Swift API Design Guidelines.\nInclude documentation comments for public declarations.",
            "kotlin": "Runtime: Kotlin (JVM).\nUse idiomatic Kotlin patterns.\nFollow Kotlin coding conventions.\nInclude KDoc for public declarations.",
            "elixir": "Runtime: Elixir (BEAM).\nUse idiomatic Elixir patterns (pipes, pattern matching).\nFollow Elixir naming conventions (snake_case).\nInclude @doc and @moduledoc annotations.",
            "python": "Runtime: Python.\nUse modern Python features (type hints, f-strings, walrus operator).\nFollow PEP 8 style guide.\nInclude docstrings for public functions."
        }
        
        return contexts.get(language, "")

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

        allowed_suffixes = (
            '.py', '.js', '.mjs', '.cjs', '.ts', '.json', '.md',
            '.yml', '.yaml', '.txt', '.toml', '.java', '.cs', '.go',
            '.rs', '.rb', '.php', '.swift', '.kt', '.ex', '.exs', '.gradle',
            '.gradle.kts', '.xml', '.properties', '.mod', '.sum', '.toml'
        )

        for line in lines:
            stripped = line.strip()

            # Detect code block start/end
            if stripped.startswith('```'):
                if in_code_block and current_code:
                    content = '\n'.join(current_code)
                    if current_file:
                        code_files[current_file] = content
                        self._create_file(workspace, current_file, content)
                    current_code = []
                    current_file = None

                in_code_block = not in_code_block
                continue

            if in_code_block:
                current_code.append(line)
                continue

            # Detect filename lines outside code blocks (e.g., "# app.py" or "File: app.py")
            if stripped.startswith('#') or 'file:' in stripped.lower():
                potential_filename = stripped.lstrip('#').strip()
                if potential_filename.endswith(allowed_suffixes) or '/' in potential_filename:
                    current_file = potential_filename.split(':')[-1].strip()

        if in_code_block and current_code and current_file:
            content = '\n'.join(current_code)
            code_files[current_file] = content
            self._create_file(workspace, current_file, content)

        return code_files
