"""Компоненты навигации для современного пользовательского интерфейса.

Этот модуль содержит фрейм навигации и связанные компоненты интерфейса
для современного интерфейса приложения Pythonchik.
"""

import os
from collections.abc import Callable
from typing import Any

import customtkinter as ctk
from PIL import Image


class SideBarFrame(ctk.CTkFrame):
    """Фрейм навигации, содержащий боковое меню и селектор темы.

    Этот класс инкапсулирует все компоненты пользовательского интерфейса,
    связанные с навигацией, включая логотип, кнопки навигации и меню выбора темы.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs: Any) -> None:
        """Инициализация фрейма навигации.

        Аргументы:
            master: Родительский виджет
            **kwargs: Дополнительные аргументы для фрейма
        """
        super().__init__(master, corner_radius=0, **kwargs)

        # Настройка сетки
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid(sticky="nsew")

        # Загрузка иконок
        self.load_icons()

        # Настройка компонентов интерфейса
        self.setup_logo()
        self.setup_navigation_buttons()
        self.setup_theme_selector()

    def load_icons(self) -> None:
        """Загрузка всех необходимых иконок для фрейма навигации."""
        image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")

        # Load and configure logo image with higher resolution
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(os.path.join(image_path, "icon_edadeal_white.png")).resize(
                (52, 52), Image.Resampling.LANCZOS
            ),
            dark_image=Image.open(os.path.join(image_path, "icon_edadeal_green.png")).resize(
                (52, 52), Image.Resampling.LANCZOS
            ),
            size=(26, 26),
        )

        # Load and configure navigation icons with higher resolution
        self.json_processing_button_icons = ctk.CTkImage(
            light_image=Image.open(os.path.join(image_path, "home_dark.png")).resize(
                (32, 32), Image.Resampling.LANCZOS
            ),
            dark_image=Image.open(os.path.join(image_path, "home_light.png")).resize(
                (32, 32), Image.Resampling.LANCZOS
            ),
            size=(16, 16),
        )

        self.image_processing_button_icon = ctk.CTkImage(
            Image.open(os.path.join(image_path, "image_icon_light.png")).resize(
                (32, 32), Image.Resampling.LANCZOS
            ),
            size=(16, 16),
        )

        self.analysis_button_icon = ctk.CTkImage(
            light_image=Image.open(os.path.join(image_path, "chat_dark.png")).resize(
                (32, 32), Image.Resampling.LANCZOS
            ),
            dark_image=Image.open(os.path.join(image_path, "chat_light.png")).resize(
                (32, 32), Image.Resampling.LANCZOS
            ),
            size=(16, 16),
        )

    def setup_logo(self) -> None:
        """Настройка логотипа и заголовка приложения."""
        self.logo_label = ctk.CTkLabel(
            self,
            text="  Pythonchik",
            image=self.logo_image,
            compound="left",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

    def setup_navigation_buttons(self) -> None:
        """Настройка кнопок навигации для разных разделов."""

        self.json_button = self._create_nav_button(
            "Работа с JSON",
            self.json_processing_button_icons,
            row=1,
            tooltip="Операции с JSON файлами",
        )

        self.image_button = self._create_nav_button(
            "Работа с изображениями",
            self.image_processing_button_icon,
            row=2,
            tooltip="Обработка и конвертация изображений",
        )

        self.analysis_button = self._create_nav_button(
            "Анализ данных",
            self.analysis_button_icon,
            row=3,
            tooltip="Аналитика и статистика",
        )

    def _create_nav_button(
        self, text: str, image: ctk.CTkImage, row: int, tooltip: str | None = None
    ) -> ctk.CTkButton:
        """Создание кнопки навигации с единым стилем.

        Аргументы:
            text: Текст кнопки
            image: Иконка кнопки
            row: Позиция в сетке (строка)
            tooltip: Подсказка при наведении (опционально)

        Возвращает:
            CTkButton: Созданная кнопка навигации
        """
        button = ctk.CTkButton(
            self,
            corner_radius=0,
            height=45,
            border_spacing=15,
            text=text,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            image=image,
            anchor="w",
            compound="left",
            font=ctk.CTkFont(size=14),
        )
        button.grid(row=row, column=0, sticky="ew")
        return button

    def setup_theme_selector(self) -> None:
        """Настройка выпадающего меню выбора темы."""
        self.appearance_mode_menu = ctk.CTkOptionMenu(self, values=["Светлая", "Тёмная", "Системная"])
        self.appearance_mode_menu.grid(row=6, column=0, padx=20, pady=20, sticky="s")
        self.appearance_mode_menu.set("Тёмная")

    def set_button_commands(
        self,
        json_command: Callable[[], None],
        image_command: Callable[[], None],
        analysis_command: Callable[[], None],
        theme_command: Callable[[str], None],
    ) -> None:
        """Установка функций обратного вызова для всех кнопок навигации.

        Аргументы:
            json_command: Обработчик для кнопки операций с JSON
            image_command: Обработчик для кнопки операций с изображениями
            analysis_command: Обработчик для кнопки анализа
            theme_command: Обработчик для селектора темы
        """
        self.json_button.configure(command=json_command)
        self.image_button.configure(command=image_command)
        self.analysis_button.configure(command=analysis_command)
        self.appearance_mode_menu.configure(command=theme_command)

    def update_selected_tab(self, selected_name: str) -> None:
        """Обновление визуального состояния кнопок навигации на основе выбора.

        Аргументы:
            selected_name: Имя выбранной вкладки ('json', 'image' или 'analysis')
        """
        self.json_button.configure(
            fg_color=("gray75", "gray25") if selected_name == "json" else "transparent"
        )
        self.image_button.configure(
            fg_color=("gray75", "gray25") if selected_name == "image" else "transparent"
        )
        self.analysis_button.configure(
            fg_color=(("gray75", "gray25") if selected_name == "analysis" else "transparent")
        )
