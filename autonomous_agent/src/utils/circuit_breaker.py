"""Circuit breaker to prevent infinite loops."""

from src.ui.logger import get_logger


class CircuitBreaker:
    """Prevents infinite loops by stopping after threshold."""

    def __init__(self, warning_threshold: int = 12, hard_stop: int = 15):
        """Initialize circuit breaker.

        Args:
            warning_threshold: Iteration to warn user
            hard_stop: Maximum iterations before hard stop
        """
        self.warning_threshold = warning_threshold
        self.hard_stop = hard_stop
        self.logger = get_logger('circuit_breaker')
        self.user_confirmed = False

    def should_stop(self, current_iteration: int) -> bool:
        """Check if execution should stop.

        Args:
            current_iteration: Current iteration number

        Returns:
            True if should stop, False otherwise
        """
        if current_iteration >= self.hard_stop:
            self.logger.warning(
                "hard_stop_triggered",
                iteration=current_iteration,
                threshold=self.hard_stop
            )
            return True

        if current_iteration >= self.warning_threshold and not self.user_confirmed:
            self.logger.warning(
                "warning_threshold_reached",
                iteration=current_iteration,
                threshold=self.warning_threshold
            )
            # In a full implementation, this would prompt the user
            # For now, allow to continue
            self.user_confirmed = True

        return False

    def reset(self):
        """Reset the circuit breaker."""
        self.user_confirmed = False
        self.logger.info("circuit_breaker_reset")
