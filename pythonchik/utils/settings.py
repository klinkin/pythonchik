"""Модуль управления настройками приложения.

Обеспечивает сохранение и загрузку пользовательских настроек приложения,
включая тему интерфейса, последнюю использованную директорию и другие
пользовательские предпочтения. Настройки сохраняются в формате JSON
в файле конфигурации и сохраняются между запусками приложения.

Классы:
    SettingsManager: Основной класс для работы с настройками приложения.

Примеры:
    >>> from pythonchik.utils.settings import SettingsManager
    >>> settings = SettingsManager()
    >>> current_theme = settings.get_theme()
    >>> settings.set_theme("dark")
    >>> last_dir = settings.get_last_directory()
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pythonchik.config import SETTINGS_FILE


class SettingsManager:
    """Менеджер настроек приложения.

    Обеспечивает интерфейс для работы с пользовательскими настройками, включая
    их загрузку из файла при инициализации, сохранение изменений и предоставление
    значений настроек по запросу. Настройки сохраняются в JSON файле в директории
    пользователя.

    Attributes:
        settings_file (Path): Путь к файлу с настройками.
        settings (Dict[str, Any]): Словарь с текущими настройками приложения.

    Examples:
        >>> # Создание менеджера настроек с настройками по умолчанию
        >>> settings = SettingsManager()
        >>>
        >>> # Получение и изменение темы интерфейса
        >>> current_theme = settings.get_theme()
        >>> settings.set_theme("dark")  # Автоматически сохраняет изменения
        >>>
        >>> # Получение произвольной настройки
        >>> auto_save = settings.get_setting("auto_save")
        >>>
        >>> # Установка пользовательской настройки
        >>> settings.set_setting("custom_setting", "value")
    """

    def __init__(self, settings_dir: Optional[Path] = None) -> None:
        """Инициализирует менеджер настроек.

        Создаёт необходимые директории для хранения настроек, если они не существуют,
        и загружает существующие настройки из файла. Если файл настроек отсутствует
        или повреждён, используются значения по умолчанию.

        Args:
            settings_dir: Опциональный путь к директории для хранения настроек.
                Если не указан, используется путь из config.py.
        """
        if settings_dir is None:
            self.settings_file = SETTINGS_FILE
        else:
            self.settings_file = settings_dir / "settings.json"
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings: Dict[str, Any] = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла.

        Читает настройки из JSON файла. Если файл не существует или содержит
        некорректные данные, возвращает настройки по умолчанию.

        Returns:
            Словарь с загруженными настройками или настройками по умолчанию.
        """
        if not self.settings_file.exists():
            return self._get_default_settings()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Возвращает настройки по умолчанию.

        Создаёт словарь с базовыми настройками, используемыми при первом запуске
        приложения или в случае повреждения файла настроек.

        Returns:
            Словарь с настройками по умолчанию.
        """
        return {
            "theme": "system",
            "last_directory": str(Path.home()),
            "auto_save": True,
            "show_tooltips": True,
        }

    def save_settings(self) -> None:
        """Сохраняет текущие настройки в файл.

        Записывает содержимое словаря настроек в JSON файл с форматированием
        для удобства чтения и поддержкой кириллицы.
        """
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get_setting(self, key: str) -> Optional[Any]:
        """Получает значение настройки по ключу.

        Args:
            key: Ключ (имя) настройки.

        Returns:
            Значение настройки или None, если настройка не найдена.
        """
        return self.settings.get(key)

    def set_setting(self, key: str, value: Any) -> None:
        """Устанавливает значение настройки и сохраняет изменения в файл.

        Args:
            key: Ключ (имя) настройки.
            value: Новое значение настройки.
        """
        self.settings[key] = value
        self.save_settings()

    def get_theme(self) -> str:
        """Получает текущую тему интерфейса.

        Returns:
            Название текущей темы или "system" если не задано.
        """
        return self.get_setting("theme") or "system"

    def set_theme(self, theme: str) -> None:
        """Устанавливает тему интерфейса.

        Args:
            theme: Название темы ("light", "dark", "system").
        """
        self.set_setting("theme", theme)

    def get_last_directory(self) -> str:
        """Получает последнюю использованную директорию.

        Returns:
            Путь к последней использованной директории или домашнюю директорию.
        """
        return self.get_setting("last_directory") or str(Path.home())

    def set_last_directory(self, directory: str) -> None:
        """Устанавливает последнюю использованную директорию.

        Args:
            directory: Путь к директории.
        """
        self.set_setting("last_directory", directory)
