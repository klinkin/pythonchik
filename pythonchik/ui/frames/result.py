"""Фрейм для отображения результатов операций.

Этот модуль содержит фрейм для отображения результатов различных операций,
включая текстовый вывод и графики matplotlib.
"""

from typing import Any

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk


class ResultFrame(ctk.CTkFrame):
    """Фрейм для отображения результатов операций в прокручиваемом контейнере."""

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs: dict[str, Any]) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Make content row expandable

        # Create header label
        self.header_label = ctk.CTkLabel(self, text="Результат", font=ctk.CTkFont(size=14, weight="bold"))
        self.header_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Create text display widget
        self.text_display = ctk.CTkTextbox(self, wrap="word")
        self.text_display.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.text_display.grid_remove()
        self._text_after_id = None  # Track scheduled updates

        # Create image display widget
        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.image_label.grid_remove()

        # Create matplotlib figure container
        self.figure_container = ctk.CTkFrame(self)
        self.figure_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.figure_container.grid_remove()
        self.figure_canvas = None

        # Create progress bar and status label
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.grid_remove()

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.status_label.grid_remove()

    def show_text(self, content: str) -> None:
        """Отображение текстового содержимого.

        Аргументы:
            content: Текстовое содержимое для отображения
        """
        if self._text_after_id:
            self.after_cancel(self._text_after_id)
            self._text_after_id = None

        self.image_label.grid_remove()
        self.figure_container.grid_remove()
        self.text_display.grid()
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", content)

    def show_image(self, image_path: str) -> None:
        """Отображение изображения.

        Аргументы:
            image_path: Путь к файлу изображения
        """
        self.text_display.grid_remove()
        self.figure_container.grid_remove()
        self.image_label.grid()

        # Load and display the image
        image = Image.open(image_path)

        # Get frame dimensions
        frame_width = self.winfo_width() - 20  # Account for padding
        frame_height = self.winfo_height() - 20

        # Calculate scaling factors
        width_ratio = frame_width / image.width
        height_ratio = frame_height / image.height
        scale_factor = min(width_ratio, height_ratio)

        # Calculate new dimensions
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)

        # Create CTkImage for proper HighDPI support
        ctk_image = ctk.CTkImage(image, size=(new_width, new_height))
        self.image_label.configure(image=ctk_image)
        self.image_label._image = ctk_image  # Keep a reference to prevent garbage collection

    def show_figure(self, figure: Figure) -> None:
        """Отображение matplotlib figure.

        Аргументы:
            figure: Matplotlib Figure для отображения
        """
        self.text_display.grid_remove()
        self.image_label.grid_remove()
        self.figure_container.grid()

        # Clear previous figure if exists
        if self.figure_canvas is not None:
            self.figure_canvas.get_tk_widget().destroy()

        # Create new canvas
        self.figure_canvas = FigureCanvasTkAgg(figure, master=self.figure_container)
        self.figure_canvas.draw()
        self.figure_canvas.get_tk_widget().pack(fill="both", expand=True)

    def clear(self) -> None:
        """Очистка содержимого фрейма."""
        if self._text_after_id:
            self.after_cancel(self._text_after_id)
            self._text_after_id = None

        self.text_display.delete("1.0", "end")
        self.image_label.configure(image=None)
        if self.figure_canvas is not None:
            self.figure_canvas.get_tk_widget().destroy()
            self.figure_canvas = None

        self.text_display.grid_remove()
        self.image_label.grid_remove()
        self.figure_container.grid_remove()

    def update_progress(self, progress: int, message: str = "") -> None:
        """Update the progress bar and status message.

        Args:
            progress: Progress percentage (0-100)
            message: Optional status message to display
        """

        def _update():
            self.progress_bar.grid()
            self.status_label.grid()
            self.progress_bar.set(progress / 100)
            if message:
                self.status_label.configure(text=message)

        # Schedule the update on the main thread
        self.after(0, _update)

    def reset_progress(self) -> None:
        """Reset the progress indicator to its initial state."""

        def _reset():
            self.progress_bar.grid_remove()
            self.status_label.grid_remove()
            self.progress_bar.set(0)
            self.status_label.configure(text="")

        # Schedule the reset on the main thread
        self.after(0, _reset)
