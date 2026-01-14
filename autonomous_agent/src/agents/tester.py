"""Tester agent for test generation and execution."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent
from src.llm.tools import get_testing_tools
from src.sandbox.sandbox_manager import SandboxManager


class TesterAgent(BaseAgent):
    """Agent responsible for generating and executing tests."""

    def __init__(
        self,
        *args,
        workspace_path: str = "./sandbox/workspace",
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.workspace_path = Path(workspace_path)
        self.sandbox = SandboxManager(config or {})

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        code_files = context.get("code_files", {})
        task_id = str(context.get("task_id", ""))
        workspace = Path(context.get("workspace", self.workspace_path / task_id))
        language = str(context.get("language", "python")).lower()

        self.logger.info("testing_started", workspace=str(workspace), language=language)

        test_generation_result = self._generate_tests(code_files, workspace, language)
        if not test_generation_result.get("success"):
            return {
                "passed": False,
                "error_message": "Test generation failed",
                "test_results": {},
            }

        test_file = test_generation_result["test_file"]
        test_results = self._execute_tests(workspace, test_file, language)

        self.logger.info(
            "testing_completed",
            passed=test_results.get("passed", False),
            test_count=test_results.get("total", 0),
        )

        return test_results

    def _generate_tests(
        self,
        code_files: Dict[str, str],
        workspace: Path,
        language: str,
    ) -> Dict[str, Any]:
        signatures = self._extract_function_signatures(code_files)

        code_context = "\n\n".join([f"# {filename}\n{content}" for filename, content in code_files.items()])

        user_message = self.format_user_message(
            code=code_context,
            signatures=signatures,
        )

        if language in {"node", "javascript", "js"}:
            user_message = (
                "Runtime: Node.js (JavaScript).\n"
                "Testing: Use the built-in node:test runner (no jest/mocha).\n"
                "Prefer creating a single test file at 'test/generated.test.js'.\n\n"
                + user_message
            )

        messages = self.build_messages(user_message)
        tools = get_testing_tools()
        response = self.call_llm(messages, tools=tools)

        tool_calls = self.extract_tool_calls(response)
        test_file: Optional[str] = None

        for tool_call in tool_calls:
            if tool_call["name"] != "create_test_file":
                continue
            args = json.loads(tool_call["arguments"])

            requested_path = str(args["path"])
            content = str(args["content"])

            if language in {"node", "javascript", "js"} and not requested_path.endswith((".js", ".mjs", ".cjs")):
                requested_path = "test/generated.test.js"

            test_path = workspace / requested_path
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(content, encoding="utf-8")
            test_file = requested_path
            break

        if not test_file:
            text_response = self.extract_text_response(response)
            test_file = self._extract_test_from_text(text_response, workspace, language)

        return {
            "success": test_file is not None,
            "test_file": test_file,
        }

    def _extract_function_signatures(self, code_files: Dict[str, str]) -> str:
        signatures = []

        for filename, content in code_files.items():
            ext = Path(filename).suffix.lower()

            for line in content.splitlines():
                stripped = line.strip()

                if ext == ".py":
                    if stripped.startswith("def ") or stripped.startswith("async def "):
                        signatures.append(f"# From {filename}\n{stripped}")

                elif ext in {".js", ".mjs", ".cjs", ".ts"}:
                    m = re.match(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(", stripped)
                    if m:
                        signatures.append(f"// From {filename}\nfunction {m.group(1)}(...)")
                        continue

                    m = re.match(r"^(?:export\s+)?const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(", stripped)
                    if m:
                        signatures.append(f"// From {filename}\nconst {m.group(1)} = (...) =>")
                        continue

        return "\n".join(signatures) if signatures else "No functions found"

    def _extract_test_from_text(self, text: str, workspace: Path, language: str) -> Optional[str]:
        in_code = False
        code_lines = []

        for line in text.split("\n"):
            if line.strip().startswith("```"):
                if in_code:
                    break
                in_code = True
                continue

            if in_code:
                code_lines.append(line)

        if not code_lines:
            return None

        test_content = "\n".join(code_lines)

        if language in {"node", "javascript", "js"}:
            test_file = "test/generated.test.js"
        else:
            test_file = "test_generated.py"

        test_path = workspace / test_file
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_content, encoding="utf-8")
        return test_file

    def _execute_tests(self, workspace: Path, test_file: str, language: str) -> Dict[str, Any]:
        if language in {"node", "javascript", "js"}:
            return self.sandbox.run_node_tests(workspace=workspace, test_file=test_file)
        return self.sandbox.run_python_tests(workspace=workspace, test_file=test_file)
