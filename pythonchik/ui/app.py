"""
Реализация пользовательского интерфейса приложения Pythonchik.

Этот модуль предоставляет современный, настраиваемый интерфейс с использованием CustomTkinter
с улучшенной навигацией и организацией функциональности.

Примечания:
    - Современный, настраиваемый интерфейс
    - Улучшенная навигация
    - Организация функциональности по вкладкам
    - Интеграция с системой событий
"""

import json
import logging
import shutil
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import messagebox as mb

import customtkinter as ctk
import matplotlib.pyplot as plt

from pythonchik import config
from pythonchik.core.application_core import ApplicationCore
from pythonchik.core.application_state import ApplicationState
from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType
from pythonchik.events.handlers import (
    ProgressEventHandler,
    StateChangeHandler,
    TaskEventHandler,
)
from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
)
from pythonchik.ui.frames import ActionMenuFrame, LogFrame, ResultFrame, SideBarFrame, StateFrame
from pythonchik.utils import (
    create_archive,
    load_json_file,
    save_to_csv,
)
from pythonchik.utils.image import ImageProcessor
from pythonchik.utils.metrics import MetricsCollector
from pythonchik.utils.settings import SettingsManager


class ModernApp(ctk.CTk):
    """Главное окно приложения, реализующее современный интерфейс.

    Управляет компоновкой приложения, настройкой тем, а также координирует
    взаимодействие между компонентами пользовательского интерфейса (UI) и бизнес-логикой.
    """

    def __init__(self, core: ApplicationCore, event_bus: EventBus) -> None:
        """Инициализирует главное окно приложения и все основные UI-компоненты.

        Запускает ApplicationCore (ядро), настраивает event_bus для подписки
        на события, инициализирует SettingsManager, задаёт тему
        CustomTkinter, а также вызывает методы по настройке интерфейса.

        Note:
            В конце инициализации планируется периодический вызов
            `self.core.process_background_tasks` через `after(100, ...).
        """
        super().__init__()
        self.logger = logging.getLogger("pythonchik.ui.app")

        # Инициализация event_bus и ядро
        self.event_bus = event_bus
        self.core = core

        self.core.start()

        # Инициализируем менеджер настроек
        self.settings_manager = SettingsManager()

        # Настройка окна (размеры, title, минимальные размеры)
        self.title("Pythonchik by Dima Svirin")
        self.geometry("1200x800")
        self.minsize(1200, 800)

        # Настройка темы из сохранённых настроек
        theme = self.settings_manager.get_theme()
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        # Привязываем метод on_closing к системной кнопке закрытия
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Периодически проверяем фоновые задачи
        self.after(100, self.core.process_background_tasks)

        # Инициализация компонентов интерфейса
        self.setup_ui()

        # Инициализируем обработчики событий (подписки тоже здесь)
        self.setup_event_handlers()

        # Подключение UI-логирования (теперь log_frame уже существует)
        self.attach_ui_logger()

    def attach_ui_logger(self):
        """Добавляет логирование в UI после инициализации log_frame."""
        if hasattr(self, "log_frame") and self.log_frame:

            class UIHandler(logging.Handler):
                def __init__(self, log_frame):
                    super().__init__()
                    self.log_frame = log_frame

                def emit(self, record):
                    level = record.levelname
                    msg = self.format(record)
                    self.log_frame.log(msg)

            ui_handler = UIHandler(self.log_frame)
            ui_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logging.getLogger().addHandler(ui_handler)

            self.logger.info("Логирование в UI подключено")

    def setup_event_handlers(self) -> None:
        """Настраивает подписки на события и дополнительные хендлеры.

        Все подписки на EventBus находятся здесь.
        """
        from pythonchik.errors.error_context import ErrorSeverity
        from pythonchik.errors.error_handlers import UIErrorHandler
        from pythonchik.events.handlers import EventHandler

        # Создаем класс-адаптер для обработки событий ошибок
        class ErrorEventHandler(EventHandler):
            def __init__(self, error_handler: UIErrorHandler):
                self.error_handler = error_handler

            def handle(self, event: Event) -> None:
                if event.type != EventType.ERROR_OCCURRED:
                    return

                error = (
                    event.data.get("error", Exception("Unknown error"))
                    if event.data
                    else Exception("Unknown error")
                )
                context = event.data.get("context", {}) if event.data else {}
                operation = context.get("operation", "UI Operation") if context else "UI Operation"

                self.error_handler.handle_error(
                    error=error,
                    operation=operation,
                    severity=ErrorSeverity.ERROR,
                    additional_context=event.data,
                )

        # Подписываемся на событие TASK_COMPLETED
        task_handler = TaskEventHandler(self.result_frame, self.log_frame)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, task_handler)

        # Подписываемся на событие ERROR_OCCURRED
        error_handler = UIErrorHandler()
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, ErrorEventHandler(error_handler))

        # Подписываемся на событие PROGRESS_UPDATED
        progress_handler = ProgressEventHandler(self.result_frame, self.log_frame)
        self.event_bus.subscribe(EventType.PROGRESS_UPDATED, progress_handler)

        # Подписываемся на событие STATE_CHANGED
        state_handler = StateChangeHandler(self.state_frame)
        self.event_bus.subscribe(EventType.STATE_CHANGED, state_handler)

    def on_closing(self) -> None:
        """Вызывается при закрытии окна (например, по кнопке 'X').

        Останавливает ядро (core.stop()) и уничтожает текущее окно.
        """

        # Логируем факт закрытия
        self.logger.info("Получен сигнал на закрытие приложения")

        # (Опционально) спрашиваем подтверждение
        if not mb.askokcancel("Выход", "Точно хотите закрыть приложение?"):
            return

        self.core.state_manager.update_state(ApplicationState.SHUTTING_DOWN)

        # Сохраняем настройки (если что-то меняли)
        self.settings_manager.save_settings()
        # Останавливаем ядро (и ждём, пока поток завершится)
        self.core.stop()
        # Закрываем окно
        self.destroy()

    def setup_ui(self) -> None:
        """Настройка компонентов интерфейса.

        Создаёт и размещает основные UI компоненты в окне приложения.

        Включает:
        - Фрейм навигации (SideBarFrame)
        - Фрейм меню действий (ActionMenuFrame)
        - Фрейм результатов (ResultFrame)
        - Фрейм логов (LogFrame)
        """
        # Конфигурация сетки
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=2)

        # Фрейм навигации
        self.navigation_frame = SideBarFrame(self)
        self.navigation_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        # Колонки для экшен-меню и result
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)

        # Создаем главные фреймы
        # Фрейм меню действий
        self.action_menu = ActionMenuFrame(
            self,
            {
                "extract_addresses": self.extract_addresses,
                "check_coordinates": self.check_coordinates,
                "extract_barcodes": self.extract_barcodes,
                "write_test_json": self.write_test_json,
                "compress_images": self.compress_images,
                "convert_image_format": self.convert_image_format,
                "count_unique_offers": self.count_unique_offers,
                "compare_prices": self.compare_prices,
            },
            width=200,
        )
        self.action_menu.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Фрейм результатов
        self.result_frame = ResultFrame(self)
        self.result_frame.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)

        # Фрейм логов
        self.log_frame = LogFrame(self)
        self.log_frame.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=20, pady=(0, 10))

        # Фрейм статуса
        self.state_frame = StateFrame(self)
        self.state_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 10))

        # Настройка навигационных кнопок
        self.navigation_frame.set_button_commands(
            json_command=self.show_json_tab,
            image_command=self.show_image_tab,
            analysis_command=self.show_analysis_tab,
            metric_command=self.show_metrics,
            theme_command=self.change_appearance_mode,
        )

        # Показ начального фрейма
        self.select_frame_by_name("json")

    def show_json_tab(self) -> None:
        """Переключается на вкладку операций с JSON."""
        self.select_frame_by_name("json")

    def show_image_tab(self) -> None:
        """Переключается на вкладку операций с изображениями."""
        self.select_frame_by_name("image")

    def show_analysis_tab(self) -> None:
        """Переключается на вкладку анализа."""
        self.select_frame_by_name("analysis")

    def show_metrics(self):
        """Показывает метрики производительности приложения."""
        # Отображаем метрики во фрейме результатов
        self.result_frame.show_metrics()

        # Скрываем фрейм меню действий и показываем только фрейм результатов
        self.action_menu.grid_remove()
        self.result_frame.grid(row=0, column=1, columnspan=2, sticky="nsew", padx=20, pady=20)

        # Обновляем заголовок
        if hasattr(self.result_frame, "header_label"):
            self.result_frame.header_label.configure(text="Метрики производительности")

        # Выделяем вкладку Метрик в боковой панели
        self.navigation_frame.select_tab("metric")

    def change_appearance_mode(self, new_appearance_mode: str) -> None:
        """Изменяет текущую тему приложения.

        Args:
            new_appearance_mode (str): Новое название темы на русском языке
                ('Светлая', 'Тёмная', 'Системная').
        """
        mode_map = {"Светлая": "light", "Тёмная": "dark", "Системная": "system"}
        theme = mode_map.get(new_appearance_mode)
        if theme:
            ctk.set_appearance_mode(theme)
            self.settings_manager.set_theme(theme)

    def select_frame_by_name(self, name: str) -> None:
        """Отображает выбранный фрейм содержимого и очищает лог/result фреймы.

        Args:
            name (str): Имя фрейма для отображения ('json', 'image', 'analysis').
        """
        self.navigation_frame.select_tab(name)

        # Восстанавливаем видимость action_menu и правильное расположение фреймов
        self.action_menu.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.result_frame.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)

        # Восстанавливаем стандартный заголовок для result_frame
        if hasattr(self.result_frame, "header_label"):
            self.result_frame.header_label.configure(text="Результат")

        if name == "json":
            self.action_menu.show_json_section()
        elif name == "image":
            self.action_menu.show_image_section()
        elif name == "analysis":
            self.action_menu.show_analysis_section()

        self.result_frame.clear()
        self.log_frame.clear_log()

    def extract_addresses(self) -> None:
        """Извлекает и сохраняет адреса из выбранных JSON-файлов."""
        try:
            files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
                return

            self.log_frame.log("Начало извлечения адресов...")
            self.result_frame.update_progress(0, "Начало извлечения адресов...")

            def task():
                try:
                    addresses = []
                    total_files = len(files)

                    for idx, file_path in enumerate(files, 1):
                        progress = int((idx / total_files) * 100)

                        self.event_bus.publish(
                            Event(
                                EventType.PROGRESS_UPDATED,
                                {
                                    "progress": progress,
                                    "message": f"Обработка файла {idx}/{total_files}: {Path(file_path).name}",
                                },
                            )
                        )

                        data = load_json_file(str(file_path))
                        result = extract_addresses(data, self.event_bus)
                        addresses.extend(result)

                    if addresses:
                        output_path = config.get_unique_filename(
                            Path(files[-1]).stem, config.ADDRESSES_SUFFIX, ".csv"
                        )
                        save_to_csv(addresses, ["Адрес"], str(output_path))
                        self.log_frame.log(f"Адреса сохранены в файл: {output_path}")
                        message = f"Найдено {len(addresses)} адресов"
                        self.result_frame.show_text(message)
                    else:
                        self.log_frame.log("Адреса не найдены в выбранных файлах")

                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 100, "message": "Операция завершена!"},
                        )
                    )
                    return addresses
                except Exception as e:
                    from pythonchik.errors.error_context import ErrorSeverity
                    from pythonchik.errors.error_handlers import DataProcessingErrorHandler

                    error_handler = DataProcessingErrorHandler()
                    error_handler.handle_error(
                        error=e,
                        operation="Извлечение адресов",
                        severity=ErrorSeverity.ERROR,
                        recovery_action="Проверьте структуру JSON файла",
                        additional_context={"files": [str(f) for f in files if files]},
                    )
                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 0, "message": ""},
                        )
                    )
                    self.log_frame.log(f"Ошибка при извлечении адресов: {str(e)}", "ERROR")
                    raise

            self.core.add_task(task, "Задача извлечения адресов")

        except Exception as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import UIErrorHandler

            error_handler = UIErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Извлечение адресов",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте выбранные файлы и повторите операцию",
                additional_context={"files": [str(f) for f in files if files]},
            )
            mb.showerror("Ошибка", f"Ошибка при извлечении адресов: {str(e)}")
            self.log_frame.log(f"Ошибка: {str(e)}", "ERROR")

    def compress_images(self) -> None:
        """Сжимает выбранные изображения и архивирует результат."""
        try:
            files = fd.askopenfilenames(filetypes=config.IMAGE_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите файл(ы) изображений")
                return

            self.log_frame.log("Начало процесса сжатия изображений")
            self.result_frame.update_progress(0, "Начало процесса сжатия изображений")

            def task():
                try:
                    output_dir = Path(config.COMPRESSED_IMAGES_DIR)
                    output_dir.mkdir(exist_ok=True)

                    self.result_frame.update_progress(20, "Сжатие изображений...")
                    processed_files = ImageProcessor.compress_multiple_images(list(files), str(output_dir))

                    self.result_frame.update_progress(60, "Создание архива...")
                    archive_path = config.get_archive_path()
                    create_archive([str(file) for file in processed_files], str(archive_path))

                    self.result_frame.update_progress(90, "Очистка временных файлов...")
                    shutil.rmtree(output_dir)

                    self.result_frame.update_progress(100, "Операция завершена!")
                    return processed_files
                except Exception as e:
                    from pythonchik.errors.error_context import ErrorSeverity
                    from pythonchik.errors.error_handlers import ImageProcessingErrorHandler

                    error_handler = ImageProcessingErrorHandler()
                    error_handler.handle_error(
                        error=e,
                        operation="Сжатие изображений",
                        severity=ErrorSeverity.ERROR,
                        recovery_action="Проверьте выбранные файлы и права доступа",
                        additional_context={"files": [str(f) for f in files if files]},
                    )
                    self.result_frame.update_progress(0, "")
                    self.log_frame.log(f"Ошибка при сжатии изображений: {str(e)}", "ERROR")
                    raise

            self.core.add_task(task)

        except Exception as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import UIErrorHandler

            error_handler = UIErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Сжатие изображений",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте выбранные файлы и повторите операцию",
                additional_context={"files": [str(f) for f in files if files]},
            )
            mb.showerror("Ошибка", f"Ошибка при сжатии изображений: {str(e)}")
            self.log_frame.log(f"Ошибка: {str(e)}", "ERROR")

    def check_coordinates(self) -> None:
        """Проверяет и формирует отчёт о соответствии адресов и координат."""
        try:
            files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
                return

            self.log_frame.log("Начало проверки соответствия адресов и координат...")
            self.result_frame.update_progress(0, "Начало проверки соответствия адресов и координат...")

            def task():
                try:
                    no_coords_list = []
                    total_catalogs = 0
                    total_coords = 0
                    matched_count = 0
                    total_files = len(files)

                    for index, file_path in enumerate(files, 1):
                        progress = int((index / total_files) * 100)
                        self.result_frame.update_progress(
                            progress, f"Обработка файла: {Path(file_path).name}"
                        )
                        data = load_json_file(file_path)
                        no_coords, catalogs, coords, matched = check_coordinates_match(data)
                        no_coords_list.extend(no_coords)
                        total_catalogs += catalogs
                        total_coords += coords
                        matched_count += matched

                    info_message = (
                        f"Всего каталогов: {total_catalogs}\n"
                        f"Всего координат: {total_coords}\n"
                        f"Адресов с координатами: {matched_count}\n"
                        f"Адреса без координат:\n"
                        f"{', '.join(no_coords_list)}"
                    )
                    self.result_frame.show_text(info_message)
                    self.log_frame.log("Анализ соответствия адресов и координат завершен")

                    if no_coords_list:
                        output_path = config.get_unique_filename(
                            Path(files[-1]).stem, config.NO_COORDINATES_SUFFIX, ".csv"
                        )
                        save_to_csv(no_coords_list, ["Адреса без координат"], str(output_path))
                        self.log_frame.log(f"Адреса без координат сохранены в файл: {output_path}")

                    self.result_frame.update_progress(100, "Операция завершена!")
                    return info_message
                except Exception as e:
                    from pythonchik.errors.error_context import ErrorSeverity
                    from pythonchik.errors.error_handlers import DataProcessingErrorHandler

                    error_handler = DataProcessingErrorHandler()
                    error_handler.handle_error(
                        error=e,
                        operation="Проверка координат",
                        severity=ErrorSeverity.ERROR,
                        recovery_action="Проверьте структуру JSON файла",
                        additional_context={"files": [str(f) for f in files if files]},
                    )
                    self.result_frame.update_progress(0, "")
                    self.log_frame.log(f"Ошибка при проверке координат: {str(e)}", "ERROR")
                    raise

            self.core.add_task(task)

        except Exception as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import UIErrorHandler

            error_handler = UIErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Проверка координат",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте выбранные файлы и повторите операцию",
                additional_context={"files": [str(f) for f in files if files]},
            )
            mb.showerror("Ошибка", f"Ошибка при проверке координат: {str(e)}")
            self.log_frame.log(f"Ошибка: {str(e)}", "ERROR")

    def extract_barcodes(self) -> None:
        """Извлекает штрих-коды из выбранных JSON-файлов и сохраняет в CSV."""
        try:
            files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
                return

            self.log_frame.log("Начало извлечения штрих-кодов...")
            self.result_frame.update_progress(0, "Начало извлечения штрих-кодов...")

            def task():
                try:
                    all_barcodes = []
                    total_files = len(files)

                    for idx, file_path in enumerate(files, 1):
                        progress = int((idx / total_files) * 100)
                        self.result_frame.update_progress(
                            progress, f"Обработка файла {idx}/{total_files}: {Path(file_path).name}"
                        )

                        data = load_json_file(str(file_path))
                        barcodes = extract_barcodes(data)
                        all_barcodes.extend(barcodes)

                    if all_barcodes:
                        output_path = config.get_unique_filename(
                            Path(files[-1]).stem, config.BARCODES_SUFFIX, ".csv"
                        )
                        save_to_csv(all_barcodes, ["Штрих-код"], str(output_path))
                        self.log_frame.log(f"Штрих-коды сохранены в файл: {output_path}")
                        message = f"Найдено {len(all_barcodes)} штрих-кодов"
                        self.result_frame.show_text(message)
                    else:
                        self.log_frame.log("Штрих-коды не найдены в выбранных файлах")

                    self.result_frame.update_progress(100, "Операция завершена!")
                    return all_barcodes
                except Exception as e:
                    from pythonchik.errors.error_context import ErrorSeverity
                    from pythonchik.errors.error_handlers import DataProcessingErrorHandler

                    error_handler = DataProcessingErrorHandler()
                    error_handler.handle_error(
                        error=e,
                        operation="Извлечение штрих-кодов",
                        severity=ErrorSeverity.ERROR,
                        recovery_action="Проверьте структуру JSON файла",
                        additional_context={"files": [str(f) for f in files if files]},
                    )
                    self.result_frame.update_progress(0, "")
                    self.log_frame.log(f"Ошибка при извлечении штрих-кодов: {str(e)}", "ERROR")
                    raise

            self.core.add_task(task)

        except Exception as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import UIErrorHandler

            error_handler = UIErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Извлечение штрих-кодов",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте выбранные файлы и повторите операцию",
                additional_context={"files": [str(f) for f in files if files]},
            )
            mb.showerror("Ошибка", f"Ошибка при извлечении штрих-кодов: {str(e)}")
            self.log_frame.log(f"Ошибка: {str(e)}", "ERROR")

    def write_test_json(self) -> None:
        """Создаёт тестовый JSON-файл из выбранного JSON."""
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if len(files) != 1:
            mb.showinfo("Информация", "Пожалуйста, выберите один JSON файл")
            return

        self.log_frame.log("Начало создания тестового JSON...")
        self.log_frame.log(f"Обработка файла: {Path(files[0]).name}")

        try:
            data = load_json_file(files[0])
            json_file = create_test_json(data)

            output_path = config.get_unique_filename(Path(files[0]).stem, config.TEST_JSON_SUFFIX, ".json")
            with open(output_path, "w", encoding="utf-8") as outfile:
                json_content = json.dumps(json_file, ensure_ascii=False, indent=2)
                json.dump(json_file, outfile, ensure_ascii=False, indent=2)
                self.result_frame.show_text(json_content)

            self.log_frame.log(f"Тестовый JSON сохранен в файл: {output_path}")
            self.log_frame.log("Операция успешно завершена!")
            mb.showinfo("Успех", "Тестовый JSON успешно создан!")
        except Exception as exc:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import UIErrorHandler

            error_handler = UIErrorHandler()
            error_handler.handle_error(
                error=exc,
                operation="Создание тестового JSON",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте структуру исходного JSON файла",
                additional_context={"file": files[0] if files else "Файл не выбран"},
            )
            mb.showerror("Ошибка", f"Не удалось создать тестовый JSON: {str(exc)}")
            self.log_frame.log(f"Ошибка: {str(exc)}", "ERROR")

    def convert_image_format(self) -> None:
        """Конвертирует выбранные изображения в формат PNG."""
        files = fd.askopenfilenames(filetypes=config.IMAGE_FILE_TYPES)
        if not files:
            mb.showinfo("Информация", "Пожалуйста, выберите файл(ы) изображений")
            return

        output_dir = Path(config.FORMAT_CONVERTED_IMAGES_DIR)
        output_dir.mkdir(exist_ok=True)

        for file_path in files:
            try:
                ImageProcessor.convert_format(file_path, str(output_dir / f"{Path(file_path).stem}.png"))
            except (FileNotFoundError, PermissionError, OSError) as e:
                mb.showerror(
                    "Ошибка",
                    f"Не удалось обработать изображение {file_path}: {str(e)}",
                )

        mb.showinfo("Успех", "Изображения успешно конвертированы!")

    def count_unique_offers(self) -> None:
        """Подсчитывает количество уникальных предложений в JSON-файлах."""
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if not files:
            mb.showinfo("Информация", "Пожалуйста, выберите JSON файл(ы)")
            return

        try:
            self.log_frame.log("Начало анализа файлов...")
            total_files = len(files)

            total_count = 0
            unique_descriptions = set()

            for index, file in enumerate(files, 1):
                progress = int((index / total_files) * 80)
                self.result_frame.update_progress(
                    progress, f"Обработка файла {index}/{total_files}: {Path(file).name}"
                )
                self.log_frame.log(f"Анализ файла: {Path(file).name}")

                data = load_json_file(file)
                offers = data.get("offers", [])
                total_count += len(offers)
                unique_descriptions.update(offer["description"] for offer in offers if "description" in offer)

            self.result_frame.update_progress(90, "Подсчет итоговых результатов...")
            unique_count = len(unique_descriptions)

            result_message = f"Всего предложений: {total_count}\n" f"Уникальных предложений: {unique_count}"
            self.log_frame.log("Анализ завершен.")
            self.log_frame.log(result_message)
            self.result_frame.show_text(result_message)
            self.result_frame.update_progress(100, "Готово!")

        except (KeyError, ValueError, TypeError, FileNotFoundError) as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import DataProcessingErrorHandler

            error_handler = DataProcessingErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Подсчет предложений",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте структуру JSON файла",
                additional_context={"files": [str(f) for f in files if files]},
            )
            error_message = f"Ошибка: {str(e)}"
            self.log_frame.log(error_message, "ERROR")
            mb.showerror("Ошибка", error_message)
            self.result_frame.update_progress(0, "")
        finally:
            self.result_frame.update_progress(0, "")

    def compare_prices(self) -> None:
        """Анализирует и визуализирует различия цен в выбранных JSON-файлах."""
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if not files:
            self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
            return

        try:
            self.log_frame.log("Начало анализа разницы цен...")
            self.log_frame.log(f"Выбрано {len(files)} файлов для обработки")
            total_files = len(files)

            price_diffs = []
            total_count = 0
            total_offers = 0

            self.result_frame.update_progress(0, "Начало обработки файлов...")
            for index, file_path in enumerate(files, 1):
                progress = int((index / total_files) * 80)
                self.result_frame.update_progress(
                    progress, f"Обработка файла {index}/{total_files}: {Path(file_path).name}"
                )
                self.log_frame.log(f"Анализ файла: {Path(file_path).name}")

                data = load_json_file(file_path)
                diffs, diff_count, total = analyze_price_differences(dict(data))
                price_diffs.extend(diffs)
                total_count += diff_count
                total_offers += total
                self.log_frame.log(f"Найдено {diff_count} предложений с разными ценами в файле")

            if total_offers > 0:
                self.result_frame.update_progress(90, "Создание графика...")
                percentage = int(total_count * 100 / total_offers)
                fig = plt.figure(figsize=config.PRICE_PLOT_SIZE)
                plt.hist(price_diffs, bins=config.PRICE_PLOT_BINS)
                self.result_frame.show_figure(fig)
                plt.close(fig)
                plot_filename = config.get_plot_filename()
                plt.savefig(plot_filename)

                result_message = (
                    f"Всего уникальных предложений: {total_offers}\n"
                    f"Предложений с различными ценами: {total_count}\n"
                    f"Процент предложений с различными ценами: {percentage}%"
                )
                self.log_frame.log("Анализ завершен.")
                self.log_frame.log(result_message)

                self.result_frame.update_progress(100, "Готово!")
            else:
                self.log_frame.log("Предложения не найдены в выбранных файлах")

        except (FileNotFoundError, PermissionError) as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import FileProcessingErrorHandler

            error_handler = FileProcessingErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Доступ к файлам для анализа цен",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте наличие и доступность выбранных файлов",
                additional_context={"files": [str(f) for f in files if files]},
            )
            error_msg = f"Ошибка доступа к файлам: {str(e)}"
            self.log_frame.log(error_msg, "ERROR")
            mb.showerror("Ошибка", error_msg)
        except (KeyError, ValueError, TypeError) as e:
            from pythonchik.errors.error_context import ErrorSeverity
            from pythonchik.errors.error_handlers import DataProcessingErrorHandler

            error_handler = DataProcessingErrorHandler()
            error_handler.handle_error(
                error=e,
                operation="Обработка данных для анализа цен",
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте структуру JSON файла",
                additional_context={"files": [str(f) for f in files if files]},
            )
            error_msg = f"Ошибка обработки данных: {str(e)}"
            self.log_frame.log(error_msg, "ERROR")
            mb.showerror("Ошибка", error_msg)
        finally:
            self.result_frame.update_progress(0, "")
            self.log_frame.log("Процесс завершен")
