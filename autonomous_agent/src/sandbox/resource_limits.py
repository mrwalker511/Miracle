"""Resource limits for sandboxed execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    cpu_count: float = 1.0
    memory_mb: int = 1024
    execution_timeout: int = 300
    disk_quota_mb: int = 500

    @classmethod
    def from_config(cls, sandbox_config: Dict[str, Any]) -> "ResourceLimits":
        limits = (sandbox_config or {}).get("resource_limits", {})
        return cls(
            cpu_count=float(limits.get("cpu_count", 1)),
            memory_mb=int(limits.get("memory_mb", 1024)),
            execution_timeout=int(limits.get("execution_timeout", 300)),
            disk_quota_mb=int(limits.get("disk_quota_mb", 500)),
        )
