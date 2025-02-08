import json
import shutil
import zipfile
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from typing import List

import customtkinter as ctk
import matplotlib.pyplot as plt
from PIL import Image

from pythonchik import config
from pythonchik.image_processor import ImageProcessor
from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
    load_json_file,
    save_to_csv,
)
from pythonchik.ui import BaseWindow, FileDialog, ProgressBar


class App(ctk.CTk, BaseWindow):
    """Главное окно приложения.

    Предоставляет графический интерфейс для выполнения различных операций
    с JSON файлами и изображениями.
    """

    def __init__(self):
        ctk.CTk.__init__(self)
        BaseWindow.__init__(self)
        self.title("Главное меню")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Set the theme and color scheme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configure window size and position
        self.geometry("800x600")
        self.minsize(600, 400)

        self.setup_ui()
        self.progress_bar = ProgressBar(self)

    def setup_ui(self) -> None:
        """Настройка пользовательского интерфейса."""
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame with grid
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        buttons = [
            ("1) Собрать адреса из json", self.show_address),
            ("2) Сжать картинки в 2 раза", self.show_image),
            ("3) Проверить матчинг адресов с координатами", self.check_coordinates),
            ("4) Собрать barcode из json", self.extract_barcodes),
            ("5) Показать кол-во уникальных офферов", self.count_unique_offers),
            ("6) Записать тестовый json", self.write_test_json),
            ("7) Поменять формат картинкам", self.convert_image_format),
            ("8) Сравнить цены", self.compare_prices),
        ]

        for i, (text, command) in enumerate(buttons):
            btn = ctk.CTkButton(
                self.main_frame,
                text=text,
                command=command,
                height=40,
                corner_radius=8,
                font=("Arial", 14),
            )
            btn.grid(row=i, column=0, padx=15, pady=8, sticky="ew")

    def on_close(self):
        """Обработчик закрытия окна."""
        if mb.askokcancel("Выход", "Вы действительно хотите выйти?"):
            self.destroy()

    def _process_json_files(self, processor_func):
        """Общий метод для обработки JSON файлов.

        Args:
            processor_func: Функция для обработки данных из JSON
        """
        files = FileDialog.get_json_files()
        if not files:
            return None, None

        results = []
        for file_path in files:
            data = load_json_file(file_path)
            result = processor_func(data)
            if isinstance(result, (list, tuple)):
                results.extend(result)
            else:
                results.append(result)
        return results, files

    def show_address(self) -> None:
        """Обработка адресов из JSON файлов."""
        with self.cleanup_context():
            addresses, files = self._process_json_files(extract_addresses)
            if not addresses:
                return

            if addresses:
                output_path = f"{Path(files[-1]).stem}{config.ADDRESSES_SUFFIX}.csv"
                save_to_csv(addresses, ["Адрес"], output_path)
                mb.showinfo("Информация", "Готово!")

    def show_image(self) -> None:
        """Обработка и сжатие изображений."""
        with self.cleanup_context():
            files = FileDialog.get_image_files()
            if not files:
                return

            output_dir = Path(config.COMPRESSED_IMAGES_DIR)
            output_dir.mkdir(exist_ok=True)

            total_files = len(files)
            processed_files = []
            for i, file_path in enumerate(files, 1):
                progress = (i - 1) / total_files * 100
                self.progress_bar.update(
                    progress, f"Обработка файла {i} из {total_files}..."
                )
                try:
                    ImageProcessor.resize_image(
                        file_path, str(output_dir), self.progress_bar.update
                    )
                    processed_files.append(output_dir / f"{Path(file_path).stem}.png")
                except Exception as e:
                    mb.showerror("Ошибка", str(e))

            self.progress_bar.update(90, "Создание архива...")
            with zipfile.ZipFile(
                config.COMPRESSED_IMAGES_ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED
            ) as zf:
                for file_path in processed_files:
                    if file_path.exists():
                        zf.write(file_path, file_path.name)

            self.progress_bar.update(95, "Очистка временных файлов...")
            shutil.rmtree(output_dir)

            self.progress_bar.update(100, "Готово!")
            mb.showinfo("Информация", "Готово!")

    def check_coordinates(self) -> None:
        """Проверка соответствия адресов и координат."""
        with self.cleanup_context():
            files = FileDialog.get_json_files()
            if not files:
                return

            nkoor = []
            for file_path in files:
                data = load_json_file(file_path)
                no_coords, total_catalogs, total_coords, matched_count = (
                    check_coordinates_match(data)
                )
                nkoor.extend(no_coords)

            info_message = (
                f"Всего каталогов - {total_catalogs}\n"
                f"Всего координат - {total_coords}\n"
                f"Для адресов нашлись координаты - {matched_count}\n"
                f"Для этих адресов нет координат:\n"
                f"{', '.join(nkoor)}"
            )
            mb.showinfo("Информация", info_message)

            if nkoor:
                output_path = (
                    f"{Path(files[-1]).stem}{config.NO_COORDINATES_SUFFIX}.csv"
                )
                save_to_csv(nkoor, ["Адреса без координат"], output_path)

    def extract_barcodes(self) -> None:
        """Извлечение штрих-кодов из JSON файлов."""
        with self.cleanup_context():
            barcode, files = self._process_json_files(extract_barcodes)
            if not barcode:
                return

            if barcode:
                output_path = f"{Path(files[-1]).stem}{config.BARCODE_SUFFIX}.csv"
                save_to_csv(barcode, ["barcode"], output_path)
                mb.showinfo("Информация", "Готово!")

    def count_unique_offers(self) -> None:
        """Подсчет уникальных предложений."""
        with self.cleanup_context():
            result, files = self._process_json_files(count_unique_offers)
            if not result:
                return

            total_count = sum(r[0] for r in result)
            offers = []
            for file_path in files:
                data = load_json_file(file_path)
                offers.extend(
                    [offer["description"] for offer in data.get("offers", [])]
                )

            mb.showinfo(
                "Информация",
                f"Всего офферов - {count}\nУникальных офферов - {len(offers)}",
            )

    def write_test_json(self) -> None:
        """Создание тестового JSON файла."""
        with self.cleanup_context():
            files = FileDialog.get_json_files()
            if len(files) != 1:
                mb.showinfo("Информация", "Выберите один файл json")
                return

            data = load_json_file(files[0])
            json_file = create_test_json(data)

            output_path = f"{Path(files[0]).stem}{config.TEST_JSON_SUFFIX}.json"
            with open(output_path, "w") as outfile:
                json.dump(json_file, outfile)

            mb.showinfo("Информация", "Готово!")

    def convert_image_format(self) -> None:
        """Конвертация форматов изображений."""
        with self.cleanup_context():
            files = FileDialog.get_image_files()
            if not files:
                return

            output_dir = Path(config.FORMAT_CONVERTED_IMAGES_DIR)
            output_dir.mkdir(exist_ok=True)

            for file_path in files:
                try:
                    with Image.open(file_path) as im:
                        output_path = output_dir / f"{Path(file_path).stem}.png"
                        im.save(output_path)
                except Exception as e:
                    mb.showerror(
                        "Ошибка",
                        f"Не удалось обработать изображение {file_path}: {str(e)}",
                    )

            mb.showinfo("Информация", "Готово!")

    def compare_prices(self) -> None:
        """Сравнение цен и построение графика."""
        with self.cleanup_context():
            files = FileDialog.get_json_files()
            if not files:
                return

            segment = []
            price_diffs = []
            count = 0

            for file_path in files:
                data = load_json_file(file_path)
                diffs, diff_count, total = analyze_price_differences(data)
                price_diffs.extend(diffs)
                count += diff_count
                segment.extend(
                    [offer["description"] for offer in data.get("offers", [])]
                )

            plt.figure(figsize=config.PRICE_PLOT_SIZE)
            plt.hist(price_diffs, bins=config.PRICE_PLOT_BINS)
            plt.savefig(config.PRICE_DIFF_PLOT_FILENAME)

            percentage = int(count * 100 / len(segment)) if segment else 0
            info_message = (
                f"Всего уникальных офферов ---> {len(segment)}\n"
                f"Кол-во офферов, у которых разные цены ----> {count}\n"
                f"Процент офферов с разными ценами --->{percentage} %"
            )
            mb.showinfo("Информация", info_message)


def main():
    """Точка входа в приложение."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
