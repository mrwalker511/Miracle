"""Higher-level pattern matching utilities.

`VectorStore` provides low-level embedding search over stored patterns. This
module offers a small abstraction for choosing which patterns to present to the
planner/coder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.memory.vector_store import VectorStore


@dataclass(slots=True)
class PatternMatch:
    pattern_id: str
    problem_type: str
    description: str
    similarity: float
    code_template: str
    test_template: Optional[str]
    dependencies: List[str]


class PatternMatcher:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def find_relevant_patterns(
        self,
        *,
        task_description: str,
        problem_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return patterns in the same shape as the DB records."""

        return self.vector_store.find_similar_patterns(
            task_description=task_description,
            problem_type=problem_type,
            limit=limit,
        )
