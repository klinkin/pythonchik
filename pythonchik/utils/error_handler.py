"""
Модуль централизованной обработки ошибок (error_handlers).

Предоставляет классы и функции для стандартизированной обработки ошибок,
включая форматирование сообщений, логирование и стратегии восстановления.
"""

import logging
from typing import Any, Callable, Dict, Optional

from pythonchik.utils.error_context import ErrorContext, ErrorSeverity

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Базовый класс для всех ошибок приложения.

    Предоставляет стандартизированный формат сообщений об ошибках
    и дополнительный контекст для логирования.

    Attributes:
        message (str): Описание ошибки.
        context (Optional[ErrorContext]): Контекст ошибки (операция, детали, уровень серьезности).
        original_error (Optional[Exception]): Исходное исключение, если обёрнуто.
    """

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """
        Args:
            message: Текст сообщения об ошибке.
            context: Дополнительный контекст с деталями, уровнем серьезности и т.д.
            original_error: Исходное исключение (если данная ошибка оборачивает другое).
        """
        self.message = message
        self.context = context
        self.original_error = original_error
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Форматирует сообщение об ошибке в стандартизированном виде.

        Returns:
            str: Итоговое сообщение об ошибке.
        """
        if not self.context:
            return self.message

        base_msg = f"[{self.context.severity.value}] {self.context.operation}: {self.message}"

        # Add context details if present
        if self.context.details:
            details_str = ", ".join(f"{k}: {v}" for k, v in self.context.details.items())
            base_msg += f"\nContext: {details_str}"

        if self.context.recovery_action:
            base_msg += f"\nРекомендуемое действие: {self.context.recovery_action}"
        return base_msg


class FileOperationError(AppError):
    """Ошибки при работе с файлами.

    Используется для:
    - Чтения/записи файлов
    - Проверки существования
    - Управления правами доступа
    """

    def __init__(self, message: str, path: str, operation: str = "Операция с файлом") -> None:
        """
        Args:
            message: Текст ошибки.
            path: Путь к файлу, на котором произошла ошибка.
            operation: Название операции (по умолчанию 'Операция с файлом').
        """
        context = ErrorContext(
            operation=operation,
            details={"path": path, "error_type": "FileOperationError"},
            severity=ErrorSeverity.ERROR,
            recovery_action="Проверьте права доступа и существование файла",
        )
        super().__init__(message, context)


class TaskOperationError(AppError):
    """Ошибки при работе с задачами.

    Используется для:
    - Чтения/записи файлов
    - Проверки существования
    - Управления правами доступа
    """

    def __init__(self, message: str, path: str, operation: str = "Операция с файлом") -> None:
        """
        Args:
            message: Текст ошибки.
            path: Путь к файлу, на котором произошла ошибка.
            operation: Название операции (по умолчанию 'Операция с файлом').
        """
        context = ErrorContext(
            operation=operation,
            details={"path": path, "error_type": "FileOperationError"},
            severity=ErrorSeverity.ERROR,
            recovery_action="Проверьте права доступа и существование файла",
        )
        super().__init__(message, context)


class ImageProcessingError(AppError):
    """Ошибки при обработке изображений.

    Используется для:
    - Конвертации форматов
    - Изменения размеров
    - Применения фильтров
    """

    def __init__(self, message: str, image_path: str, operation: str = "Обработка изображения") -> None:
        """
        Args:
            message: Текст ошибки.
            image_path: Путь к изображению, где произошла ошибка.
            operation: Название операции (по умолчанию 'Обработка изображения').
        """
        context = ErrorContext(
            operation=operation,
            details={"image_path": image_path, "error_type": "ImageProcessingError"},
            severity=ErrorSeverity.ERROR,
            recovery_action="Проверьте формат и целостность изображения",
        )
        super().__init__(message, context)


class DataProcessingError(AppError):
    """Ошибки при обработке данных.

    Используется для:
    - Парсинга JSON/XML
    - Валидации данных
    - Преобразования форматов
    """

    def __init__(self, message: str, data_type: str, operation: str = "Обработка данных") -> None:
        """
        Args:
            message: Текст ошибки.
            data_type: Тип данных, которые обрабатываются (JSON, XML, etc.).
            operation: Название операции (по умолчанию 'Обработка данных').
        """
        context = ErrorContext(
            operation=operation,
            details={"data_type": data_type, "error_type": "DataProcessingError"},
            severity=ErrorSeverity.ERROR,
            recovery_action="Проверьте формат и структуру данных",
        )
        super().__init__(message, context)


class ErrorHandler:
    """Обработчик ошибок приложения.

    Предоставляет методы для обработки различных типов ошибок
    и их логирования в стандартизированном формате.
    """

    @staticmethod
    def _default_log_callback(msg: str, severity: str) -> None:
        """Колбэк логирования по умолчанию (использует стандартный logger).

        Args:
            msg (str): Сообщение для логирования.
            severity (str): Уровень серьезности (DEBUG, INFO, WARNING, ERROR...).
        """
        # Можно использовать logger по уровню severity:
        # Или просто logger.error(msg) — упрощённый вариант
        logger.error(f"[{severity}] {msg}")

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None) -> None:
        """
        Args:
            log_callback: Функция, принимающая (message, severity)
                по умолчанию выводит через logger.error.
        """
        self.log_callback = log_callback if log_callback else self._default_log_callback

    def handle_error(
        self,
        error: Exception,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_action: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Обрабатывает ошибку и логирует её в стандартизированном формате.

        Args:
            error (Exception): Исключение для обработки.
            operation (str): Название операции, при которой произошла ошибка.
            severity (ErrorSeverity): Уровень серьезности ошибки (по умолчанию ERROR).
            recovery_action (Optional[str]): Рекомендуемое действие для восстановления.
            additional_context (Optional[Dict[str, Any]]): Дополнительные детали для логирования.

        Пример использования:
            try:
                process_file('example.txt')
            except FileNotFoundError as e:
                error_handler.handle_error(
                    e,
                    'Чтение файла',
                    ErrorSeverity.ERROR,
                    'Проверьте существование файла',
                    {'file_path': 'example.txt', 'attempt': 1}
                )
        """
        details = {"error_type": type(error).__name__}
        if additional_context:
            details.update(additional_context)

        if isinstance(error, AppError) and error.context:
            # Если это AppError со своим контекстом — дополним его
            error.context.details.update(details)
            app_error = error
        else:
            # Иначе создаём новый AppError, оборачивая исходную ошибку
            context = ErrorContext(
                operation=operation,
                details=details,
                severity=severity,
                recovery_action=recovery_action or self._get_default_recovery_action(error),
            )
            app_error = AppError(str(error), context, error)

        # Логируем через заданный колбэк
        self.log_callback(app_error.format_message(), severity.value)

    def _get_default_recovery_action(self, error: Exception) -> str:
        """Возвращает стандартное действие восстановления на основе типа ошибки.

        Args:
            error (Exception): Исходная ошибка.

        Returns:
            str: Рекомендуемое действие для восстановления.
        """
        error_type = type(error).__name__
        recovery_actions = {
            "FileNotFoundError": "Проверьте существование файла и его путь",
            "PermissionError": "Проверьте права доступа к файлу или директории",
            "ValueError": "Проверьте корректность введённых данных",
            "TypeError": "Проверьте типы передаваемых данных",
            "KeyError": "Проверьте наличие требуемого ключа в данных",
            "IndexError": "Проверьте границы массива или списка",
            "ZeroDivisionError": "Проверьте деление на ноль",
            "AttributeError": "Проверьте наличие требуемого атрибута",
            "ImportError": "Проверьте наличие требуемого модуля",
            "RuntimeError": "Произошла ошибка выполнения, проверьте логи",
        }
        return recovery_actions.get(error_type, "Обратитесь к документации или администратору")
