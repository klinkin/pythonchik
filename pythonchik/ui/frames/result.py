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

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kwargs: Any) -> None:
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

        # Create progress bar and state label
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.grid_remove()

        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.progress_label.grid_remove()

    def show_text(self, content: str) -> None:
        """Отображение текстового содержимого.

        Args:
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

        Args:
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

        Args:
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
        """Update the progress bar and progress message.

        Args:
            progress: Progress percentage (0-100)
            message: Optional message to display
        """

        def _update():
            self.progress_bar.grid()
            self.progress_label.grid()
            self.progress_bar.set(progress / 100)
            if message:
                self.progress_label.configure(text=message)

        # Schedule the update on the main thread
        self.after(0, _update)

    def reset_progress(self) -> None:
        """Reset the progress indicator to its initial state."""

        def _reset():
            self.progress_bar.grid_remove()
            self.progress_label.grid_remove()
            self.progress_bar.set(0)
            self.progress_label.configure(text="")

        # Schedule the reset on the main thread
        self.after(0, _reset)

    def show_metrics(self) -> None:
        """Отображает метрики производительности приложения.

        Собирает и форматирует метрики из коллектора метрик и отображает их
        в текстовом виде в фрейме результатов.
        """
        try:
            from pythonchik.utils.metrics import MetricsCollector

            # Попытка получить метрики из файла или другого источника
            try:
                # Пытаемся загрузить метрики из файла сохраненных метрик
                import json
                from pathlib import Path

                metrics_file = Path.home() / ".pythonchik" / "metrics.json"
                if metrics_file.exists():
                    with open(metrics_file, "r") as f:
                        metrics = json.load(f)
                else:
                    # Если файл не существует, создадим пустые метрики
                    metrics = {"timings": {}, "counters": {}}
            except (ImportError, FileNotFoundError, json.JSONDecodeError) as e:
                # В случае ошибки создаем пустые метрики
                metrics = {"timings": {}, "counters": {}}

            # Форматируем метрики в текст
            text = self._format_metrics(metrics)

            # Отображаем метрики
            self.show_text(text)

        except Exception as e:
            import traceback

            error_text = f"Ошибка при получении метрик: {str(e)}\n\n{traceback.format_exc()}"
            self.show_text(error_text)

    def _format_metrics(self, metrics):
        """Форматирует метрики в текстовый вид.

        Args:
            metrics: Словарь с метриками от MetricsCollector.

        Returns:
            Отформатированный текст с метриками.
        """
        text = "МЕТРИКИ ПРОИЗВОДИТЕЛЬНОСТИ ПРИЛОЖЕНИЯ\n"
        text += "====================================\n\n"

        # Секция счетчиков
        text += "СЧЕТЧИКИ ОПЕРАЦИЙ:\n"
        text += "-------------------\n"
        if "counters" in metrics and metrics["counters"]:
            # Отбираем и сортируем ключевые счетчики
            counters = metrics["counters"]
            important_counters = {
                k: v
                for k, v in counters.items()
                if k
                in [
                    "tasks_added",
                    "tasks_completed",
                    "tasks_interrupted",
                    "task_errors",
                    "start_calls",
                    "add_task_calls",
                ]
            }

            if important_counters:
                # Определяем максимальную длину названия для выравнивания
                max_name_length = max(len(name) for name in important_counters.keys())

                # Форматируем каждый счетчик
                for name, value in sorted(important_counters.items()):
                    text += f"{name.ljust(max_name_length)} : {value}\n"
            else:
                text += "Нет данных о счетчиках операций\n"
        else:
            text += "Нет данных о счетчиках операций\n"

        text += "\n"

        # Секция времени выполнения
        text += "ВРЕМЯ ВЫПОЛНЕНИЯ ЗАДАЧ (в секундах):\n"
        text += "------------------------------------\n"
        if "timings" in metrics and metrics["timings"]:
            # Извлекаем данные о времени выполнения
            timings = metrics["timings"]

            # Фильтруем и сортируем метрики времени
            task_times = {}
            for name, metric in timings.items():
                if name.startswith("task_") or name == "task_execution" or name == "core_uptime":
                    task_times[name] = metric

            if task_times:
                # Определяем максимальную длину названия для выравнивания
                max_name_length = max(len(name) for name in task_times.keys())

                # Заголовок таблицы
                text += f"{'Операция'.ljust(max_name_length)} | {'Вызовы':<7} | {'Мин (с)':<8} | {'Сред (с)':<8} | {'Макс (с)':<8} | {'Всего (с)':<9}\n"
                text += "-" * (max_name_length + 51) + "\n"

                # Данные таблицы
                for name, metric in sorted(task_times.items()):
                    count = metric.get("count", 0)
                    min_time = metric.get("min_time", 0)
                    avg_time = metric.get("avg_time", 0)
                    max_time = metric.get("max_time", 0)
                    total_time = metric.get("total_time", 0)

                    # Форматируем до 4 знаков после запятой
                    text += f"{name.ljust(max_name_length)} | {count:<7} | {min_time:<8.4f} | {avg_time:<8.4f} | {max_time:<8.4f} | {total_time:<9.4f}\n"
            else:
                text += "Нет данных о времени выполнения задач\n"
        else:
            text += "Нет данных о времени выполнения задач\n"

        # Если есть другие интересные метрики, их можно добавить здесь
        if "timings" in metrics and "core_uptime" in metrics["timings"]:
            text += "\n"
            text += "ОБЩАЯ ИНФОРМАЦИЯ:\n"
            text += "----------------\n"
            core_uptime = metrics["timings"]["core_uptime"]
            if isinstance(core_uptime, dict) and "total_time" in core_uptime:
                text += f"Общее время работы ядра: {core_uptime['total_time']:.2f} секунд\n"

        return text
