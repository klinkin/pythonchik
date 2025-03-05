"""Модуль обработки ошибок и исключений приложения Pythonchik.

Этот модуль предоставляет инфраструктуру для централизованной обработки ошибок,
классификации исключений по типам и уровням серьезности, а также их последующей
обработки через специализированные обработчики.

Основные компоненты:
- ErrorContext: Контекст ошибки с дополнительной информацией и уровнем серьезности
- ErrorSeverity: Перечисление уровней серьезности ошибок (INFO, WARNING, ERROR, CRITICAL)
- ErrorHandler: Базовый класс для всех обработчиков ошибок
- Специализированные обработчики: UIErrorHandler, FileProcessingErrorHandler и др.
- Специализированные исключения: AppError, DataProcessingError, FileOperationError и др.

Преимущества использования:
- Единая точка обработки ошибок в приложении
- Классификация ошибок по типам и уровням серьезности
- Возможность специализированной обработки разных типов ошибок
- Интеграция с системой логирования и уведомлений пользователя

Пример использования:
    >>> from pythonchik.errors import ErrorContext, ErrorSeverity, UIErrorHandler
    >>> from pythonchik.events.eventbus import EventBus
    >>>
    >>> # Создание обработчика ошибок UI
    >>> bus = EventBus()
    >>> error_handler = UIErrorHandler(bus)
    >>>
    >>> try:
    ...     # Код, который может вызвать ошибку
    ...     result = process_data(invalid_data)
    ... except Exception as e:
    ...     # Создание контекста ошибки
    ...     context = ErrorContext(
    ...         exception=e,
    ...         severity=ErrorSeverity.ERROR,
    ...         message="Не удалось обработать данные",
    ...     )
    ...     # Обработка ошибки
    ...     error_handler.handle_error(context)
"""

from pythonchik.errors.error_context import ErrorContext, ErrorSeverity
from pythonchik.errors.error_handlers import (
    AppError,
    DataProcessingError,
    DataProcessingErrorHandler,
    ErrorHandler,
    FileOperationError,
    FileProcessingErrorHandler,
    ImageProcessingError,
    ImageProcessingErrorHandler,
    TaskOperationError,
    UIErrorHandler,
)

__all__ = [
    "AppError",
    "DataProcessingError",
    "ErrorHandler",
    "FileOperationError",
    "ImageProcessingError",
    "TaskOperationError",
    "ErrorContext",
    "ErrorSeverity",
    "UIErrorHandler",
    "FileProcessingErrorHandler",
    "ImageProcessingErrorHandler",
    "DataProcessingErrorHandler",
]
