"""Interactive approval prompts."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import Console
from rich.prompt import Confirm

from src.ui.logger import get_logger


class ApprovalPrompt:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = get_logger("approval_prompt")

    def request(self, *, approval_type: str, details: Dict[str, Any], default: bool = False) -> bool:
        self.logger.info("approval_requested", approval_type=approval_type, details=details)
        message = f"Approve {approval_type}?\n\nDetails: {details}"
        approved = Confirm.ask(message, default=default, console=self.console)
        self.logger.info("approval_decision", approval_type=approval_type, approved=approved)
        return approved
