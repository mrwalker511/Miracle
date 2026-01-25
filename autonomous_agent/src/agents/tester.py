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

    def _resolve_in_workspace(self, workspace: Path, path: str) -> Path:
        if not path:
            raise ValueError("Path is required")

        workspace_root = workspace.resolve()
        candidate = (workspace_root / path).resolve()

        if candidate == workspace_root or workspace_root in candidate.parents:
            return candidate

        raise ValueError(f"Path escapes workspace: {path}")

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

        # Add language-specific testing context
        test_context = self._get_testing_context(language)
        if test_context:
            user_message = test_context + "\n\n" + user_message

        messages = self.build_messages(user_message)
        tools = get_testing_tools()
        response = self.call_llm(messages, tools=tools)

        tool_calls = self.extract_tool_calls(response)
        test_file: Optional[str] = None

        for tool_call in tool_calls:
            if tool_call.get("name") != "create_test_file":
                continue

            arguments_raw = tool_call.get("arguments", {})
            if isinstance(arguments_raw, str):
                try:
                    args = json.loads(arguments_raw) if arguments_raw else {}
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(arguments_raw, dict):
                args = arguments_raw
            else:
                args = {}

            requested_path = str(args.get("path") or "")
            content = args.get("content")
            if content is None:
                continue
            content = str(content)

            # Determine test file path based on language
            if language in {"node", "javascript", "js", "typescript", "ts"}:
                requested_path = "test/generated.test.js"
            elif language == "java":
                requested_path = "src/test/java/TestGenerated.java"
            elif language == "csharp":
                requested_path = "TestGenerated.cs"
            elif language == "go":
                requested_path = "generated_test.go"
            elif language == "rust":
                requested_path = "tests/generated_test.rs"
            elif language == "ruby":
                requested_path = "spec/generated_spec.rb"
            elif language == "php":
                requested_path = "tests/TestGenerated.php"
            elif language == "swift":
                requested_path = "Tests/GeneratedTests.swift"
            elif language == "kotlin":
                requested_path = "src/test/kotlin/TestGenerated.kt"
            elif language == "elixir":
                requested_path = "test/generated_test.exs"
            elif not requested_path:
                requested_path = "test_generated.py"

            try:
                test_path = self._resolve_in_workspace(workspace, requested_path)
            except ValueError:
                requested_path = "test/generated.test.js" if language in {"node", "javascript", "js"} else "test_generated.py"
                test_path = self._resolve_in_workspace(workspace, requested_path)

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

    def _get_testing_context(self, language: str) -> str:
        """Get language-specific testing context."""
        language = str(language).lower()
        
        contexts = {
            "node": "Runtime: Node.js (JavaScript).\nTesting: Use the built-in node:test runner (no jest/mocha).\nPrefer creating a single test file at 'test/generated.test.js'.",
            "javascript": "Runtime: Node.js (JavaScript).\nTesting: Use the built-in node:test runner (no jest/mocha).\nPrefer creating a single test file at 'test/generated.test.js'.",
            "js": "Runtime: Node.js (JavaScript).\nTesting: Use the built-in node:test runner (no jest/mocha).\nPrefer creating a single test file at 'test/generated.test.js'.",
            "typescript": "Runtime: Node.js (TypeScript).\nTesting: Use the built-in node:test runner.\nCreate test file at 'test/generated.test.js' that imports from compiled TypeScript.",
            "ts": "Runtime: Node.js (TypeScript).\nTesting: Use the built-in node:test runner.\nCreate test file at 'test/generated.test.js' that imports from compiled TypeScript.",
            "java": "Runtime: Java (JVM).\nTesting: Use JUnit 5.\nCreate test class in 'src/test/java' with @Test annotations.\nUse Assertions class for assertions.",
            "csharp": "Runtime: C# (.NET).\nTesting: Use xUnit or NUnit.\nCreate test class with [Fact] or [Test] attributes.\nFollow AAA pattern (Arrange, Act, Assert).",
            "c#": "Runtime: C# (.NET).\nTesting: Use xUnit or NUnit.\nCreate test class with [Fact] or [Test] attributes.\nFollow AAA pattern (Arrange, Act, Assert).",
            "go": "Runtime: Go.\nTesting: Use built-in testing package.\nCreate test file with '_test.go' suffix.\nUse t.Run() for sub-tests and testing.T for assertions.",
            "golang": "Runtime: Go.\nTesting: Use built-in testing package.\nCreate test file with '_test.go' suffix.\nUse t.Run() for sub-tests and testing.T for assertions.",
            "rust": "Runtime: Rust.\nTesting: Use built-in test framework.\nCreate test module with #[cfg(test)] and #[test] attributes.\nUse assert macros for assertions.",
            "ruby": "Runtime: Ruby.\nTesting: Use RSpec or Minitest.\nCreate spec file in 'spec/' directory.\nFollow BDD style with describe/it blocks.",
            "php": "Runtime: PHP.\nTesting: Use PHPUnit.\nCreate test class extending TestCase.\nUse $this->assert* methods for assertions.",
            "swift": "Runtime: Swift.\nTesting: Use XCTest.\nCreate test class extending XCTestCase.\nUse XCTAssert* functions for assertions.",
            "kotlin": "Runtime: Kotlin (JVM).\nTesting: Use JUnit 5 with Kotlin.\nCreate test class with @Test annotations.\nUse Assertions.assert* functions.",
            "elixir": "Runtime: Elixir (BEAM).\nTesting: Use ExUnit.\nCreate test module with use ExUnit.Case.\nUse assert macros for assertions.",
            "python": "Runtime: Python.\nTesting: Use pytest.\nCreate test file with 'test_' prefix.\nUse assert statements and pytest fixtures."
        }
        
        return contexts.get(language, "")

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

                elif ext == ".java":
                    # Java method signatures
                    if re.match(r"\s*(public|private|protected|static|final|synchronized|native|abstract|strictfp|transient|volatile)\s+.+\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".cs":
                    # C# method signatures
                    if re.match(r"\s*(public|private|protected|internal|static|async|virtual|override|abstract|sealed|partial)\s+.+\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".go":
                    # Go function signatures
                    if re.match(r"^func\s+\([^)]+\)\s+[A-Za-z0-9_]+\s*\(", stripped) or re.match(r"^func\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".rs":
                    # Rust function signatures
                    if re.match(r"^fn\s+[A-Za-z0-9_]+\s*\(", stripped) or re.match(r"^pub\s+fn\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".rb":
                    # Ruby method signatures
                    if re.match(r"^\s*def\s+[A-Za-z0-9_]+\s*[(", stripped):
                        signatures.append(f"# From {filename}\n{stripped}")

                elif ext == ".php":
                    # PHP function signatures
                    if re.match(r"^\s*(public|private|protected|static|final|abstract)\s+function\s+[A-Za-z0-9_]+\s*\(", stripped) or re.match(r"^function\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".swift":
                    # Swift function signatures
                    if re.match(r"^\s*(public|private|internal|fileprivate|open|static|class|func)\s+func\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".kt":
                    # Kotlin function signatures
                    if re.match(r"^\s*(public|private|protected|internal|open|override|abstract|final)\s+fun\s+[A-Za-z0-9_]+\s*\(", stripped):
                        signatures.append(f"// From {filename}\n{stripped}")

                elif ext == ".ex":
                    # Elixir function signatures
                    if re.match(r"^\s*def\s+[A-Za-z0-9_]+\s*[(", stripped):
                        signatures.append(f"# From {filename}\n{stripped}")

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

        # Determine test file path based on language
        if language in {"node", "javascript", "js", "typescript", "ts"}:
            test_file = "test/generated.test.js"
        elif language == "java":
            test_file = "src/test/java/TestGenerated.java"
        elif language == "csharp":
            test_file = "TestGenerated.cs"
        elif language == "go":
            test_file = "generated_test.go"
        elif language == "rust":
            test_file = "tests/generated_test.rs"
        elif language == "ruby":
            test_file = "spec/generated_spec.rb"
        elif language == "php":
            test_file = "tests/TestGenerated.php"
        elif language == "swift":
            test_file = "Tests/GeneratedTests.swift"
        elif language == "kotlin":
            test_file = "src/test/kotlin/TestGenerated.kt"
        elif language == "elixir":
            test_file = "test/generated_test.exs"
        else:
            test_file = "test_generated.py"

        test_path = self._resolve_in_workspace(workspace, test_file)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_content, encoding="utf-8")
        return test_file

    def _execute_tests(self, workspace: Path, test_file: str, language: str) -> Dict[str, Any]:
        if language in {"node", "javascript", "js"}:
            return self.sandbox.run_node_tests(workspace=workspace, test_file=test_file)
        return self.sandbox.run_python_tests(workspace=workspace, test_file=test_file)
