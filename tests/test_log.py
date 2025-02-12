from datetime import datetime

import customtkinter as ctk
import pytest

from pythonchik.ui.frames.log import LogFrame


@pytest.fixture
def log_frame():
    root = ctk.CTk()
    frame = LogFrame(root)
    yield frame
    root.destroy()


def test_log_initialization(log_frame):
    """Test initial state of the log frame."""
    assert log_frame.log_text.get("1.0", "end-1c") == ""
    assert log_frame._text_after_id is None


def test_log_message_formatting(log_frame):
    """Test log message formatting with different levels."""
    log_frame.log("Test message", "INFO")
    log_content = log_frame.log_text.get("1.0", "end-1c")

    # Check timestamp format [HH:MM:SS]
    assert "[" in log_content and "]" in log_content
    assert "[INFO]" in log_content
    assert "Test message" in log_content


def test_log_levels(log_frame):
    """Test different log levels appearance."""
    levels = ["INFO", "WARNING", "ERROR"]
    for level in levels:
        log_frame.log(f"Test {level} message", level)
        log_content = log_frame.log_text.get("1.0", "end-1c")
        assert f"[{level}]" in log_content


def test_operation_separator(log_frame):
    """Test separator lines between operations."""
    log_frame.log("Начало операции")
    log_content = log_frame.log_text.get("1.0", "end-1c")
    assert "─ ─" in log_content

    log_frame.log("Процесс завершен")
    log_content = log_frame.log_text.get("1.0", "end-1c")
    assert log_content.count("─ ─" * 20) == 2


def test_clear_log(log_frame):
    """Test log clearing functionality."""
    log_frame.log("Test message")
    assert log_frame.log_text.get("1.0", "end-1c") != ""

    log_frame.clear_log()
    assert log_frame.log_text.get("1.0", "end-1c") == ""
    assert log_frame._text_after_id is None


def test_multiple_logs(log_frame):
    """Test multiple log messages in sequence."""
    messages = ["First message", "Second message", "Third message"]
    for msg in messages:
        log_frame.log(msg)

    log_content = log_frame.log_text.get("1.0", "end-1c")
    for msg in messages:
        assert msg in log_content


def test_log_state_management(log_frame):
    """Test text widget state management during logging."""
    log_frame.log("Test message")
    assert log_frame.log_text._textbox.cget("state") == "disabled"

    log_frame.clear_log()
    assert log_frame.log_text._textbox.cget("state") == "disabled"
