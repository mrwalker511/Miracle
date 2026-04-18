"""Tests for coder approval and protected file writes."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.coder import CoderAgent
from src.utils.approval_manager import ApprovalDenied


def make_coder(tmp_path: Path, approval_result: bool = True) -> CoderAgent:
    approval_manager = MagicMock()
    approval_manager.request = AsyncMock(return_value=approval_result)
    return CoderAgent(
        "coder",
        MagicMock(),
        MagicMock(),
        {},
        workspace_path=str(tmp_path),
        config={"settings": {"execution_hooks": {"enabled": True}}},
        approval_manager=approval_manager,
    )


@pytest.mark.asyncio
async def test_protected_file_write_requests_approval(tmp_path: Path):
    coder = make_coder(tmp_path, approval_result=True)

    result = await coder._create_file(
        tmp_path,
        ".env",
        "SECRET=value",
        task_id=None,
        iteration_id=None,
        iteration=1,
    )

    assert result["file_created"] is True
    assert (tmp_path / ".env").exists()
    coder.approval_manager.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_protected_file_write_denial_pauses(tmp_path: Path):
    coder = make_coder(tmp_path, approval_result=False)

    with pytest.raises(ApprovalDenied):
        await coder._create_file(
            tmp_path,
            ".env",
            "SECRET=value",
            task_id=None,
            iteration_id=None,
            iteration=1,
        )

    assert not (tmp_path / ".env").exists()


@pytest.mark.asyncio
async def test_post_write_hooks_format_python_file(tmp_path: Path):
    coder = make_coder(tmp_path, approval_result=True)

    result = await coder._create_file(
        tmp_path,
        "main.py",
        "print('hello')",
        task_id=None,
        iteration_id=None,
        iteration=1,
    )

    assert result["content"].endswith("\n")
    assert (tmp_path / "main.py").read_text(encoding="utf-8").endswith("\n")
