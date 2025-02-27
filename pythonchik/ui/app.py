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
from pythonchik.core import ApplicationCore
from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
)
from pythonchik.ui.frames import ActionMenuFrame, LogFrame, ResultFrame, SideBarFrame, StatusFrame
from pythonchik.utils import (
    create_archive,
    load_json_file,
    save_to_csv,
)
from pythonchik.utils.error_context import ErrorContext, ErrorSeverity
from pythonchik.utils.event_system import Event, EventBus, EventType
from pythonchik.utils.image import ImageProcessor
from pythonchik.utils.settings import SettingsManager


class ModernApp(ctk.CTk):
    """Главное окно приложения, реализующее современный интерфейс.

    Управляет компоновкой приложения, настройкой тем, а также координирует
    взаимодействие между компонентами пользовательского интерфейса (UI) и бизнес-логикой.
    """

    def __init__(self) -> None:
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
        self.event_bus = EventBus()
        self.core = ApplicationCore(event_bus=self.event_bus)
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

        # Инициализируем обработчики событий (подписки тоже здесь)
        self.setup_event_handlers()

        # Периодически проверяем фоновые задачи
        self.after(100, self.core.process_background_tasks)

        # Инициализация компонентов интерфейса
        self.setup_ui()

        # Подключение UI-логирования (теперь log_frame уже существует)
        self.attach_ui_logger()

    def attach_ui_logger(self):
        """Добавляет логирование в UI после инициализации log_frame."""
        if hasattr(self, "log_frame") and self.log_frame:

            class UIHandler(logging.Handler):
                def emit(self, record):
                    level = record.levelname
                    msg = self.format(record)
                    self.log_frame.log(msg, level)

            ui_handler = UIHandler()
            ui_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logging.getLogger().addHandler(ui_handler)

            self.logger.info("Логирование в UI подключено")

    def setup_event_handlers(self) -> None:
        """Настраивает подписки на события и дополнительные хендлеры.

        Все подписки на EventBus находятся здесь.
        """

        def on_task_completed(event: Event) -> None:
            """Обработчик события TASK_COMPLETED.

            Args:
                event (Event): Событие, содержащее данные о результате (`event.data["result"]`).
            """
            result = event.data.get("result")
            self.logger.info(f"Task completed with result: {result}")
            # Здесь можно обновить UI, показать уведомление и т.д.

        def on_error_occurred(event: Event) -> None:
            """Обработчик события ERROR_OCCURRED.

            Args:
                event (Event): Событие об ошибке, внутри `event.data["error"]`.
            """
            error_msg = event.data.get("error", "Unknown error")
            self.logger.error(f"Error occurred: {error_msg}")
            mb.showerror("Ошибка", f"Произошла ошибка: {error_msg}")

        def on_state_changed(event: Event) -> None:
            """Обработчик события STATE_CHANGED.

            Args:
                event (Event): Событие, содержащее новое состояние в `event.data["state"]`.
            """
            new_state = event.data.get("state")
            self.logger.info(f"Application state changed to: {new_state}")
            # Можно обновить статус-бары, заголовки и т.д.

        # Подписываемся на основные события
        self.event_bus.subscribe(EventType.TASK_COMPLETED, on_task_completed)
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, on_error_occurred)
        self.event_bus.subscribe(EventType.STATE_CHANGED, on_state_changed)

        # Пример подписки на UI_ACTION (если нужно):
        # def on_ui_action(event: Event) -> None:
        #     """Обработчик событий UI_ACTION."""
        #     # Вызвать какие-то UI-действия или бизнес-логику
        #     pass
        # self.event_bus.subscribe(EventType.UI_ACTION, on_ui_action)

    def on_closing(self) -> None:
        """Вызывается при закрытии окна (например, по кнопке 'X').

        Останавливает ядро (core.stop()) и уничтожает текущее окно.
        """

        # Логируем факт закрытия
        self.logger.info("Application is closing...")

        # (Опционально) спрашиваем подтверждение
        if not mb.askokcancel("Выход", "Точно хотите закрыть приложение?"):
            return

        # Сохраняем настройки (если что-то меняли)
        self.settings_manager.save_settings()

        # Останавливаем ядро (и ждём, пока поток завершится)
        self.core.stop()
        if self.core._worker_thread is not None and self.core._worker_thread.is_alive():
            self.core._worker_thread.join(timeout=2)

        # Очистка других ресурсов (файлы, соединения)
        # close_all_files() ...
        # db_connection.close() ...

        # Закрываем окно
        self.destroy()

    def setup_ui(self) -> None:
        """Создаёт и конфигурирует все основные UI-компоненты.

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
        self.status_frame = StatusFrame(self, self.event_bus)
        self.status_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 10))

        # Настройка навигационных кнопок
        self.navigation_frame.set_button_commands(
            self.show_json_tab,
            self.show_image_tab,
            self.show_analysis_tab,
            self.change_appearance_mode,
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

    def change_appearance_mode(self, new_appearance_mode: str) -> None:
        """Изменяет текущую тему приложения.

        Args:
            new_appearance_mode (str): Новое название темы на русском языке
                ('Светлая', 'Тёмная', 'Системная').
        """
        mode_map = {"Светлая": "light", "Тёмная": "dark", "Системная": "system"}
        theme = mode_map[new_appearance_mode]
        ctk.set_appearance_mode(theme)
        self.settings_manager.set_theme(theme)

    def select_frame_by_name(self, name: str) -> None:
        """Отображает выбранный фрейм содержимого и очищает лог/result фреймы.

        Args:
            name (str): Имя фрейма для отображения ('json', 'image', 'analysis').
        """
        self.navigation_frame.select_tab(name)

        if name == "json":
            self.action_menu.show_json_section()
        elif name == "image":
            self.action_menu.show_image_section()
        elif name == "analysis":
            self.action_menu.show_analysis_section()

        self.result_frame.clear()
        self.log_frame.clear_log()

    def _handle_error(self, error: Exception, operation: str) -> None:
        """Обрабатывает ошибку, возникшую при выполнении конкретной операции.

        Args:
            error (Exception): Возникшее исключение.
            operation (str): Название операции, при выполнении которой произошла ошибка.
        """
        error_msg = f"Ошибка при {operation}: {str(error)}"
        self.log_frame.log(error_msg)
        mb.showerror("Ошибка", error_msg)

    def _track_progress(self, total_items: int, operation: str):
        """Создаёт функцию обновления прогресса для длительных операций.

        Args:
            total_items (int): Общее количество элементов для обработки.
            operation (str): Название операции.

        Returns:
            Callable[[int, str], None]: Функция, принимающая текущий индекс
            обработки и необязательное сообщение, и обновляющая прогресс.
        """

        def update(current: int, message: str = "") -> None:
            progress = int((current / total_items) * 100)
            self.update_progress(progress, f"{operation}: {message}")

        return update

    def extract_addresses(self) -> None:
        """Извлекает и сохраняет адреса из выбранных JSON-файлов."""
        try:
            files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
                return

            self.log_frame.log("Начало обработки файлов")

            def task():
                addresses = []
                for file_path in files:
                    data = load_json_file(str(file_path))
                    result = extract_addresses(data)
                    addresses.extend(result)

                if addresses:
                    output_path = config.get_unique_filename(
                        Path(files[-1]).stem, config.ADDRESSES_SUFFIX, ".csv"
                    )
                    save_to_csv(addresses, ["Адрес"], str(output_path))
                    return addresses
                return []

            # self.core.handle_task(
            #     task,
            #     description="Извлечение адресов",
            #     on_complete=lambda result: (
            #         self.result_frame.show_text("\n".join(result)) if result else None,
            #         (
            #             self.log_frame.log("Адреса успешно извлечены!")
            #             if result
            #             else self.log_frame.log("Адреса не найдены")
            #         ),
            #     ),
            # )
            self.core.add_task(task)

        except Exception as e:
            self._handle_error(e, "извлечении адресов")

    def compress_images(self) -> None:
        """Сжимает выбранные изображения и архивирует результат."""
        try:
            files = fd.askopenfilenames(filetypes=config.IMAGE_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите файл(ы) изображений")
                return

            self.log_frame.log("Начало процесса сжатия изображений")
            output_dir = Path(config.COMPRESSED_IMAGES_DIR)
            output_dir.mkdir(exist_ok=True)

            processed_files = ImageProcessor.compress_multiple_images(list(files), str(output_dir))
            archive_path = config.get_archive_path()
            create_archive(processed_files, archive_path)
            shutil.rmtree(output_dir)

            self.log_frame.log("Процесс сжатия изображений успешно завершен!")

        except Exception as e:
            self._handle_error(e, "сжатии изображений")

    def check_coordinates(self) -> None:
        """Проверяет и формирует отчёт о соответствии адресов и координат."""
        try:
            files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
            if not files:
                self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
                return

            self.log_frame.log("Начало проверки соответствия адресов и координат...")
            progress_update = self._track_progress(len(files), "Проверка координат")

            no_coords_list = []
            total_catalogs = 0
            total_coords = 0
            matched_count = 0

            for index, file_path in enumerate(files, 1):
                progress_update(index, f"Обработка файла: {Path(file_path).name}")
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

        except Exception as e:
            self._handle_error(e, "проверке координат")
        finally:
            self.reset_progress()

    def extract_barcodes(self) -> None:
        """Извлекает штрих-коды из выбранных JSON-файлов и сохраняет в CSV."""
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if not files:
            self.log_frame.log("Пожалуйста, выберите JSON файл(ы)")
            return

        try:
            self.log_frame.log("Начало извлечения штрих-кодов...")
            self.log_frame.log(f"Выбрано {len(files)} файлов для обработки")
            total_files = len(files)

            barcodes = []
            for index, file_path in enumerate(files, 1):
                progress = int((index / total_files) * 80)
                self.update_progress(
                    progress, f"Обработка файла {index}/{total_files}: {Path(file_path).name}"
                )
                self.log_frame.log(f"Анализ файла: {Path(file_path).name}")

                data = load_json_file(file_path)
                result = extract_barcodes(data)
                barcodes.extend(result)
                self.log_frame.log(f"Найдено {len(result)} штрих-кодов в файле")

            if barcodes:
                self.update_progress(90, "Сохранение результатов...")
                output_path = config.get_unique_filename(Path(files[-1]).stem, config.BARCODE_SUFFIX, ".csv")
                save_to_csv(barcodes, ["Штрих-код"], str(output_path))
                self.log_frame.log(f"Штрих-коды сохранены в файл: {output_path}")
                self.result_frame.show_text("\n".join(barcodes))
                self.update_progress(100, "Готово!")
                self.log_frame.log(f"Всего извлечено {len(barcodes)} уникальных штрих-кодов")
            else:
                self.log_frame.log("Штрих-коды не найдены в выбранных файлах")

        except (FileNotFoundError, PermissionError) as e:
            error_msg = f"Ошибка доступа к файлам: {str(e)}"
            self.log_frame.log(error_msg)
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Ошибка обработки данных: {str(e)}"
            self.log_frame.log(error_msg)
        finally:
            self.update_progress(0)
            self.log_frame.log("Процесс завершен")

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
            self._handle_error(exc, "создании тестового JSON")

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
                self.update_progress(progress, f"Обработка файла {index}/{total_files}: {Path(file).name}")
                self.log_frame.log(f"Анализ файла: {Path(file).name}")

                data = load_json_file(file)
                offers = data.get("offers", [])
                total_count += len(offers)
                unique_descriptions.update(offer["description"] for offer in offers if "description" in offer)

            self.update_progress(90, "Подсчет итоговых результатов...")
            unique_count = len(unique_descriptions)

            result_message = f"Всего предложений: {total_count}\n" f"Уникальных предложений: {unique_count}"
            self.log_frame.log("Анализ завершен.")
            self.log_frame.log(result_message)
            self.result_frame.show_text(result_message)
            self.update_progress(100, "Готово!")

        except (KeyError, ValueError, TypeError, FileNotFoundError) as e:
            error_message = f"Ошибка: {str(e)}"
            self.log_frame.log(error_message, "ERROR")
            self.update_progress(0)
        finally:
            self.update_progress(0)

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

            self.update_progress(0, "Начало обработки файлов...")
            for index, file_path in enumerate(files, 1):
                progress = int((index / total_files) * 80)
                self.update_progress(
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
                self.update_progress(90, "Создание графика...")
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

                self.update_progress(100, "Готово!")
            else:
                self.log_frame.log("Предложения не найдены в выбранных файлах")

        except (FileNotFoundError, PermissionError) as e:
            error_msg = f"Ошибка доступа к файлам: {str(e)}"
            self.log_frame.log(error_msg)
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Ошибка обработки данных: {str(e)}"
            self.log_frame.log(error_msg)
        finally:
            self.reset_progress()
            self.log_frame.log("Процесс завершен")

    def update_progress(self, progress: int, message: str = "") -> None:
        """Обновляет индикатор прогресса и сообщение в фрейме результатов.

        Args:
            progress (int): Процент выполнения (0..100).
            message (str, optional): Статусное сообщение для отображения.
        """
        self.result_frame.update_progress(progress, message)
        self.log_frame.log(message)

    def reset_progress(self) -> None:
        """Сбрасывает индикатор прогресса в исходное состояние."""
        self.result_frame.reset_progress()
