"""Prompt helpers.

Prompts are primarily loaded from YAML (see config/system_prompts.yaml). This
module provides a lightweight string rendering helper and a safe formatting
function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Prompt:
    system: str
    user_template: str

    def render_user(self, **kwargs: Any) -> str:
        return safe_format(self.user_template, **kwargs)


def safe_format(template: str, **kwargs: Any) -> str:
    """Format a template while avoiding KeyError crashes.

    Missing keys are rendered as an empty string.
    """

    class _SafeDict(dict):
        def __missing__(self, key):  # type: ignore[override]
            return ""

    return template.format_map(_SafeDict(**kwargs))
