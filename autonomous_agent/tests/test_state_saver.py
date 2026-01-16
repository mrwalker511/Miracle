"""Tests for state saver utility."""

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.state_saver import StateSaver


class TestStateSaver:
    """Test cases for StateSaver."""

    def test_initialization_defaults(self):
        """Test StateSaver initialization with defaults."""
        saver = StateSaver()
        assert saver.filename == "checkpoint.json"

    def test_initialization_custom(self):
        """Test StateSaver with custom filename."""
        saver = StateSaver(filename="custom.json")
        assert saver.filename == "custom.json"

    def test_save_creates_file(self):
        """Test save creates checkpoint file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            saver.save(
                workspace=workspace,
                state="testing",
                iteration=5,
                context={"key": "value"}
            )

            checkpoint_file = workspace / "checkpoint.json"
            assert checkpoint_file.exists()

    def test_save_content(self):
        """Test save writes correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            test_context = {
                "task_id": "test-123",
                "iteration": 3,
                "data": "test data"
            }

            saver.save(
                workspace=workspace,
                state="coding",
                iteration=3,
                context=test_context
            )

            checkpoint_file = workspace / "checkpoint.json"
            content = json.loads(checkpoint_file.read_text(encoding="utf-8"))

            assert content["state"] == "coding"
            assert content["iteration"] == 3
            assert content["context"] == test_context

    def test_load_existing(self):
        """Test loading existing checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            test_data = {
                "state": "planning",
                "iteration": 7,
                "context": {"test": "data"}
            }

            # Save checkpoint
            checkpoint_file = workspace / "checkpoint.json"
            checkpoint_file.write_text(json.dumps(test_data), encoding="utf-8")

            # Load checkpoint
            loaded = saver.load(workspace=workspace)

            assert loaded is not None
            assert loaded["state"] == "planning"
            assert loaded["iteration"] == 7
            assert loaded["context"]["test"] == "data"

    def test_load_nonexistent(self):
        """Test loading when checkpoint doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            loaded = saver.load(workspace=workspace)

            assert loaded is None

    def test_save_creates_directory(self):
        """Test save creates workspace directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "new_workspace"
            assert not workspace.exists()

            saver = StateSaver()
            saver.save(
                workspace=workspace,
                state="init",
                iteration=0,
                context={}
            )

            assert workspace.exists()
            assert (workspace / "checkpoint.json").exists()

    def test_overwrite_existing(self):
        """Test overwriting existing checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            # Save first checkpoint
            saver.save(
                workspace=workspace,
                state="first",
                iteration=1,
                context={"version": 1}
            )

            # Overwrite with new checkpoint
            saver.save(
                workspace=workspace,
                state="second",
                iteration=2,
                context={"version": 2}
            )

            loaded = saver.load(workspace=workspace)
            assert loaded["state"] == "second"
            assert loaded["iteration"] == 2
            assert loaded["context"]["version"] == 2

    def test_save_with_complex_context(self):
        """Test save with complex nested context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver()

            complex_context = {
                "nested": {
                    "deeply": {
                        "value": 42
                    }
                },
                "list": [1, 2, 3],
                "bool": True,
                "null": None
            }

            saver.save(
                workspace=workspace,
                state="complex",
                iteration=10,
                context=complex_context
            )

            loaded = saver.load(workspace=workspace)
            assert loaded["context"] == complex_context

    def test_custom_filename(self):
        """Test save/load with custom filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            saver = StateSaver(filename="custom_checkpoint.json")

            saver.save(
                workspace=workspace,
                state="custom",
                iteration=1,
                context={}
            )

            assert (workspace / "custom_checkpoint.json").exists()
            assert not (workspace / "checkpoint.json").exists()

            loaded = saver.load(workspace=workspace)
            assert loaded is not None
            assert loaded["state"] == "custom"
