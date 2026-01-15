"""Metrics collection helpers."""

from __future__ import annotations

from uuid import UUID

from src.llm.openai_client import OpenAIClient
from src.memory.db_manager import DatabaseManager
from src.ui.logger import get_logger


class MetricsCollector:
    def __init__(self, *, db: DatabaseManager, openai_client: OpenAIClient):
        self.db = db
        self.openai = openai_client
        self.logger = get_logger("metrics_collector")
        self._token_baseline = openai_client.get_total_tokens_used()

    def start_iteration(self):
        self._token_baseline = self.openai.get_total_tokens_used()

    def record_iteration_tokens(self, *, task_id: UUID, iteration: int):
        tokens_now = self.openai.get_total_tokens_used()
        tokens_used = max(tokens_now - self._token_baseline, 0)

        self.db.store_metric(
            task_id,
            "token_usage",
            float(tokens_used),
            metadata={"iteration": iteration},
        )

        self.logger.info("iteration_token_usage_recorded", iteration=iteration, tokens_used=tokens_used)

    def record_test_pass_rate(self, *, task_id: UUID, passed: bool, iteration: int):
        self.db.store_metric(
            task_id,
            "test_pass_rate",
            1.0 if passed else 0.0,
            metadata={"iteration": iteration},
        )
