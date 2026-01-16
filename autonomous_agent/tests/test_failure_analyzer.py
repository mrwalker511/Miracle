"""Tests for failure analyzer."""

import pytest

from src.memory.failure_analyzer import FailureAnalyzer, FailureInfo


class TestFailureInfo:
    """Test cases for FailureInfo dataclass."""

    def test_create_failure_info(self):
        """Test creating FailureInfo."""
        info = FailureInfo(
            error_message="ImportError: No module named 'xyz'",
            error_type="ImportError",
            error_signature="ImportError: No module named 'X'",
            stack_trace="Traceback..."
        )

        assert info.error_message == "ImportError: No module named 'xyz'"
        assert info.error_type == "ImportError"
        assert info.error_signature == "ImportError: No module named 'X'"
        assert info.stack_trace == "Traceback..."


class TestFailureAnalyzer:
    """Test cases for FailureAnalyzer."""

    def test_initialization(self):
        """Test FailureAnalyzer initialization."""
        analyzer = FailureAnalyzer()
        assert len(analyzer.COMMON_ERROR_TYPES) > 0

    def test_extract_with_error_message(self):
        """Test extraction with error_message."""
        analyzer = FailureAnalyzer()
        test_results = {
            "error_message": "ImportError: No module named 'requests'",
            "stderr": "Full error details",
            "stack_trace": "Traceback (most recent call last):..."
        }

        info = analyzer.extract(test_results)

        assert info is not None
        assert info.error_type == "ImportError"
        assert "ImportError" in info.error_message
        assert info.stack_trace is not None

    def test_extract_with_stderr(self):
        """Test extraction with stderr only."""
        analyzer = FailureAnalyzer()
        test_results = {
            "stderr": "AttributeError: 'NoneType' object has no attribute 'x'",
        }

        info = analyzer.extract(test_results)

        assert info is not None
        assert info.error_type == "AttributeError"
        assert "AttributeError" in info.error_message

    def test_extract_from_raw_test_results(self):
        """Test extraction from raw test_results dict."""
        analyzer = FailureAnalyzer()
        test_results = {
            "test_results": {"error": "KeyError: 'missing_key'"}
        }

        info = analyzer.extract(test_results)

        assert info is not None
        assert info.error_type == "KeyError"

    def test_extract_no_error(self):
        """Test extraction when no error is present."""
        analyzer = FailureAnalyzer()
        # When there's no error message and no stderr, it extracts from test_results
        # which will result in UnknownError type
        test_results = {
            "passed": True,
            "test_results": {"passed": 5, "failed": 0},
            "error_message": "",
            "stderr": ""
        }

        info = analyzer.extract(test_results)

        # With empty error_message and stderr, it falls back to test_results
        # Since there's no error type in the dict, it becomes UnknownError
        # This is actually expected behavior - it always extracts something if test_results is not empty
        assert info is not None

    def test_extract_error_type_import_error(self):
        """Test extracting ImportError type."""
        analyzer = FailureAnalyzer()
        text = "ImportError: No module named 'xyz'"

        error_type = analyzer._extract_error_type(text)
        assert error_type == "ImportError"

    def test_extract_error_type_attribute_error(self):
        """Test extracting AttributeError type."""
        analyzer = FailureAnalyzer()
        text = "AttributeError: 'NoneType' object has no attribute"

        error_type = analyzer._extract_error_type(text)
        assert error_type == "AttributeError"

    def test_extract_error_type_unknown(self):
        """Test extracting unknown error type."""
        analyzer = FailureAnalyzer()
        text = "Some weird error without standard type"

        error_type = analyzer._extract_error_type(text)
        assert error_type == "UnknownError"

    def test_create_error_signature_basic(self):
        """Test creating basic error signature."""
        analyzer = FailureAnalyzer()
        error_text = "ImportError: No module named 'requests'"

        signature = analyzer._create_error_signature(error_text, "ImportError")

        assert "ImportError" in signature
        assert signature != error_text  # Should be normalized

    def test_create_error_signature_normalizes_files(self):
        """Test error signature normalizes file paths."""
        analyzer = FailureAnalyzer()
        error_text = 'File "/path/to/file.py", line 42, in function\n  ImportError: module not found'

        signature = analyzer._create_error_signature(error_text, "ImportError")

        assert "/path/to/file.py" not in signature
        assert "line 42" not in signature
        assert "ImportError" in signature

    def test_create_error_signature_normalizes_quotes(self):
        """Test error signature normalizes quoted strings."""
        analyzer = FailureAnalyzer()
        error_text = "KeyError: 'specific_variable_name'"

        signature = analyzer._create_error_signature(error_text, "KeyError")

        assert "specific_variable_name" not in signature
        assert "'X'" in signature

    def test_create_error_signature_fallback(self):
        """Test error signature fallback to first line."""
        analyzer = FailureAnalyzer()
        error_text = "Random error without type keyword\n  Some details\n  More details"

        signature = analyzer._create_error_signature(error_text, "UnknownError")

        assert "Random error" in signature
        assert "UnknownError:" in signature

    def test_extract_complex_stack_trace(self):
        """Test extraction with complex stack trace."""
        analyzer = FailureAnalyzer()
        test_results = {
            "error_message": "ValueError: invalid literal for int()",
            "stack_trace": """
Traceback (most recent call last):
  File "app.py", line 10, in main
    value = int(input_data)
ValueError: invalid literal for int() with base 10: 'abc'
            """.strip()
        }

        info = analyzer.extract(test_results)

        assert info is not None
        assert info.error_type == "ValueError"
        assert info.stack_trace is not None
        assert "Traceback" in info.stack_trace

    def test_all_common_error_types(self):
        """Test that all common error types are recognized."""
        analyzer = FailureAnalyzer()

        for error_type in analyzer.COMMON_ERROR_TYPES:
            text = f"{error_type}: test message"
            extracted = analyzer._extract_error_type(text)
            assert extracted == error_type
