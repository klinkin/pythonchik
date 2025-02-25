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

    Returns:
        Generator с путем к временной директории.

    Note:
        Автоматически удаляет временную директорию после завершения теста.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def settings_manager(settings_dir: Path) -> SettingsManager:
    """Создает экземпляр SettingsManager для тестирования.

    Args:
        settings_dir: Путь к временной директории настроек

    Returns:
        Настроенный экземпляр SettingsManager.
    """
    return SettingsManager(settings_dir)


def test_default_settings(settings_manager: SettingsManager) -> None:
    """Проверяет корректность загрузки настроек по умолчанию.

    Args:
        settings_manager: Тестируемый экземпляр SettingsManager

    Note:
        Проверяет наличие и значения всех настроек по умолчанию.
    """
    assert settings_manager.get_theme() == "system"
    assert settings_manager.get_last_directory() == str(Path.home())


def test_save_load_settings(settings_manager: SettingsManager, settings_dir: Path) -> None:
    """Проверяет сохранение и загрузку пользовательских настроек.

    Args:
        settings_manager: Тестируемый экземпляр SettingsManager
        settings_dir: Путь к временной директории настроек

    Note:
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

    Args:
        settings_manager: Тестируемый экземпляр SettingsManager

    Note:
        Проверяет установку и получение настроек темы интерфейса.
    """
    settings_manager.set_theme("light")
    assert settings_manager.get_theme() == "light"


def test_last_directory(settings_manager: SettingsManager) -> None:
    """Проверяет управление последней использованной директорией.

    Args:
        settings_manager: Тестируемый экземпляр SettingsManager

    Note:
        Проверяет сохранение и получение пути последней директории.
    """
    test_path = "/test/last/directory"
    settings_manager.set_last_directory(test_path)
    assert settings_manager.get_last_directory() == test_path


def test_missing_settings(settings_dir: Path) -> None:
    """Проверяет обработку отсутствующих настроек.

    Args:
        settings_dir: Путь к временной директории настроек

    Note:
        Проверяет корректность загрузки настроек по умолчанию при отсутствии файла.
    """
    manager = SettingsManager(settings_dir)
    assert manager.get_theme() == "system"


def test_corrupted_settings(settings_dir: Path) -> None:
    """Проверяет обработку поврежденного файла настроек.

    Args:
        settings_dir: Путь к временной директории настроек

    Note:
        Проверяет восстановление настроек по умолчанию при повреждении файла.
    """
    settings_file = settings_dir / "settings.json"
    settings_file.write_text("invalid json content")

    manager = SettingsManager(settings_dir)
    assert manager.get_theme() == "system"
    assert manager.get_last_directory() == str(Path.home())


def test_settings_persistence(settings_manager: SettingsManager, settings_dir: Path) -> None:
    """Проверяет сохранение настроек между сессиями.

    Args:
        settings_manager: Тестируемый экземпляр SettingsManager
        settings_dir: Путь к временной директории настроек

    Note:
        Проверяет сохранение настроек при создании нового экземпляра менеджера.
    """
    settings_manager.set_theme("dark")
    settings_manager.save_settings()

    another_manager = SettingsManager(settings_dir)
    assert another_manager.get_theme() == "dark"
