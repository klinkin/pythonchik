"""Модуль управления настройками приложения.

Обеспечивает сохранение и загрузку пользовательских настроек,
включая тему интерфейса и другие предпочтения.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class SettingsManager:
    """Менеджер настроек приложения.

    Управляет сохранением и загрузкой пользовательских настроек,
    обеспечивая персистентность между сессиями.
    """

    def __init__(self) -> None:
        self.settings_file = Path.home() / ".pythonchik" / "settings.json"
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings: Dict[str, Any] = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла."""
        if not self.settings_file.exists():
            return self._get_default_settings()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Возвращает настройки по умолчанию."""
        return {"theme": "dark", "last_directory": str(Path.home()), "auto_save": True, "show_tooltips": True}

    def save_settings(self) -> None:
        """Сохраняет текущие настройки в файл."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get_setting(self, key: str) -> Optional[Any]:
        """Получает значение настройки по ключу."""
        return self.settings.get(key)

    def set_setting(self, key: str, value: Any) -> None:
        """Устанавливает значение настройки."""
        self.settings[key] = value
        self.save_settings()

    def get_theme(self) -> str:
        """Получает текущую тему интерфейса."""
        return self.get_setting("theme") or "dark"

    def set_theme(self, theme: str) -> None:
        """Устанавливает тему интерфейса."""
        self.set_setting("theme", theme)

    def get_last_directory(self) -> str:
        """Получает последнюю использованную директорию."""
        return self.get_setting("last_directory") or str(Path.home())

    def set_last_directory(self, directory: str) -> None:
        """Устанавливает последнюю использованную директорию."""
        self.set_setting("last_directory", directory)
