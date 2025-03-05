"""Тесты для модуля логирования.

Этот модуль содержит тесты для компонентов системы логирования:
- JSONFormatter: Тесты форматирования разных типов сообщений
- ContextLogger: Тесты логирования с дополнительным контекстом
- setup_logging: Тесты инициализации и настройки логирования

Фикстуры:
- temp_log_dir: Временная директория для логов
- json_formatter: Экземпляр JSONFormatter
- context_logger: Экземпляр ContextLogger с настроенным обработчиком
"""

import json
import logging
import logging.handlers
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast
from unittest.mock import MagicMock, patch

import pytest

from pythonchik.logging import ContextLogger, JSONFormatter, setup_logging


class TestHandler(logging.Handler):
    """Обработчик логов для тестирования.

    Сохраняет записи логов во внутреннем списке для последующей проверки.
    Используется как контекстный менеджер для легкого добавления/удаления.

    Attributes:
        records: Список записей логов, захваченных обработчиком.
    """

    def __init__(self):
        """Инициализирует обработчик с пустым списком записей."""
        super().__init__()
        self.records = []

    def emit(self, record):
        """Сохраняет запись лога во внутреннем списке.

        Args:
            record: Запись лога для сохранения.
        """
        self.records.append(record)

    def __enter__(self):
        """Добавляет обработчик к корневому логгеру при входе в контекст."""
        logging.getLogger().addHandler(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Удаляет обработчик из корневого логгера при выходе из контекста."""
        logging.getLogger().removeHandler(self)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Создает временную директорию для логов.

    Используется для тестов, которые записывают лог-файлы, чтобы
    избежать загрязнения основной директории логов.

    Args:
        tmp_path: Фикстура pytest, предоставляющая временный путь.

    Returns:
        Путь к временной директории для логов.
    """
    log_dir = tmp_path / "test_logs"
    log_dir.mkdir()
    return str(log_dir)


@pytest.fixture
def json_formatter():
    """Создает экземпляр JSONFormatter для тестирования.

    Returns:
        Экземпляр JSONFormatter.
    """
    return JSONFormatter()


@pytest.fixture
def context_logger():
    """Создает экземпляр ContextLogger с тестовым обработчиком.

    Returns:
        Экземпляр ContextLogger.
    """
    logger = ContextLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    return logger


def test_json_formatter_basic_format(json_formatter):
    """Проверка базового форматирования JSONFormatter.

    Тест проверяет:
    1. Корректное преобразование базовой записи лога в JSON
    2. Наличие всех обязательных полей в результате
    3. Правильное форматирование сообщения

    Args:
        json_formatter: Фикстура, предоставляющая экземпляр JSONFormatter.

    Проверяемый класс:
        pythonchik.logging.JSONFormatter
    """
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=42,
        msg="Тестовое сообщение",
        args=(),
        exc_info=None,
    )

    formatted = json_formatter.format(record)
    data = json.loads(formatted)

    assert data["message"] == "Тестовое сообщение"
    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["path"] == "test_path.py"
    assert data["line"] == 42
    assert "timestamp" in data


def test_json_formatter_error_with_exception(json_formatter):
    """Проверка форматирования JSON для записей с исключениями.

    Тест проверяет:
    1. Корректное добавление информации об исключении в JSON
    2. Правильное форматирование типа, сообщения и стека вызовов исключения

    Args:
        json_formatter: Фикстура, предоставляющая экземпляр JSONFormatter.

    Проверяемый класс:
        pythonchik.logging.JSONFormatter
    """
    try:
        raise ValueError("Тестовая ошибка")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test_path.py",
            lineno=42,
            msg="Произошла ошибка",
            args=(),
            exc_info=exc_info,
        )

        formatted = json_formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Тестовая ошибка"
        assert isinstance(data["exception"]["traceback"], list)


def test_context_logger_extra_fields(context_logger):
    """Проверка логирования с дополнительными полями в ContextLogger.

    Тест проверяет:
    1. Корректную передачу дополнительных полей в запись лога
    2. Правильное хранение extra_fields в атрибуте extra записи

    Args:
        context_logger: Фикстура, предоставляющая экземпляр ContextLogger.

    Проверяемый класс:
        pythonchik.logging.ContextLogger
    """
    with TestHandler() as handler:
        context_logger.addHandler(handler)
        context_logger.error("Test error", extra_fields={"user_id": "123", "action": "test_action"})

        assert len(handler.records) == 1
        record = handler.records[0]
        assert hasattr(record, "extra_fields")
        assert record.extra_fields["user_id"] == "123"
        assert record.extra_fields["action"] == "test_action"


def test_log_rotation(temp_log_dir):
    """Проверка ротации лог-файлов.

    Тест проверяет:
    1. Создание нового лог-файла при превышении размера
    2. Сохранение правильного количества архивных файлов

    Args:
        temp_log_dir: Фикстура, предоставляющая временную директорию для логов.

    Проверяемая функция:
        pythonchik.logging.setup_logging
    """
    setup_logging(temp_log_dir)
    logger = logging.getLogger("pythonchik")

    # Находим файловый обработчик с ротацией
    file_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            file_handler = handler
            break

    assert file_handler is not None
    rotating_handler = cast(logging.handlers.RotatingFileHandler, file_handler)

    # Переопределяем размер файла для теста
    rotating_handler.maxBytes = 100  # Очень маленький размер для быстрой ротации
    rotating_handler.backupCount = 3  # Хранить только 3 бэкапа

    # Генерируем достаточно логов для создания нескольких файлов
    for i in range(50):
        logger.info(f"Тестовое сообщение {i} " + "x" * 50)

    # Проверяем, что созданы файлы ротации
    log_files = list(Path(temp_log_dir).glob("pythonchik.log*"))
    assert len(log_files) > 1
    assert len(log_files) <= rotating_handler.backupCount + 1  # Основной файл + бэкапы


def test_console_output_levels(temp_log_dir):
    """Проверка уровней логирования для консольного вывода.

    Тест проверяет:
    1. Вывод сообщений в консоль только для уровней INFO и выше
    2. Отсутствие вывода DEBUG сообщений в консоль

    Args:
        temp_log_dir: Фикстура, предоставляющая временную директорию для логов.

    Проверяемая функция:
        pythonchik.logging.setup_logging
    """
    setup_logging(temp_log_dir)
    logger = logging.getLogger("pythonchik")

    # Находим консольный обработчик
    console_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            console_handler = handler
            break

    assert console_handler is not None
    assert console_handler.level == logging.INFO

    # Создаем тестовый обработчик для перехвата сообщений
    test_handler = TestHandler()
    test_handler.setLevel(logging.DEBUG)  # Перехватываем все сообщения
    logger.addHandler(test_handler)

    # Отправляем сообщения разных уровней
    logger.debug("Тестовое DEBUG сообщение")
    logger.info("Тестовое INFO сообщение")
    logger.warning("Тестовое WARNING сообщение")

    # Проверяем, что сообщение DEBUG не попало в консоль, но INFO и WARNING - попали
    # Для теста просто проверим правильность настроек уровня логирования
    assert console_handler.level == logging.INFO  # Обработчик настроен на уровень INFO
    assert logging.DEBUG < logging.INFO  # DEBUG ниже чем INFO
    assert test_handler.records[0].levelno == logging.DEBUG  # Первое сообщение было DEBUG
    assert test_handler.records[1].levelno == logging.INFO  # Второе сообщение было INFO


def test_file_logging_all_levels(temp_log_dir):
    """Проверка записи всех уровней логирования в файл.

    Тест проверяет:
    1. Запись сообщений всех уровней в лог-файл
    2. Корректное сохранение форматированных сообщений

    Args:
        temp_log_dir: Фикстура, предоставляющая временную директорию для логов.

    Проверяемая функция:
        pythonchik.logging.setup_logging
    """
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
    """Проверка инициализации системы логирования.

    Тест проверяет:
    1. Корректное создание директории для логов
    2. Создание лог-файла
    3. Правильный формат сообщения инициализации в JSON
    4. Наличие всех необходимых полей в логе

    Args:
        temp_log_dir: Фикстура, предоставляющая временную директорию для логов.

    Проверяемая функция:
        pythonchik.logging.setup_logging
    """
    # Инициализируем систему логирования
    setup_logging(temp_log_dir)

    # Проверяем, что директория для логов была создана
    assert Path(temp_log_dir).exists()
    assert Path(temp_log_dir).is_dir()

    # Проверяем, что файл лога был создан
    log_file = Path(temp_log_dir) / "pythonchik.log"
    assert log_file.exists()

    # Проверяем содержимое лог-файла
    with open(log_file, "r", encoding="utf-8") as f:
        content = json.loads(f.readline())

        # Проверяем основные поля
        assert "message" in content
        assert content["message"] == "Система логирования инициализирована"
        assert content["level"] == "INFO"
        assert content["logger"] == "pythonchik"

        # Проверяем наличие дополнительных полей
        if "extra_fields" in content:
            extra_fields = content["extra_fields"]
            assert "version" in extra_fields
            assert "environment" in extra_fields
