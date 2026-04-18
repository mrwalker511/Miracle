"""Tests for the shared approval manager."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.utils.approval_manager import ApprovalManager, ApprovalRequest


@pytest.mark.asyncio
async def test_request_persists_approval_decision():
    db = MagicMock()
    db.store_approval = AsyncMock(return_value=uuid.uuid4())
    prompt = MagicMock()
    prompt.request.return_value = True

    manager = ApprovalManager(db_manager=db, prompt=prompt)
    task_id = uuid.uuid4()
    iteration_id = uuid.uuid4()

    approved = await manager.request(
        ApprovalRequest(
            approval_type="protected_file_write",
            details={"path": ".env", "workspace": "/tmp/ws"},
            task_id=task_id,
            iteration_id=iteration_id,
        )
    )

    assert approved is True
    db.store_approval.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_without_db_still_prompts():
    prompt = MagicMock()
    prompt.request.return_value = False
    manager = ApprovalManager(prompt=prompt)

    approved = await manager.request(
        ApprovalRequest(
            approval_type="command_execution",
            details={"command": "python -m pytest"},
        )
    )

    assert approved is False
    prompt.request.assert_called_once()
