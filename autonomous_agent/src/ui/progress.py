"""Rich progress helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


@contextmanager
def progress_task(description: str, *, console: Optional[Console] = None) -> Iterator[Progress]:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console or Console(),
        transient=True,
    )
    with progress:
        progress.add_task(description, total=None)
        yield progress
