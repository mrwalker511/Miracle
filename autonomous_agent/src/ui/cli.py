"""UI convenience helpers.

The main CLI uses Click + Rich directly. This module provides reusable helpers
for printing common UI elements.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel


def print_banner(*, console: Optional[Console] = None, version: str = "0.1.0"):
    c = console or Console()
    c.print(
        Panel.fit(
            f"[bold cyan]AUTONOMOUS CODING AGENT v{version}[/bold cyan]\n"
            "[dim]Build code autonomously with AI[/dim]",
            border_style="cyan",
        )
    )


def print_kv(*, console: Optional[Console] = None, **items: Any):
    c = console or Console()
    for k, v in items.items():
        c.print(f"[bold]{k}:[/bold] {v}")


def print_result_summary(
    *,
    console: Optional[Console] = None,
    success: bool,
    details: Dict[str, Any],
):
    c = console or Console()
    if success:
        c.print(Panel.fit(str(details), border_style="green"))
    else:
        c.print(Panel.fit(str(details), border_style="red"))
