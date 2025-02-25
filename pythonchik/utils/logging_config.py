"""Конфигурация логирования для приложения Pythonchik.

Этот модуль настраивает систему логирования Python для записи сообщений
в файл и вывода в консоль, а также интеграции с пользовательским интерфейсом.
"""

import logging
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Настраивает систему логирования."""
    logger = logging.getLogger("pythonchik")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Не передавать логи в корневой логгер

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Файловый лог (ротация при 5MB, хранит 3 старых файла)
    file_handler = RotatingFileHandler("pythonchik.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Консольный лог
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    logging.info("Система логирования инициализирована")
