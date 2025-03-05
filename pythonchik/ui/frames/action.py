"""Фрейм меню действий для управления операциями.

Этот модуль содержит компоненты для управления различными
операциями в приложении Pythonchik.
"""

from collections.abc import Callable
from typing import Any

import customtkinter as ctk


class ActionMenuFrame(ctk.CTkFrame):
    """Фрейм меню действий.

    Этот класс отвечает за отображение и управление кнопками
    и элементами управления для различных операций.
    """

    def __init__(
        self, master: ctk.CTk | ctk.CTkFrame, commands: dict[str, Callable[[], None]], **kwargs: Any
    ) -> None:
        """Инициализация фрейма меню действий.

        Args:
            master: Родительский виджет
            commands: Словарь с командами для кнопок
            **kwargs: Дополнительные аргументы для фрейма
        """
        super().__init__(master, **kwargs)

        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)

        # Сохраняем команды для использования в других методах
        self._commands = commands

        # Создаем все кнопки, но изначально скрываем их
        self._create_json_section()
        self._create_image_section()
        self._create_analysis_section()

        # По умолчанию показываем JSON секцию
        self.show_json_section()

    def _create_json_section(self) -> None:
        """Создание секции JSON операций."""
        self.json_label = ctk.CTkLabel(self, text="JSON Операции", font=ctk.CTkFont(size=16, weight="bold"))

        self.json_buttons = [
            ctk.CTkButton(
                self,
                text="Извлечь адреса",
                command=self._commands.get("extract_addresses"),
            ),
            ctk.CTkButton(
                self,
                text="Проверить координаты",
                command=self._commands.get("check_coordinates"),
            ),
            ctk.CTkButton(
                self,
                text="Извлечь штрих-коды",
                command=self._commands.get("extract_barcodes"),
            ),
            ctk.CTkButton(
                self,
                text="Создать тестовый JSON",
                command=self._commands.get("write_test_json"),
            ),
        ]

    def _create_image_section(self) -> None:
        """Создание секции операций с изображениями."""
        self.image_label = ctk.CTkLabel(
            self,
            text="Операции с изображениями",
            font=ctk.CTkFont(size=16, weight="bold"),
        )

        self.image_buttons = [
            ctk.CTkButton(
                self,
                text="Сжать изображения",
                command=self._commands.get("compress_images"),
            ),
            ctk.CTkButton(
                self,
                text="Конвертировать формат",
                command=self._commands.get("convert_image_format"),
            ),
        ]

    def _create_analysis_section(self) -> None:
        """Создание секции анализа данных."""
        self.analysis_label = ctk.CTkLabel(
            self, text="Анализ данных", font=ctk.CTkFont(size=16, weight="bold")
        )

        self.analysis_buttons = [
            ctk.CTkButton(
                self,
                text="Подсчет предложений",
                command=self._commands.get("count_unique_offers"),
            ),
            ctk.CTkButton(self, text="Сравнить цены", command=self._commands.get("compare_prices")),
        ]

    def _hide_all_sections(self) -> None:
        """Скрыть все секции кнопок."""
        for widget in self.grid_slaves():
            widget.grid_remove()

    def show_json_section(self) -> None:
        """Показать секцию JSON операций."""
        self._hide_all_sections()
        self.json_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        for i, button in enumerate(self.json_buttons, start=1):
            button.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

    def show_image_section(self) -> None:
        """Показать секцию операций с изображениями."""
        self._hide_all_sections()
        self.image_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        for i, button in enumerate(self.image_buttons, start=1):
            button.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

    def show_analysis_section(self) -> None:
        """Показать секцию анализа данных."""
        self._hide_all_sections()
        self.analysis_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        for i, button in enumerate(self.analysis_buttons, start=1):
            button.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

    def set_buttons_state(self, enabled: bool) -> None:
        """Enable or disable all buttons in the menu based on processing state.

        Args:
            enabled (bool): True to enable buttons, False to disable
        """
        for button_list in [self.json_buttons, self.image_buttons, self.analysis_buttons]:
            for button in button_list:
                button.configure(state="normal" if enabled else "disabled")
