"""Shared approval flow for user-gated operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

from src.ui.approval_prompt import ApprovalPrompt
from src.ui.logger import get_logger


class ApprovalDenied(RuntimeError):
    """Raised when a user denies a required approval."""


@dataclass
class ApprovalRequest:
    """Structured approval request."""

    approval_type: str
    details: Dict[str, Any]
    task_id: Optional[UUID] = None
    iteration_id: Optional[UUID] = None
    default: bool = False
    reasoning: Optional[str] = None


class ApprovalManager:
    """Handle approval prompts and persistence."""

    def __init__(self, db_manager: Any | None = None, prompt: ApprovalPrompt | None = None):
        self.db = db_manager
        self.prompt = prompt or ApprovalPrompt()
        self.logger = get_logger("approval_manager")

    async def request(self, request: ApprovalRequest) -> bool:
        """Prompt the user and persist the resulting decision when possible."""
        self.logger.info(
            "approval_requested",
            approval_type=request.approval_type,
            details=request.details,
            task_id=str(request.task_id) if request.task_id else None,
            iteration_id=str(request.iteration_id) if request.iteration_id else None,
        )

        approved = self.prompt.request(
            approval_type=request.approval_type,
            details=request.details,
            default=request.default,
        )

        if self.db and request.task_id and request.iteration_id:
            await self.db.store_approval(
                task_id=request.task_id,
                iteration_id=request.iteration_id,
                approval_type=request.approval_type,
                request_details=request.details,
                approved=approved,
                reasoning=request.reasoning,
            )

        self.logger.info(
            "approval_resolved",
            approval_type=request.approval_type,
            approved=approved,
            task_id=str(request.task_id) if request.task_id else None,
            iteration_id=str(request.iteration_id) if request.iteration_id else None,
        )
        return approved

