"""Фрейм для отображения результатов операций.

Этот модуль содержит фрейм для отображения результатов различных операций,
включая текстовый вывод и графики matplotlib.
"""

from typing import Any

import customtkinter as ctk
from PIL import Image, ImageTk


class ResultFrame(ctk.CTkFrame):
    """Фрейм для отображения результатов операций в прокручиваемом контейнере."""

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs: dict[str, Any]) -> None:
        super().__init__(master, corner_radius=0, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Make row 0 expandable

        # Create text display widget
        self.text_display = ctk.CTkTextbox(self, wrap="word")
        self.text_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.text_display.grid_remove()

        # Create image display widget
        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.image_label.grid_remove()

        # Create progress bar and status label
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.grid_remove()

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.status_label.grid_remove()

    def show_text(self, content: str) -> None:
        """Отображение текстового содержимого.

        Аргументы:
            content: Текстовое содержимое для отображения
        """
        self.image_label.grid_remove()
        self.text_display.grid()
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", content)

    def show_image(self, image_path: str) -> None:
        """Отображение изображения.

        Аргументы:
            image_path: Путь к файлу изображения
        """
        self.text_display.grid_remove()
        self.image_label.grid()

        # Load and display the image
        image = Image.open(image_path)
        photo = ImageTk.PhotoImage(image)
        self.image_label.configure(image=photo)
        self.image_label._image = photo  # Keep a reference to prevent garbage collection

    def clear(self) -> None:
        """Очистка содержимого фрейма."""
        self.text_display.delete("1.0", "end")
        self.image_label.configure(image=None)
        self.text_display.grid_remove()
        self.image_label.grid_remove()

    def update_progress(self, progress: int, message: str = "") -> None:
        """Update the progress bar and status message.

        Args:
            progress: Progress percentage (0-100)
            message: Optional status message to display
        """
        self.progress_bar.grid()
        self.status_label.grid()
        self.progress_bar.set(progress / 100)
        if message:
            self.status_label.configure(text=message)

    def reset_progress(self) -> None:
        """Reset the progress indicator to its initial state."""
        self.progress_bar.grid_remove()
        self.status_label.grid_remove()
        self.progress_bar.set(0)
        self.status_label.configure(text="")
