"""Тесты для модуля обработки ошибок.

Этот модуль содержит тесты для компонентов системы обработки ошибок:
- AppError: Базовый класс ошибок приложения
- Специализированные классы ошибок (FileOperationError, TaskOperationError и др.)
- ErrorHandler: Централизованная обработка и логирование ошибок
- ErrorContext: Контекстная информация для ошибок

Фикстуры:
- error_handler: Экземпляр ErrorHandler для тестирования
- logger_mock: Мок логгера для проверки вызовов логирования
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from pythonchik.errors.error_context import ErrorContext, ErrorSeverity
from pythonchik.errors.error_handlers import (
    AppError,
    DataProcessingError,
    ErrorHandler,
    FileOperationError,
    ImageProcessingError,
)


@pytest.fixture
def error_handler():
    """Создает экземпляр ErrorHandler для тестирования.

    Returns:
        Экземпляр ErrorHandler с настройками по умолчанию.
    """
    return ErrorHandler()


@pytest.fixture
def logger_mock():
    """Создает мок объект логгера для проверки вызовов логирования.

    Returns:
        MagicMock, имитирующий объект логгера.
    """
    return MagicMock(spec=logging.Logger)


def test_app_error_basic():
    """Проверка базовой функциональности AppError.

    Тест проверяет:
    1. Корректное создание экземпляра AppError
    2. Правильное форматирование сообщения об ошибке
    3. Сохранение исходного сообщения и оригинальной ошибки

    Проверяемый класс:
        pythonchik.errors.error_handlers.AppError
    """
    # Простая ошибка без контекста
    simple_error = AppError("Тестовая ошибка")
    assert simple_error.message == "Тестовая ошибка"
    assert str(simple_error) == "Тестовая ошибка"
    assert simple_error.context is None
    assert simple_error.original_error is None


def test_app_error_with_context():
    """Проверка AppError с контекстной информацией.

    Тест проверяет:
    1. Корректное создание ошибки с контекстом
    2. Правильное форматирование сообщения с деталями контекста
    3. Включение информации о серьезности и рекомендуемом действии

    Проверяемый класс:
        pythonchik.errors.error_handlers.AppError
    """
    context = ErrorContext(
        operation="test_operation",
        details={"param1": "value1", "param2": 42},
        severity=ErrorSeverity.WARNING,
        recovery_action="Повторите попытку позже",
    )

    error = AppError("Тестовая ошибка с контекстом", context)

    # Проверяем детали ошибки
    assert error.message == "Тестовая ошибка с контекстом"
    assert error.context == context

    # Проверяем форматирование сообщения
    error_str = str(error)
    assert "[WARNING]" in error_str
    assert "test_operation" in error_str
    assert "Тестовая ошибка с контекстом" in error_str
    assert "param1: value1" in error_str
    assert "param2: 42" in error_str
    assert "Повторите попытку позже" in error_str


def test_file_operation_error():
    """Проверка класса ошибки FileOperationError.

    Тест проверяет:
    1. Корректное создание специализированной файловой ошибки
    2. Автоматическое добавление пути к файлу в контекст
    3. Правильный текст рекомендуемого действия для восстановления

    Проверяемый класс:
        pythonchik.errors.error_handlers.FileOperationError
    """
    error = FileOperationError(
        "Файл недоступен для чтения", path="/path/to/file.txt", operation="Чтение файла"
    )

    # Проверяем детали ошибки
    assert error.message == "Файл недоступен для чтения"
    assert error.context is not None
    assert error.context.operation == "Чтение файла"
    assert error.context.details["path"] == "/path/to/file.txt"
    assert error.context.details["error_type"] == "FileOperationError"
    assert error.context.recovery_action is not None
    assert "Проверьте права доступа" in error.context.recovery_action


def test_image_processing_error():
    """Проверка класса ошибки ImageProcessingError.

    Тест проверяет:
    1. Корректное создание ошибки обработки изображений
    2. Автоматическое добавление информации об изображении в контекст
    3. Правильный уровень серьезности ошибки

    Проверяемый класс:
        pythonchik.errors.error_handlers.ImageProcessingError
    """
    error = ImageProcessingError(
        "Неподдерживаемый формат изображения",
        image_path="/path/to/image.xyz",
        operation="Преобразование формата",
    )

    # Проверяем детали ошибки
    assert error.message == "Неподдерживаемый формат изображения"
    assert error.context is not None
    assert error.context.operation == "Преобразование формата"
    assert error.context.details["image_path"] == "/path/to/image.xyz"
    assert error.context.details["error_type"] == "ImageProcessingError"
    assert error.context.severity == ErrorSeverity.ERROR


def test_data_processing_error():
    """Проверяем DataProcessingError и наличие data_type в context.details."""
    err = DataProcessingError("Invalid JSON", "json")
    assert "Invalid JSON" in str(err)
    assert err.context is not None
    assert "data_type" in err.context.details
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
    assert "age" in logged_msg
    assert logged_severity == "ERROR"


def test_error_handler_handle_existing_app_error():
    """
    Если передаём AppError c уже существующим контекстом,
    ErrorHandler не создает новый, а дополняет текущий.
    """
    from pythonchik.errors.error_context import ErrorContext

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
