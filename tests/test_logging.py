"""Tests for the logging system implementation.

This module contains comprehensive tests for the logging configuration,
JSON formatting, context logging, and log rotation functionality.
"""

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest

from pythonchik.utils.logging_config import ContextLogger, JSONFormatter, setup_logging


class TestHandler(logging.Handler):
    """A handler class for testing logging output."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@pytest.fixture
def temp_log_dir(tmp_path):
    """Creates a temporary directory for log files."""
    log_dir = tmp_path / "test_logs"
    yield str(log_dir)
    if log_dir.exists():
        shutil.rmtree(log_dir)


@pytest.fixture
def json_formatter():
    """Creates a JSONFormatter instance for testing."""
    return JSONFormatter()


@pytest.fixture
def context_logger():
    """Creates a ContextLogger instance for testing."""
    return ContextLogger("test_logger")


def test_json_formatter_basic_format(json_formatter):
    """Test basic JSON formatting of log records."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    formatted = json_formatter.format(record)
    data = json.loads(formatted)

    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert data["logger"] == "test"
    assert data["path"] == "test.py"
    assert data["line"] == 1
    assert "timestamp" in data


def test_json_formatter_error_with_exception(json_formatter):
    """Test JSON formatting of error records with exception information."""
    try:
        raise ValueError("Test error")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = json_formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test error"
        assert isinstance(data["exception"]["traceback"], list)


def test_context_logger_extra_fields(context_logger):
    """Test logging with additional context fields."""
    with TestHandler() as handler:
        context_logger.addHandler(handler)
        context_logger.error("Test error", extra_fields={"user_id": "123", "action": "test_action"})

        assert len(handler.records) == 1
        record = handler.records[0]
        assert hasattr(record, "extra_fields")
        assert record.extra_fields["user_id"] == "123"
        assert record.extra_fields["action"] == "test_action"


def test_log_rotation(temp_log_dir):
    """Test log file rotation functionality."""
    setup_logging(temp_log_dir)
    logger = logging.getLogger("pythonchik")

    # Write enough logs to trigger rotation
    large_message = "x" * 1000000  # 1MB message
    for _ in range(12):  # Should create multiple log files
        logger.info(large_message)

    log_files = list(Path(temp_log_dir).glob("pythonchik.log*"))
    assert len(log_files) > 1  # Should have multiple log files
    assert len(log_files) <= 6  # Main log + 5 backups maximum


def test_console_output_levels(temp_log_dir):
    """Test that console output respects log levels."""
    setup_logging(temp_log_dir)
    logger = logging.getLogger("pythonchik")

    with TestHandler() as handler:
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should appear
        logger.warning("Warning message")  # Should appear
        logger.error("Error message")  # Should appear

        messages = [r.message for r in handler.records]
        assert "Debug message" not in messages
        assert "Info message" in messages
        assert "Warning message" in messages
        assert "Error message" in messages


def test_file_logging_all_levels(temp_log_dir):
    """Test that file logging captures all log levels."""
    setup_logging(temp_log_dir)
    logger = logging.getLogger("pythonchik")

    test_messages = {
        "debug": "Debug test message",
        "info": "Info test message",
        "warning": "Warning test message",
        "error": "Error test message",
    }

    logger.debug(test_messages["debug"])
    logger.info(test_messages["info"])
    logger.warning(test_messages["warning"])
    logger.error(test_messages["error"])

    log_file = Path(temp_log_dir) / "pythonchik.log"
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()

    for message in test_messages.values():
        assert message in content


def test_logging_initialization(temp_log_dir):
    """Test logging system initialization with custom directory."""
    setup_logging(temp_log_dir)

    # Check if log directory was created
    assert Path(temp_log_dir).exists()
    assert Path(temp_log_dir).is_dir()

    # Check if log file was created
    log_file = Path(temp_log_dir) / "pythonchik.log"
    assert log_file.exists()

    # Verify initialization message
    with open(log_file, "r", encoding="utf-8") as f:
        content = json.loads(f.readline())
        assert "Система логирования инициализирована" in content["message"]
        assert "version" in content["extra_fields"]
        assert "environment" in content["extra_fields"]
