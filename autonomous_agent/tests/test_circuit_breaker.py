"""Tests for circuit breaker utility."""

import pytest

from src.utils.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""

    def test_initialization_defaults(self):
        """Test CircuitBreaker initialization with defaults."""
        breaker = CircuitBreaker()
        assert breaker.warning_threshold == 12
        assert breaker.hard_stop == 15
        assert breaker.user_confirmed is False

    def test_initialization_custom(self):
        """Test CircuitBreaker with custom thresholds."""
        breaker = CircuitBreaker(warning_threshold=5, hard_stop=10)
        assert breaker.warning_threshold == 5
        assert breaker.hard_stop == 10

    def test_should_stop_below_warning(self):
        """Test should_stop below warning threshold."""
        breaker = CircuitBreaker(warning_threshold=10, hard_stop=15)
        assert breaker.should_stop(5) is False

    def test_should_stop_at_warning(self):
        """Test should_stop at warning threshold (should not stop)."""
        breaker = CircuitBreaker(warning_threshold=10, hard_stop=15)
        assert breaker.should_stop(10) is False
        # But user_confirmed should be set
        assert breaker.user_confirmed is True

    def test_should_stop_at_warning_only_once(self):
        """Test warning confirmation happens only once."""
        breaker = CircuitBreaker(warning_threshold=10, hard_stop=15)
        # First call at warning threshold sets user_confirmed
        breaker.should_stop(10)
        assert breaker.user_confirmed is True

        # Subsequent calls after warning threshold don't change user_confirmed
        breaker.should_stop(11)
        breaker.should_stop(12)
        # It stays True once set
        assert breaker.user_confirmed is True

    def test_should_stop_at_hard_limit(self):
        """Test should_stop at hard limit."""
        breaker = CircuitBreaker(warning_threshold=10, hard_stop=15)
        assert breaker.should_stop(15) is True
        assert breaker.should_stop(16) is True

    def test_reset(self):
        """Test reset functionality."""
        breaker = CircuitBreaker(warning_threshold=10, hard_stop=15)
        breaker.user_confirmed = True
        breaker.reset()
        assert breaker.user_confirmed is False

    def test_progression(self):
        """Test typical progression through iterations."""
        breaker = CircuitBreaker(warning_threshold=12, hard_stop=15)

        # Below warning
        for i in range(1, 12):
            assert breaker.should_stop(i) is False

        # At warning
        assert breaker.should_stop(12) is False
        assert breaker.user_confirmed is True

        # Between warning and hard stop
        for i in range(13, 15):
            assert breaker.should_stop(i) is False

        # At hard stop
        assert breaker.should_stop(15) is True

    def test_different_thresholds(self):
        """Test with various threshold combinations."""
        breaker = CircuitBreaker(warning_threshold=3, hard_stop=5)

        assert breaker.should_stop(1) is False
        assert breaker.should_stop(2) is False
        assert breaker.should_stop(3) is False
        assert breaker.user_confirmed is True
        assert breaker.should_stop(4) is False
        assert breaker.should_stop(5) is True
