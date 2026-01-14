"""State persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.ui.logger import get_logger


class StateSaver:
    def __init__(self, *, filename: str = "checkpoint.json"):
        self.filename = filename
        self.logger = get_logger("state_saver")

    def save(self, *, workspace: Path, state: str, iteration: int, context: Dict[str, Any]):
        workspace.mkdir(parents=True, exist_ok=True)
        path = workspace / self.filename

        payload = {
            "state": state,
            "iteration": iteration,
            "context": context,
        }

        path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
        self.logger.info("checkpoint_written", path=str(path), iteration=iteration, state=state)

    def load(self, *, workspace: Path) -> Optional[Dict[str, Any]]:
        path = workspace / self.filename
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            self.logger.warning("checkpoint_load_failed", error=str(e), path=str(path))
            return None
