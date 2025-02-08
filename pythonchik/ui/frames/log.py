"""Фрейм для отображения логов операций.

Этот модуль предоставляет компонент для отображения и фильтрации
логов операций в приложении Pythonchik.
"""

from datetime import datetime

import customtkinter as ctk


class LogFrame(ctk.CTkFrame):
    """Фрейм для отображения логов с возможностью фильтрации по тегам.

    Этот класс обеспечивает отображение логов операций в прокручиваемой
    области с поддержкой различных уровней логирования (INFO, WARNING, ERROR)
    и возможностью фильтрации по тегам.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs) -> None:
        """Инициализация фрейма логов.

        Аргументы:
            master: Родительский виджет
            **kwargs: Дополнительные аргументы для фрейма
        """
        super().__init__(master, **kwargs)

        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Создание заголовка
        self.header_label = ctk.CTkLabel(
            self, text="Журнал операций", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.header_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Создание кнопки очистки
        self.clear_button = ctk.CTkButton(
            self,
            text="Очистить",
            width=70,
            height=24,
            font=ctk.CTkFont(size=12),
            command=self.clear_log,
        )
        self.clear_button.grid(row=0, column=1, padx=(5, 10), pady=(10, 5), sticky="e")

        # Создание текстовой области для логов
        self.log_text = ctk.CTkTextbox(self, wrap="word")
        self.log_text.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")
        self.log_text.configure(state="disabled")

    def log(self, message: str, level: str = "INFO") -> None:
        """Добавление сообщения в лог.

        Аргументы:
            message: Текст сообщения для логирования
            level: Уровень сообщения (INFO, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.log_text.update()

    def clear_log(self) -> None:
        """Очистка всех записей в логе."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
