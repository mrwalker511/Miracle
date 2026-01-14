"""Structured logging configuration using structlog."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger


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
            self.logger = None

    def setup(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        file_path: str = "logs/agent.log",
        console_output: bool = True
    ):
        """Configure structured logging.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_format: Format type ("json" or "text")
            file_path: Path to log file
            console_output: Whether to output to console
        """
        # Create logs directory if it doesn't exist
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer() if log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Set up standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

        # Create file handler with JSON formatting
        if log_format == "json":
            file_handler = logging.FileHandler(file_path)
            json_formatter = jsonlogger.JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s'
            )
            file_handler.setFormatter(json_formatter)
            logging.getLogger().addHandler(file_handler)

        self.logger = structlog.get_logger()

    def get_logger(self, name: str = None) -> structlog.stdlib.BoundLogger:
        """Get a bound logger instance.

        Args:
            name: Optional logger name (e.g., 'orchestrator', 'coder')

        Returns:
            Bound logger instance
        """
        if self.logger is None:
            self.setup()  # Initialize with defaults if not already set up

        if name:
            return self.logger.bind(component=name)
        return self.logger

    def log_iteration_start(
        self,
        task_id: str,
        iteration: int,
        phase: str,
        **kwargs
    ):
        """Log the start of an iteration.

        Args:
            task_id: UUID of the task
            iteration: Iteration number
            phase: Current phase (planning, coding, testing, reflecting)
            **kwargs: Additional context
        """
        self.get_logger().info(
            "iteration_start",
            task_id=task_id,
            iteration=iteration,
            phase=phase,
            **kwargs
        )

    def log_iteration_complete(
        self,
        task_id: str,
        iteration: int,
        phase: str,
        duration: float,
        success: bool,
        **kwargs
    ):
        """Log the completion of an iteration.

        Args:
            task_id: UUID of the task
            iteration: Iteration number
            phase: Current phase
            duration: Time taken in seconds
            success: Whether the iteration succeeded
            **kwargs: Additional context
        """
        self.get_logger().info(
            "iteration_complete",
            task_id=task_id,
            iteration=iteration,
            phase=phase,
            duration=duration,
            success=success,
            **kwargs
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        task_id: str = None,
        iteration: int = None,
        **kwargs
    ):
        """Log an error with context.

        Args:
            error_type: Type of error
            error_message: Error message
            task_id: Optional task ID
            iteration: Optional iteration number
            **kwargs: Additional context
        """
        self.get_logger().error(
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            task_id=task_id,
            iteration=iteration,
            **kwargs
        )

    def log_metric(
        self,
        metric_type: str,
        value: float,
        task_id: str = None,
        **kwargs
    ):
        """Log a metric.

        Args:
            metric_type: Type of metric
            value: Metric value
            task_id: Optional task ID
            **kwargs: Additional context
        """
        self.get_logger().info(
            "metric",
            metric_type=metric_type,
            value=value,
            task_id=task_id,
            **kwargs
        )

    def log_approval_request(
        self,
        approval_type: str,
        details: Dict[str, Any],
        task_id: str = None,
        **kwargs
    ):
        """Log an approval request.

        Args:
            approval_type: Type of approval requested
            details: Details of the request
            task_id: Optional task ID
            **kwargs: Additional context
        """
        self.get_logger().info(
            "approval_request",
            approval_type=approval_type,
            details=details,
            task_id=task_id,
            **kwargs
        )


# Singleton instance
def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Optional component name

    Returns:
        Bound logger instance
    """
    return AgentLogger().get_logger(name)


def setup_logging(config: Dict[str, Any]):
    """Setup logging from configuration.

    Args:
        config: Logging configuration dictionary
    """
    logger = AgentLogger()
    logger.setup(
        log_level=config.get('level', 'INFO'),
        log_format=config.get('format', 'json'),
        file_path=config.get('file_path', 'logs/agent.log'),
        console_output='console' in config.get('outputs', ['console'])
    )
