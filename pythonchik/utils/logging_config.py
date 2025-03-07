"""Конфигурация логирования для приложения Pythonchik.

Этот модуль настраивает систему логирования Python для записи сообщений
в файл и вывода в консоль, а также интеграции с пользовательским интерфейсом.

Поддерживает:
- Структурированное логирование в JSON формате
- Ротацию логов с настраиваемыми параметрами
- Расширенный контекст для ошибок
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
    """Форматтер для структурированного вывода логов в JSON формате."""

    def __init__(self) -> None:
        super().__init__()
        self.default_fields = ["name", "levelname", "pathname", "lineno"]

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON."""
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
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
            }

        # Добавляем дополнительные поля из extra
        if hasattr(record, "extra_fields"):
            message_dict["extra_fields"] = record.extra_fields

        return json.dumps(message_dict, ensure_ascii=False)


class ContextLogger(logging.Logger):
    """Расширенный логгер с поддержкой контекста."""

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)

    def _log_with_context(
        self,
        level: int,
        msg: str,
        args: tuple = (),
        extra_fields: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        if extra_fields:
            if "extra" not in kwargs:
                kwargs["extra"] = {}
            kwargs["extra"]["extra_fields"] = extra_fields
        super()._log(level, msg, args, **kwargs)

    def info(
        self, msg: str, *args: Any, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование информационного сообщения с дополнительным контекстом."""
        self._log_with_context(logging.INFO, msg, args, extra_fields, **kwargs)

    def error(
        self, msg: str, *args: Any, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование ошибки с дополнительным контекстом."""
        self._log_with_context(logging.ERROR, msg, args, extra_fields, **kwargs)

    def warning(
        self, msg: str, *args: Any, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование предупреждения с дополнительным контекстом."""
        self._log_with_context(logging.WARNING, msg, args, extra_fields, **kwargs)

    def debug(
        self, msg: str, *args: Any, extra_fields: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Логирование отладочного сообщения с дополнительным контекстом."""
        self._log_with_context(logging.DEBUG, msg, args, extra_fields, **kwargs)


def setup_logging(log_dir: str = "logs") -> None:
    """Настраивает систему логирования.

    Args:
        log_dir: Директория для хранения лог-файлов
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
    console_handler.setLevel(logging.DEBUG)  # Консоль только INFO и выше
    logger.addHandler(console_handler)

    logger.info(
        "Система логирования инициализирована",
        extra_fields={"version": "1.0", "environment": os.getenv("ENV", "development")},
    )
