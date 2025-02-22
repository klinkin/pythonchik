"""Реализация пользовательского интерфейса приложения Pythonchik.

Описание:
    Этот модуль предоставляет современный, настраиваемый интерфейс с использованием CustomTkinter
    с улучшенной навигацией и организацией функциональности.

Особенности:
    - Современный, настраиваемый интерфейс
    - Улучшенная навигация
    - Организация функциональности по вкладкам
    - Интеграция с системой событий
"""

import json
import shutil
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import messagebox as mb

import customtkinter as ctk
import matplotlib.pyplot as plt

from pythonchik import config
from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
)
from pythonchik.ui.core import ApplicationCore
from pythonchik.ui.frames import ActionMenuFrame, LogFrame, ResultFrame, SideBarFrame
from pythonchik.utils import (
    create_archive,
    load_json_file,
    process_multiple_files,
    save_to_csv,
)
from pythonchik.utils.image import ImageProcessor


class ModernApp(ctk.CTk):
    """Главное окно приложения, реализующее современный интерфейс.

    Этот класс управляет общей компоновкой приложения и координирует
    взаимодействие между различными компонентами пользовательского интерфейса и бизнес-логикой.
    """

    def __init__(self) -> None:
        super().__init__()

        # Инициализация ядра приложения
        self.core = ApplicationCore()
        self.settings_manager = self.core.settings_manager

        # Настройка окна
        self.title("Pythonchik by Dima Svirin")
        self.geometry("1200x800")
        self.minsize(1200, 800)

        # Настройка темы из сохраненных настроек
        theme = self.settings_manager.get_theme()
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        # Конфигурация сетки
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=2)

        # Инициализация компонентов интерфейса
        self.setup_ui()

        # Start background task processing
        self.after(100, self.core.process_background_tasks)

    def setup_ui(self) -> None:
        """Инициализация и настройка всех компонентов интерфейса.

        Метод создает и размещает все основные компоненты пользовательского
        интерфейса, включая навигационную панель, меню действий, фреймы
        результатов и логов.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.setup_ui()
        """
        # Создание фрейма навигации
        self.navigation_frame = SideBarFrame(self)
        self.navigation_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        # Configure column weights for proper layout
        self.grid_columnconfigure(1, weight=0)  # Action menu column
        self.grid_columnconfigure(2, weight=1)  # Result frame column

        # Создание фрейма меню действий
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
            width=200,  # Set fixed width for action menu
        )
        self.action_menu.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Создание фрейма результатов
        self.result_frame = ResultFrame(self)
        self.result_frame.grid(row=0, column=2, sticky="nsew", padx=20, pady=20)

        # Создание фрейма логов
        self.log_frame = LogFrame(self)
        self.log_frame.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=20, pady=(0, 20))

        # Настройка обработчиков навигации
        self.navigation_frame.set_button_commands(
            self.show_json_tab,
            self.show_image_tab,
            self.show_analysis_tab,
            self.change_appearance_mode,
        )

        # Показать начальный фрейм
        self.select_frame_by_name("json")

    def show_json_tab(self) -> None:
        """Переключение на вкладку операций с JSON.

        Активирует вкладку JSON и обновляет интерфейс для отображения
        соответствующих элементов управления.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.show_json_tab()
        """
        self.select_frame_by_name("json")

    def show_image_tab(self) -> None:
        """Переключение на вкладку операций с изображениями.

        Активирует вкладку изображений и обновляет интерфейс для отображения
        соответствующих элементов управления.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.show_image_tab()
        """
        self.select_frame_by_name("image")

    def show_analysis_tab(self) -> None:
        """Переключение на вкладку анализа.

        Активирует вкладку анализа и обновляет интерфейс для отображения
        соответствующих элементов управления.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.show_analysis_tab()
        """
        self.select_frame_by_name("analysis")

    def change_appearance_mode(self, new_appearance_mode: str) -> None:
        """Изменение темы приложения.

        Изменяет текущую тему оформления приложения на основе
        выбранного пользователем значения.

        Аргументы:
            new_appearance_mode: Новое название темы на русском языке
                               ('Светлая', 'Тёмная' или 'Системная')

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.change_appearance_mode('Тёмная')
        """
        mode_map = {"Светлая": "light", "Тёмная": "dark", "Системная": "system"}
        theme = mode_map[new_appearance_mode]
        ctk.set_appearance_mode(theme)
        self.settings_manager.set_theme(theme)

    def select_frame_by_name(self, name: str) -> None:
        """Показать выбранный фрейм содержимого и обновить состояние навигации.

        Обновляет интерфейс для отображения выбранного фрейма и
        соответствующих элементов управления, а также очищает
        фреймы результатов и логов.

        Аргументы:
            name: Имя фрейма для отображения ('json', 'image' или 'analysis')

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.select_frame_by_name('json')
        """
        # Update navigation frame state and buttons
        self.navigation_frame.select_tab(name)

        # Update action menu sections
        if name == "json":
            self.action_menu.show_json_section()
        elif name == "image":
            self.action_menu.show_image_section()
        elif name == "analysis":
            self.action_menu.show_analysis_section()

        # Clear result and log frames
        self.result_frame.clear()
        self.log_frame.clear_log()

    def _handle_error(self, error: Exception, operation: str) -> None:
        """Unified error handling for all operations.

        Аргументы:
            error: Возникшее исключение
            operation: Название операции, в которой произошла ошибка
        """
        error_msg = f"Ошибка при {operation}: {str(error)}"
        self.log_frame.log(error_msg)
        mb.showerror("Ошибка", error_msg)

    def _track_progress(self, total_items: int, operation: str) -> None:
        """Unified progress tracking for long-running operations.

        Аргументы:
            total_items: Общее количество элементов для обработки
            operation: Название текущей операции
        """

        def update(current: int, message: str = "") -> None:
            progress = int((current / total_items) * 100)
            self.update_progress(progress, f"{operation}: {message}")

        return update

    def extract_addresses(self) -> None:
        """Извлечение и сохранение адресов из JSON файлов."""
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

            self.core.handle_task(
                task,
                description="Извлечение адресов",
                on_complete=lambda result: (
                    self.result_frame.show_text("\n".join(result)) if result else None,
                    (
                        self.log_frame.log("Адреса успешно извлечены!")
                        if result
                        else self.log_frame.log("Адреса не найдены")
                    ),
                ),
            )

        except Exception as e:
            self._handle_error(e, "извлечении адресов")

    def compress_images(self) -> None:
        """Обработка и сжатие выбранных изображений."""
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
        """Проверка и отчет о соответствии адресов и координат."""
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
        """Извлечение и сохранение штрих-кодов из JSON файлов.

        Загружает выбранные JSON файлы, извлекает штрих-коды и
        сохраняет их в CSV файл.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.extract_barcodes()
        """
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
        """Создание тестового JSON файла из выбранного файла.

        Загружает выбранный JSON файл, создает на его основе тестовый
        файл и сохраняет результат.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.write_test_json()
        """
        files = fd.askopenfilenames(filetypes=config.JSON_FILE_TYPES)
        if len(files) != 1:
            mb.showinfo("Информация", "Пожалуйста, выберите один JSON файл")
            return

        self.log_frame.log("Начало создания тестового JSON...")
        self.log_frame.log(f"Обработка файла: {Path(files[0]).name}")

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

    def convert_image_format(self) -> None:
        """Конвертация изображений в формат PNG.

        Загружает выбранные изображения и конвертирует их в формат PNG,
        сохраняя результаты в отдельную директорию.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.convert_image_format()
        """
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
        """Подсчет и отображение статистики уникальных предложений.

        Анализирует выбранные JSON файлы и подсчитывает количество
        уникальных предложений, отображая результаты в диалоговом окне.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.count_unique_offers()
        """
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

            result_message = f"Всего предложений: {total_count}\nУникальных предложений: {unique_count}"
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
        """Анализ и визуализация разницы в ценах.

        Загружает выбранные JSON файлы, анализирует разницу в ценах
        и создает визуализацию результатов.

        Аргументы:
            Нет

        Возвращает:
            None

        Пример использования:
            app = ModernApp()
            app.compare_prices()
        """
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
        """Update the progress indicator and message in the result frame.

        Args:
            progress: Progress percentage (0-100)
            message: Optional status message to display
        """
        self.result_frame.update_progress(progress, message)
        self.log_frame.log(message)

    def reset_progress(self) -> None:
        """Reset the progress indicator to its initial state."""
        self.result_frame.reset_progress()
