"""Конфигурация логирования для приложения Pythonchik.

Модуль предоставляет расширенный функционал логирования:
- Структурированное логирование в JSON формате
- Ротацию логов с настраиваемыми параметрами
- Расширенный контекст для ошибок
- Дополнительные поля для обогащения логов метаданными

Модуль содержит:
- JSONFormatter: Форматтер для вывода логов в JSON формате
- ContextLogger: Расширенный логгер с поддержкой дополнительных полей
- setup_logging: Функция настройки системы логирования

Примеры:
    Базовая настройка логирования:

    >>> from pythonchik.logging import setup_logging
    >>> setup_logging("/path/to/logs")

    Использование расширенного логгера:

    >>> logger = logging.getLogger("pythonchik")
    >>> logger.info("Важное сообщение", extra_fields={"user_id": 123})
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Форматтер для структурированного вывода логов в JSON формате.

    Преобразует стандартные записи логов в структурированный JSON-формат,
    добавляя дополнительные поля для анализа и поиска.

    Attributes:
        default_fields (list): Список стандартных полей, включаемых в каждую запись.

    Note:
        Формат JSON-лога включает следующие поля:
        - timestamp: Временная метка в ISO формате
        - message: Текст сообщения
        - level: Уровень логирования (INFO, ERROR, etc.)
        - logger: Имя логгера
        - path: Путь к файлу, из которого вызван лог
        - line: Номер строки в файле
        - function: Имя функции
        - exception: Информация об исключении (для ERROR и выше)
        - extra_fields: Дополнительные пользовательские поля
    """

    def __init__(self) -> None:
        """Инициализирует форматтер с настройками по умолчанию."""
        super().__init__()
        self.default_fields = ["name", "levelname", "pathname", "lineno"]

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON.

        Преобразует стандартную запись лога в структурированный
        JSON объект с дополнительными полями.

        Args:
            record: Запись лога для форматирования.

        Returns:
            JSON-строка, представляющая форматированную запись лога.

        Examples:
            >>> formatter = JSONFormatter()
            >>> formatted_log = formatter.format(log_record)
            >>> print(formatted_log)
            {"timestamp": "2023-03-06T21:34:57", "message": "Тестовое сообщение", ...}
        """
        message_dict = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "message": record.getMessage(),
            "level": record.levelname,
            "logger": record.name,
            "path": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Добавляем расширенный контекст для ошибок
        if record.levelno >= logging.ERROR and record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            message_dict["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value) if exc_value else "",
                "traceback": (
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                    if all([exc_type, exc_value, exc_tb])
                    else []
                ),
            }

        # Добавляем дополнительные поля из extra
        extra = getattr(record, "extra", None)
        if extra and isinstance(extra, dict) and "extra_fields" in extra:
            message_dict["extra_fields"] = extra["extra_fields"]

        return json.dumps(message_dict, ensure_ascii=False)


class ContextLogger(logging.Logger):
    """Расширенный логгер с поддержкой контекста.

    Добавляет возможность логирования с дополнительными полями
    контекста для обогащения записей лога метаданными.

    Attributes:
        name (str): Имя логгера.
        level (int): Уровень логирования.

    Note:
        Этот логгер расширяет стандартный Logger, добавляя параметр
        extra_fields для всех методов логирования.
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        """Инициализирует логгер с указанным именем и уровнем.

        Args:
            name: Имя логгера.
            level: Уровень логирования. По умолчанию NOTSET.
        """
        super().__init__(name, level)

    def _log_with_context(
        self,
        level: int,
        msg: str,
        args: tuple[Any, ...] = (),
        extra_fields: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Внутренний метод для логирования с дополнительным контекстом.

        Добавляет дополнительные поля в словарь extra перед передачей
        записи базовому логгеру.

        Args:
            level: Уровень логирования.
            msg: Сообщение лога.
            args: Аргументы для форматирования сообщения.
            extra_fields: Дополнительные поля контекста для записи лога.
            **kwargs: Дополнительные аргументы для базового метода _log.
        """
        if extra_fields:
            if "extra" not in kwargs:
                kwargs["extra"] = {}
            kwargs["extra"]["extra_fields"] = extra_fields
        super()._log(level, msg, args, **kwargs)

    def info(
        self, msg: object, *args: object, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование информационного сообщения с дополнительным контекстом.

        Args:
            msg: Сообщение для логирования.
            *args: Аргументы для форматирования сообщения.
            extra_fields: Дополнительные поля контекста.
            **kwargs: Дополнительные аргументы для базового метода.

        Examples:
            >>> logger = logging.getLogger("pythonchik")
            >>> logger.info("Файл успешно обработан", extra_fields={"file_size": 1024, "duration": 0.5})
        """
        self._log_with_context(logging.INFO, str(msg), args, extra_fields, **kwargs)

    def error(
        self, msg: object, *args: object, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование ошибки с дополнительным контекстом.

        Args:
            msg: Сообщение для логирования.
            *args: Аргументы для форматирования сообщения.
            extra_fields: Дополнительные поля контекста.
            **kwargs: Дополнительные аргументы для базового метода.

        Examples:
            >>> logger = logging.getLogger("pythonchik")
            >>> try:
            ...     # какой-то код
            ... except ValueError as e:
            ...     logger.error("Ошибка обработки", extra_fields={"error_code": 500})
        """
        self._log_with_context(logging.ERROR, str(msg), args, extra_fields, **kwargs)

    def warning(
        self, msg: object, *args: object, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование предупреждения с дополнительным контекстом.

        Args:
            msg: Сообщение для логирования.
            *args: Аргументы для форматирования сообщения.
            extra_fields: Дополнительные поля контекста.
            **kwargs: Дополнительные аргументы для базового метода.
        """
        self._log_with_context(logging.WARNING, str(msg), args, extra_fields, **kwargs)

    def debug(
        self, msg: object, *args: object, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование отладочного сообщения с дополнительным контекстом.

        Args:
            msg: Сообщение для логирования.
            *args: Аргументы для форматирования сообщения.
            extra_fields: Дополнительные поля контекста.
            **kwargs: Дополнительные аргументы для базового метода.
        """
        self._log_with_context(logging.DEBUG, str(msg), args, extra_fields, **kwargs)


def setup_logging(log_dir: str = "logs") -> None:
    """Настраивает систему логирования.

    Создает директорию для логов, настраивает логгеры и обработчики
    для файлового и консольного вывода.

    Args:
        log_dir: Директория для хранения лог-файлов. По умолчанию "logs".
            Если директория не существует, она будет создана.

    Returns:
        None

    Raises:
        PermissionError: Если нет прав на создание директории или файлов логов.

    Examples:
        >>> setup_logging("/var/log/pythonchik")
        >>> setup_logging()  # Используется директория "logs" по умолчанию
    """
    # Создаём директорию для логов если её нет
    os.makedirs(log_dir, exist_ok=True)

    # Регистрируем наш кастомный логгер
    logging.setLoggerClass(ContextLogger)
    logger = logging.getLogger("pythonchik")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # JSON форматтер для файлового хендлера
    json_formatter = JSONFormatter()

    # Обычный форматтер для консоли
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Файловый лог с ротацией (10MB, хранит 5 файлов)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "pythonchik.log"),
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8",  # 10MB
    )
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Консольный лог
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)  # Консоль только INFO и выше
    logger.addHandler(console_handler)

    logger.info(
        "Система логирования инициализирована",
        extra={"version": "1.0", "environment": os.getenv("ENV", "development")},
    )
