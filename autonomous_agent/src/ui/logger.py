"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


class AgentLogger:
    """Centralized logging for the autonomous agent."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger (only once)."""
        if not self._initialized:
            self._initialized = True
            self.logger: Optional[structlog.stdlib.BoundLogger] = None

    def setup(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        file_path: str = "logs/agent.log",
        console_output: bool = True,
        file_output: bool = True,
    ):
        """Configure structured logging.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_format: Format type ("json" or "text")
            file_path: Path to log file
            console_output: Whether to output to console
            file_output: Whether to output to file
        """

        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        if log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        level = getattr(logging, log_level.upper(), logging.INFO)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        formatter = logging.Formatter("%(message)s")

        if console_output:
            console_handler = logging.StreamHandler(stream=sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        if file_output and file_path:
            log_file = Path(file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        self.logger = structlog.get_logger()

    def get_logger(self, name: str = None) -> structlog.stdlib.BoundLogger:
        """Get a bound logger instance.

        Args:
            name: Optional logger name (e.g., 'orchestrator', 'coder')

        Returns:
            Bound logger instance
        """
        if self.logger is None:
            self.setup()

        if name:
            return self.logger.bind(component=name)
        return self.logger

    def log_iteration_start(
        self,
        task_id: str,
        iteration: int,
        phase: str,
        **kwargs,
    ):
        """Log the start of an iteration."""
        self.get_logger().info(
            "iteration_start",
            task_id=task_id,
            iteration=iteration,
            phase=phase,
            **kwargs,
        )

    def log_iteration_complete(
        self,
        task_id: str,
        iteration: int,
        phase: str,
        duration: float,
        success: bool,
        **kwargs,
    ):
        """Log the completion of an iteration."""
        self.get_logger().info(
            "iteration_complete",
            task_id=task_id,
            iteration=iteration,
            phase=phase,
            duration=duration,
            success=success,
            **kwargs,
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        task_id: str = None,
        iteration: int = None,
        **kwargs,
    ):
        """Log an error with context."""
        self.get_logger().error(
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            task_id=task_id,
            iteration=iteration,
            **kwargs,
        )

    def log_metric(
        self,
        metric_type: str,
        value: float,
        task_id: str = None,
        **kwargs,
    ):
        """Log a metric."""
        self.get_logger().info(
            "metric",
            metric_type=metric_type,
            value=value,
            task_id=task_id,
            **kwargs,
        )

    def log_approval_request(
        self,
        approval_type: str,
        details: Dict[str, Any],
        task_id: str = None,
        **kwargs,
    ):
        """Log an approval request."""
        self.get_logger().info(
            "approval_request",
            approval_type=approval_type,
            details=details,
            task_id=task_id,
            **kwargs,
        )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""

    return AgentLogger().get_logger(name)


def setup_logging(config: Dict[str, Any]):
    """Setup logging from configuration."""

    outputs = config.get("outputs", ["console"])

    logger = AgentLogger()
    logger.setup(
        log_level=config.get("level", "INFO"),
        log_format=config.get("format", "json"),
        file_path=config.get("file_path", "logs/agent.log"),
        console_output="console" in outputs,
        file_output="file" in outputs,
    )
