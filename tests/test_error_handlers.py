from unittest.mock import MagicMock

import pytest

from pythonchik.utils.error_context import ErrorSeverity
from pythonchik.utils.error_handler import (
    AppError,
    DataProcessingError,
    ErrorHandler,
    FileOperationError,
    ImageProcessingError,
)

# ----------------------------------------------------------------
# Тестируем базовые классы AppError и его наследников
# ----------------------------------------------------------------


def test_app_error_basic():
    """Проверяем базовый AppError без контекста."""
    err = AppError("Something went wrong")
    assert err.message == "Something went wrong"
    assert err.context is None
    # __str__ использует format_message
    assert str(err) == "Something went wrong"


def test_app_error_with_context():
    """Проверяем AppError с контекстом и recovery_action."""
    from pythonchik.utils.error_context import ErrorContext

    ctx = ErrorContext(
        operation="TestOperation",
        details={"key": "value"},
        severity=ErrorSeverity.WARNING,
        recovery_action="Try something",
    )
    err = AppError("Oops", context=ctx)
    assert "[WARNING] TestOperation: Oops" in str(err)
    assert "Рекомендуемое действие: Try something" in str(err)


def test_file_operation_error():
    """Проверяем FileOperationError и наличие path в context.details."""
    err = FileOperationError("File not found", "/path/to/file")
    assert "File not found" in str(err)
    assert err.context is not None
    assert err.context.details["path"] == "/path/to/file"
    assert err.context.severity == ErrorSeverity.ERROR
    assert "FileOperationError" in err.context.details["error_type"]


def test_image_processing_error():
    """Проверяем ImageProcessingError и наличие image_path в context.details."""
    err = ImageProcessingError("Bad image format", "/images/img.png")
    assert "Bad image format" in str(err)
    assert err.context.details["image_path"] == "/images/img.png"
    assert "ImageProcessingError" == err.context.details["error_type"]


def test_data_processing_error():
    """Проверяем DataProcessingError и наличие data_type в context.details."""
    err = DataProcessingError("Invalid JSON", "json")
    assert "Invalid JSON" in str(err)
    assert err.context.details["data_type"] == "json"
    assert err.context.operation == "Обработка данных"


# ----------------------------------------------------------------
# Тестируем ErrorHandler
# ----------------------------------------------------------------


def test_error_handler_wrap_builtin_error():
    """
    Проверяем, что ErrorHandler корректно оборачивает обычную Python ошибку
    (ValueError) в AppError, формирует контекст и логирует.
    """
    mock_log_callback = MagicMock()
    handler = ErrorHandler(log_callback=mock_log_callback)

    # Искусственно вызываем ValueError
    try:
        raise ValueError("Some invalid data")
    except ValueError as e:
        handler.handle_error(
            error=e,
            operation="Parsing data",
            severity=ErrorSeverity.ERROR,
            recovery_action="Check the input format",
            additional_context={"field": "age"},
        )

    mock_log_callback.assert_called_once()
    logged_msg, logged_severity = mock_log_callback.call_args[0]

    assert "[ERROR] Parsing data: Some invalid data" in logged_msg
    assert "Рекомендуемое действие: Check the input format" in logged_msg
    # Доп. контекст
    assert "field" in logged_msg
    assert logged_severity == "ERROR"


def test_error_handler_handle_existing_app_error():
    """
    Если передаём AppError c уже существующим контекстом,
    ErrorHandler не создает новый, а дополняет текущий.
    """
    from pythonchik.utils.error_context import ErrorContext

    ctx = ErrorContext(
        operation="InitialOperation", details={"initial": "detail"}, severity=ErrorSeverity.WARNING
    )
    app_err = AppError("Already has context", context=ctx)

    mock_log_callback = MagicMock()
    handler = ErrorHandler(log_callback=mock_log_callback)

    # Передаём уже готовый AppError
    handler.handle_error(
        app_err,
        operation="ShouldNotOverwriteOperation",
        severity=ErrorSeverity.ERROR,  # вроде бы новый severity
        additional_context={"extra": "info"},
    )

    mock_log_callback.assert_called_once()
    logged_msg, logged_severity = mock_log_callback.call_args[0]

    # Проверяем, что старый operation остался
    assert "[WARNING] InitialOperation: Already has context" in logged_msg
    # Доп контекст
    assert "extra" in logged_msg
    # Severity внутри AppError не меняется,
    # но логируем с severity=ERROR => logged_severity = "ERROR"
    assert logged_severity == "ERROR"


def test_error_handler_default_recovery_action():
    """
    Проверяем, что ErrorHandler подставляет стандартное recovery_action
    если не передан явно.
    """
    mock_log_callback = MagicMock()
    handler = ErrorHandler(log_callback=mock_log_callback)

    try:
        raise KeyError("missing 'foo'")
    except KeyError as e:
        handler.handle_error(e, operation="Access dictionary", severity=ErrorSeverity.ERROR)

    mock_log_callback.assert_called_once()
    logged_msg, _ = mock_log_callback.call_args[0]

    # Для KeyError в _get_default_recovery_action
    # прописано "Проверьте наличие требуемого ключа в данных"
    assert "Проверьте наличие требуемого ключа в данных" in logged_msg


def test_error_handler_unknown_builtin_error():
    """
    Если тип ошибки не в recovery_actions,
    должно использоваться "Обратитесь к документации или администратору".
    """
    mock_log_callback = MagicMock()
    handler = ErrorHandler(log_callback=mock_log_callback)

    class CustomPythonError(Exception):
        pass

    try:
        raise CustomPythonError("Something custom")
    except CustomPythonError as e:
        handler.handle_error(e, operation="Custom operation")

    mock_log_callback.assert_called_once()
    logged_msg, _ = mock_log_callback.call_args[0]
    assert "Обратитесь к документации или администратору" in logged_msg


def test_error_handler_no_recovery_action_for_app_error():
    """
    Если мы создаём новый AppError без recovery_action,
    но severity=ERROR, нужно проверить,
    что всё же появляется "Обратитесь к документации..." (или то, что в коде).
    """
    mock_log_callback = MagicMock()
    handler = ErrorHandler(log_callback=mock_log_callback)

    # Создаём AppError без контекста
    err = AppError("Some app error")

    handler.handle_error(
        err,
        operation="SomeOperation",
        severity=ErrorSeverity.ERROR,
        recovery_action=None,  # не указано
        additional_context=None,
    )

    mock_log_callback.assert_called_once()
    logged_msg, _ = mock_log_callback.call_args[0]
    # внутри handle_error -> _get_default_recovery_action(err)
    # err - AppError, type(err).__name__ = 'AppError' -> не в словаре => "Обратитесь к документации..."
    assert "Обратитесь к документации или администратору" in logged_msg
