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
        super().__init__(master, **kwargs)

        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._text_after_id = None  # Track scheduled updates

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
        self.log_text.configure(state="disabled", font=ctk.CTkFont(size=12))

    def log(self, message: str, level: str = "INFO") -> None:
        if self._text_after_id:
            self.after_cancel(self._text_after_id)
            self._text_after_id = None

        timestamp = datetime.now().strftime("%H:%M:%S")
        level_colors = {
            "INFO": ("gray90", "gray90"),
            "WARNING": ("#FFA500", "#FFA500"),  # Orange for warnings
            "ERROR": ("#FF0000", "#FF0000"),  # Red for errors
        }

        log_entry = f"[{timestamp}] [{level}] "
        self.log_text._textbox.configure(state="normal")
        self.log_text.insert("end", log_entry)
        color = level_colors.get(level, ("gray90", "gray90"))
        self.log_text.insert("end", f"{message}\n")

        # Add separator only if this is a new operation start
        if message.startswith("Начало") or message.startswith("Процесс завершен"):
            self.log_text.insert("end", "─ ─" * 20 + "\n")

        self.log_text.see("end")
        self.log_text._textbox.configure(state="disabled")

    def get_log(self) -> str:
        """Получить содержимое лога.

        Returns:
            str: Текущее содержимое лога
        """
        self.log_text.configure(state="normal")
        log_content = self.log_text.get("1.0", "end-1c")
        self.log_text.configure(state="disabled")
        return log_content

    def clear_log(self) -> None:
        if self._text_after_id:
            self.after_cancel(self._text_after_id)
            self._text_after_id = None

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
