"""Tests for project scaffolder."""

import json
import tempfile
from pathlib import Path

import pytest

from src.projects.scaffolder import ProjectScaffolder, SCAFFOLD_MARKER


class TestProjectScaffolder:
    """Test cases for ProjectScaffolder."""

    def test_initialization(self):
        """Test ProjectScaffolder initialization."""
        scaffolder = ProjectScaffolder()
        assert scaffolder is not None

    def test_scaffold_python(self):
        """Test scaffolding a Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            result = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )

            assert result["scaffolded"] is True
            assert result["language"] == "python"
            assert result["project_type"] == "general"

            # Check files exist
            assert (workspace / "README.md").exists()
            assert (workspace / SCAFFOLD_MARKER).exists()

    def test_scaffold_node(self):
        """Test scaffolding a Node.js project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            result = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="node",
                project_type="general"
            )

            assert result["scaffolded"] is True
            assert result["language"] == "node"
            assert result["project_type"] == "general"

            # Check files exist
            assert (workspace / "README.md").exists()
            assert (workspace / "package.json").exists()
            assert (workspace / "src").exists()
            assert (workspace / "test").exists()

            # Check package.json content
            package_json = json.loads(
                (workspace / "package.json").read_text(encoding="utf-8")
            )
            assert package_json["name"] == "agent-workspace"
            assert "scripts" in package_json
            assert "test" in package_json["scripts"]

    def test_scaffold_javascript(self):
        """Test scaffolding with 'javascript' language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            result = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="javascript",
                project_type="general"
            )

            assert result["scaffolded"] is True
            assert result["language"] == "node"  # Should normalize to "node"

    def test_scaffold_already_scaffolded(self):
        """Test that workspace isn't re-scaffolded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            # First scaffold
            result1 = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )
            assert result1["scaffolded"] is True

            # Second attempt
            result2 = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )
            assert result2["scaffolded"] is False
            assert result2["reason"] == "already_scaffolded"

    def test_scaffold_non_empty_workspace(self):
        """Test that non-empty workspace isn't scaffolded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # Create a file first
            (workspace / "existing.py").write_text("# existing file", encoding="utf-8")

            scaffolder = ProjectScaffolder()

            result = scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )

            assert result["scaffolded"] is False
            assert result["reason"] == "workspace_not_empty"

    def test_python_readme_content(self):
        """Test Python README content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )

            readme = (workspace / "README.md").read_text(encoding="utf-8")
            assert "Python" in readme
            assert "autonomous coding agent" in readme.lower()

    def test_node_readme_content(self):
        """Test Node.js README content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            scaffolder.ensure_scaffold(
                workspace=workspace,
                language="node",
                project_type="general"
            )

            readme = (workspace / "README.md").read_text(encoding="utf-8")
            assert "Node.js" in readme
            assert "autonomous coding agent" in readme.lower()

    def test_node_project_structure(self):
        """Test Node.js project structure is correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            scaffolder.ensure_scaffold(
                workspace=workspace,
                language="node",
                project_type="general"
            )

            # Check src directory
            assert (workspace / "src").exists()
            index_js = workspace / "src" / "index.js"
            assert index_js.exists()
            content = index_js.read_text(encoding="utf-8")
            assert "module.exports" in content

            # Check test directory
            assert (workspace / "test").exists()
            smoke_test = workspace / "test" / "smoke.test.js"
            assert smoke_test.exists()
            content = smoke_test.read_text(encoding="utf-8")
            assert "node:test" in content
            assert "node:assert" in content

    def test_marker_file_content(self):
        """Test marker file has correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="cli_tool"
            )

            marker = json.loads(
                (workspace / SCAFFOLD_MARKER).read_text(encoding="utf-8")
            )

            assert marker["language"] == "python"
            assert marker["project_type"] == "cli_tool"

    def test_creates_workspace_directory(self):
        """Test that workspace directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "new_workspace"
            assert not workspace.exists()

            scaffolder = ProjectScaffolder()
            scaffolder.ensure_scaffold(
                workspace=workspace,
                language="python",
                project_type="general"
            )

            assert workspace.exists()

    def test_case_insensitive_language(self):
        """Test language parameter is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            scaffolder = ProjectScaffolder()

            for lang in ["python", "Python", "PYTHON"]:
                ws = Path(tmpdir) / f"workspace_{lang}"
                result = scaffolder.ensure_scaffold(
                    workspace=ws,
                    language=lang,
                    project_type="general"
                )
                assert result["scaffolded"] is True
                assert (ws / "README.md").exists()

    def test_abbreviations(self):
        """Test language abbreviations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scaffolder = ProjectScaffolder()

            # Test 'js' abbreviation
            ws1 = Path(tmpdir) / "workspace_js"
            result1 = scaffolder.ensure_scaffold(
                workspace=ws1,
                language="js",
                project_type="general"
            )
            assert result1["language"] == "node"
            assert (ws1 / "package.json").exists()
