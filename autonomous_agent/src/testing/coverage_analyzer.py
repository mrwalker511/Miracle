"""Coverage analysis helpers.

Coverage collection is not yet integrated into the main loop, but this module
contains parsers that can be wired in later.
"""

from __future__ import annotations

import re
from typing import Any, Dict


def parse_pytest_cov_output(output: str) -> Dict[str, Any]:
    """Parse the total coverage percentage from pytest-cov output."""

    # Common line: "TOTAL 12 0 100%"
    m = re.search(r"^TOTAL\s+\d+\s+\d+\s+(?P<pct>\d+)%\s*$", output, flags=re.MULTILINE)
    if not m:
        return {}

    return {"total_coverage_percent": int(m.group("pct"))}
