"""Модуль централизованной обработки ошибок.

Предоставляет классы и функции для стандартизированной обработки ошибок,
включая форматирование сообщений и логирование.
"""

from typing import Callable

from pythonchik.utils.error_context import ErrorContext, ErrorSeverity


class AppError(Exception):
    """Базовый класс для всех ошибок приложения.

    Предоставляет стандартизированный формат сообщений об ошибках
    и дополнительный контекст для логирования.
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.message = message
        self.context = context
        self.original_error = original_error
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Форматирует сообщение об ошибке в стандартизированном виде."""
        if not self.context:
            return self.message

        formatted_msg = f"[{self.context.severity.value}] {self.context.operation}: {self.message}"
        if self.context.recovery_action:
            formatted_msg += f"\nРекомендуемое действие: {self.context.recovery_action}"
        return formatted_msg


class FileOperationError(AppError):
    """Ошибки при работе с файлами."""

    pass


class ImageProcessingError(AppError):
    """Ошибки при обработке изображений."""

    pass


class DataProcessingError(AppError):
    """Ошибки при обработке данных."""

    pass


class ErrorHandler:
    """Обработчик ошибок приложения.

    Предоставляет методы для обработки различных типов ошибок
    и их логирования в стандартизированном формате.
    """

    @staticmethod
    def _default_log_callback(msg: str, severity: str) -> None:
        print(f"[{severity}] {msg}")

    def __init__(self, log_callback: Callable[[str, str], None] | None = None) -> None:
        self.log_callback = log_callback if log_callback is not None else self._default_log_callback

    def handle_error(
        self,
        error: Exception,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_action: str | None = None,
    ) -> None:
        """Обрабатывает ошибку и логирует ее.

        Args:
            error: Исключение для обработки
            operation: Название операции, при которой произошла ошибка
            severity: Уровень серьезности ошибки
            recovery_action: Рекомендуемое действие для восстановления

        Пример использования:
            try:
                process_file('example.txt')
            except FileNotFoundError as e:
                error_handler.handle_error(
                    e,
                    'Чтение файла',
                    ErrorSeverity.ERROR,
                    'Проверьте существование файла'
                )
        """
        context = ErrorContext(
            operation=operation,
            details={"error_type": type(error).__name__},
            severity=severity,
            recovery_action=recovery_action,
        )

        if isinstance(error, AppError):
            app_error = error
        else:
            app_error = AppError(str(error), context, error)

        self.log_callback(app_error.format_message(), severity.value)
