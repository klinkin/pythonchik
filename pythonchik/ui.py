"""Модуль пользовательского интерфейса.

Содержит классы и компоненты для создания и управления графическим интерфейсом.
"""

import tkinter as tk
import tkinter.ttk as ttk
from contextlib import contextmanager
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from typing import Callable, List

from pythonchik import config


class ProgressBar:
    """Класс для отображения прогресса выполнения операций.

    Предоставляет интерфейс для обновления и сброса индикатора прогресса.
    """

    def __init__(self, parent: tk.Frame):
        """Инициализация индикатора прогресса.

        Аргументы:
            parent (tk.Frame): Родительский фрейм для размещения прогресс-бара
        """
        self.progress_frame = tk.Frame(parent)
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(self.progress_frame, text="")
        self.progress_label.pack()

    def update(self, value: float, text: str = "") -> None:
        """Обновление значения и текста прогресс-бара.

        Аргументы:
            value (float): Значение прогресса (0-100)
            text (str): Текст для отображения под прогресс-баром
        """
        self.progress_var.set(value)
        self.progress_label.config(text=text)
        self.progress_frame.update()

    def reset(self) -> None:
        """Сброс прогресс-бара в начальное состояние."""
        self.progress_var.set(0)
        self.progress_label.config(text="")
        self.progress_frame.update()


class FileDialog:
    """Класс для работы с диалогами выбора файлов."""

    @staticmethod
    def get_json_files() -> List[str]:
        """Открывает диалог выбора JSON файлов.

        Возвращает:
            List[str]: Список путей к выбранным файлам
        """
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if not files:
            mb.showinfo("Информация", "Выберите файл(ы) JSON")
        return list(files)

    @staticmethod
    def get_image_files() -> List[str]:
        """Открывает диалог выбора файлов изображений.

        Возвращает:
            List[str]: Список путей к выбранным файлам
        """
        files = fd.askopenfilenames(filetypes=config.IMAGE_FILE_TYPES)
        if not files:
            mb.showinfo("Информация", "Выберите изображение(я)")
        return list(files)


class BaseWindow:
    """Базовый класс для окон приложения.

    Предоставляет общую функциональность для всех окон.
    """

    def __init__(self):
        """Инициализация базового окна."""
        if isinstance(self, tk.Tk):
            super().__init__()

    def setup_button(self, button: ttk.Button, tooltip: str = "") -> None:
        """Настраивает кнопку с подсказкой.

        Аргументы:
            button (ttk.Button): Кнопка для настройки
            tooltip (str): Текст всплывающей подсказки
        """
        if tooltip:
            self._create_tooltip(button, tooltip)

    def _create_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Создает всплывающую подсказку для виджета.

        Аргументы:
            widget (tk.Widget): Виджет для добавления подсказки
            text (str): Текст подсказки
        """
        tooltip = tk.Label(
            widget, text=text, background="#FFE4B5", relief="solid", borderwidth=1
        )
        tooltip.pack_forget()

        def show_tooltip(event):
            tooltip.pack()
            tooltip.place(x=event.x + 10, y=event.y + 10)

        def hide_tooltip(event):
            tooltip.pack_forget()
            tooltip.place_forget()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    @contextmanager
    def cleanup_context(self):
        """Контекстный менеджер для обработки очистки.

        Обрабатывает сброс прогресса и закрытие окна после выполнения операции.
        """
        try:
            yield
        finally:
            if hasattr(self, "progress_bar"):
                self.progress_bar.reset()
            if hasattr(self, "quit"):
                self.quit()
