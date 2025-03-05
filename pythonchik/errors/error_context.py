"""Модуль контекста и уровней серьезности ошибок.

Этот модуль предоставляет основные классы для стандартизированного управления
ошибками во всем приложении. Он вводит концепцию контекста ошибки, который
включает информацию об операции, деталях, уровне серьезности и возможных
действиях по восстановлению.

Основные компоненты:
- ErrorSeverity: Перечисление уровней серьезности ошибок
- ErrorContext: Класс для хранения контекстной информации об ошибке

Примеры использования:
    >>> from pythonchik.errors.error_context import ErrorContext, ErrorSeverity
    >>>
    >>> # Создание контекста ошибки
    >>> context = ErrorContext(
    ...     operation="file_processing",
    ...     details={"filename": "data.json", "error_type": "parsing_error"},
    ...     severity=ErrorSeverity.ERROR,
    ...     recovery_action="Проверьте формат файла и попробуйте снова"
    ... )
    >>>
    >>> # Использование в обработке ошибок
    >>> try:
    ...     # Код, который может вызвать ошибку
    ...     result = process_file("data.json")
    ... except Exception as e:
    ...     context = ErrorContext(
    ...         operation="file_processing",
    ...         details={"filename": "data.json", "exception": str(e)},
    ...         severity=ErrorSeverity.ERROR
    ...     )
    ...     # Передача контекста обработчику ошибок
    ...     error_handler.handle_error(context)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок для классификации инцидентов.

    Предоставляет стандартизированные уровни серьезности для ошибок,
    которые используются для определения приоритета, методов логирования
    и стратегий обработки ошибок.

    Attributes:
        INFO: Информационное сообщение, не требующее действий
        WARNING: Предупреждение, может потребовать внимания пользователя
        ERROR: Ошибка, требующая внимания пользователя или разработчика
        CRITICAL: Критическая ошибка, требующая немедленного вмешательства

    Examples:
        >>> severity = ErrorSeverity.WARNING
        >>> if severity == ErrorSeverity.WARNING:
        ...     print("Обнаружено предупреждение")
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorContext:
    """Контекст ошибки для детализированного логирования и обработки.

    Объединяет всю необходимую информацию об ошибке в единую структуру,
    что позволяет стандартизировать обработку ошибок в приложении и
    предоставлять подробную контекстную информацию для отладки.

    Attributes:
        operation: Название операции, во время которой произошла ошибка
        details: Словарь с дополнительными деталями об ошибке (имя файла, ID записи и т.д.)
        severity: Уровень серьезности ошибки из перечисления ErrorSeverity
        recovery_action: Опциональные инструкции для восстановления после ошибки

    Examples:
        >>> context = ErrorContext(
        ...     operation="load_json",
        ...     details={"path": "/path/to/file.json"},
        ...     severity=ErrorSeverity.ERROR,
        ...     recovery_action="Проверьте формат JSON-файла"
        ... )
        >>> print(f"Ошибка в операции {context.operation}")
        >>> print(f"Уровень серьезности: {context.severity.value}")
    """

    operation: str
    details: Dict[str, Any]
    severity: ErrorSeverity
    recovery_action: Optional[str] = None
