"""Тесты для функциональности управления настройками.

Этот модуль содержит тесты для проверки корректности работы
менеджера настроек приложения.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from pythonchik.utils.settings import SettingsManager


@pytest.fixture
def settings_dir() -> Generator[Path, None, None]:
    """Создает временную директорию настроек для тестирования.

    Возвращает:
        Generator с путем к временной директории.

    Особенности:
        Автоматически удаляет временную директорию после завершения теста.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def settings_manager(settings_dir: Path) -> SettingsManager:
    """Создает экземпляр SettingsManager для тестирования.

    Аргументы:
        settings_dir: Путь к временной директории настроек

    Возвращает:
        Настроенный экземпляр SettingsManager.
    """
    return SettingsManager(settings_dir)


def test_default_settings(settings_manager: SettingsManager) -> None:
    """Проверяет корректность загрузки настроек по умолчанию.

    Аргументы:
        settings_manager: Тестируемый экземпляр SettingsManager

    Особенности:
        Проверяет наличие и значения всех настроек по умолчанию.
    """
    assert settings_manager.get_theme() == "system"
    assert settings_manager.get_last_directory() == str(Path.home())


def test_save_load_settings(settings_manager: SettingsManager, settings_dir: Path) -> None:
    """Проверяет сохранение и загрузку пользовательских настроек.

    Аргументы:
        settings_manager: Тестируемый экземпляр SettingsManager
        settings_dir: Путь к временной директории настроек

    Особенности:
        Проверяет сохранение и восстановление пользовательских настроек.
    """
    settings_manager.set_theme("dark")
    settings_manager.set_last_directory("/test/path")
    settings_manager.save_settings()

    new_manager = SettingsManager(settings_dir)
    assert new_manager.get_theme() == "dark"
    assert new_manager.get_last_directory() == "/test/path"


def test_theme_settings(settings_manager: SettingsManager) -> None:
    """Проверяет управление настройками темы.

    Аргументы:
        settings_manager: Тестируемый экземпляр SettingsManager

    Особенности:
        Проверяет установку и получение настроек темы интерфейса.
    """
    settings_manager.set_theme("light")
    assert settings_manager.get_theme() == "light"


def test_last_directory(settings_manager: SettingsManager) -> None:
    """Проверяет управление последней использованной директорией.

    Аргументы:
        settings_manager: Тестируемый экземпляр SettingsManager

    Особенности:
        Проверяет сохранение и получение пути последней директории.
    """
    test_path = "/test/last/directory"
    settings_manager.set_last_directory(test_path)
    assert settings_manager.get_last_directory() == test_path


def test_missing_settings(settings_dir: Path) -> None:
    """Проверяет обработку отсутствующих настроек.

    Аргументы:
        settings_dir: Путь к временной директории настроек

    Особенности:
        Проверяет корректность загрузки настроек по умолчанию при отсутствии файла.
    """
    manager = SettingsManager(settings_dir)
    assert manager.get_theme() == "system"


def test_corrupted_settings(settings_dir: Path) -> None:
    """Проверяет обработку поврежденного файла настроек.

    Аргументы:
        settings_dir: Путь к временной директории настроек

    Особенности:
        Проверяет восстановление настроек по умолчанию при повреждении файла.
    """
    settings_file = settings_dir / "settings.json"
    settings_file.write_text("invalid json content")

    manager = SettingsManager(settings_dir)
    assert manager.get_theme() == "system"
    assert manager.get_last_directory() == str(Path.home())


def test_settings_persistence(settings_manager: SettingsManager, settings_dir: Path) -> None:
    """Проверяет сохранение настроек между сессиями.

    Аргументы:
        settings_manager: Тестируемый экземпляр SettingsManager
        settings_dir: Путь к временной директории настроек

    Особенности:
        Проверяет сохранение настроек при создании нового экземпляра менеджера.
    """
    settings_manager.set_theme("dark")
    settings_manager.save_settings()

    another_manager = SettingsManager(settings_dir)
    assert another_manager.get_theme() == "dark"
