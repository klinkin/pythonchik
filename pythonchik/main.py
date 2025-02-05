import json
import os
import shutil
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from typing import Any, Dict, List, Optional
import csv
import matplotlib.pyplot as plt
from PIL import Image


class JsonProcessor:
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            mb.showerror("Error", "Invalid JSON file format")
            return {}
        except FileNotFoundError:
            mb.showerror("Error", f"File not found: {file_path}")
            return {}


class ImageProcessor:
    @staticmethod
    def resize_image(image_path: str, output_dir: str) -> None:
        try:
            with Image.open(image_path) as im:
                width, height = im.size
                new_size = (width // 2, height // 2)
                resized_image = im.resize(new_size)
                output_path = Path(output_dir) / f"{Path(image_path).stem}.png"
                resized_image.save(output_path, optimize=True, quality=50)
        except Exception as e:
            mb.showerror("Error", f"Failed to process image {image_path}: {str(e)}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Меню")
        self.json_processor = JsonProcessor()
        self.setup_ui()

    def setup_ui(self) -> None:
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

        button_opts = {"padx": 60, "pady": 25, "expand": True, "fill": tk.BOTH}
        for text, command in buttons:
            tk.Button(self, text=text, command=command).pack(**button_opts)

    def get_json_files(self) -> List[str]:
        files = fd.askopenfilenames(filetypes=[("JSON files", "*.json")])
        if not files:
            mb.showinfo("Информация", "Выберите файл(ы) JSON")
        return list(files)

    def get_image_files(self) -> List[str]:
        files = fd.askopenfilenames(
            filetypes=[("Image files", "*.png;*.jpg;*.webp;*.tif")]
        )
        if not files:
            mb.showinfo("Информация", "Выберите изображение(я)")
        return list(files)

    def show_address(self) -> None:
        files = self.get_json_files()
        if not files:
            return

        addresses = []
        for file_path in files:
            data = self.json_processor.load_json_file(file_path)
            for catalog in data.get("catalogs", []):
                try:
                    addresses.append(
                        catalog.get("target_regions", [catalog["target_shops"][0]])[0]
                    )
                except (KeyError, IndexError):
                    continue

        if addresses:
            output_path = f"{Path(files[-1]).stem}_addresses.csv"
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Adress"])
                writer.writerows([[addr] for addr in addresses])
            mb.showinfo("Информация", "Готово!")
        self.quit()

    def show_image(self) -> None:
        files = self.get_image_files()
        if not files:
            return

        output_dir = Path("Картинки Сжатые")
        output_dir.mkdir(exist_ok=True)

        for file_path in files:
            ImageProcessor.resize_image(file_path, str(output_dir))

        # Create zip archive
        with zipfile.ZipFile(
            "Картинки Сжатые.zip", "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            for file_path in output_dir.glob("*"):
                zf.write(file_path, file_path.name)

        shutil.rmtree(output_dir)
        mb.showinfo("Информация", "Готово!")
        self.quit()

    def check_coordinates(self) -> None:
        files = self.get_json_files()
        if not files:
            return

        segment = []
        koor = []
        nkoor = []
        count = 0

        for file_path in files:
            data = self.json_processor.load_json_file(file_path)
            for catalog in data.get("catalogs", []):
                segment.append(catalog["target_shops"][0])
            for shop in data.get("target_shops_coords", []):
                koor.append(shop)

        for shop in segment:
            if shop not in koor:
                nkoor.append(str(shop))
            else:
                count += 1

        info_message = (
            f"Всего каталогов - {len(segment)}\n"
            f"Всего координат - {len(koor)}\n"
            f"Для адресов нашлись координаты - {count}\n"
            f"Для этих адресов нет координат:\n"
            f"{', '.join(nkoor)}"
        )
        mb.showinfo("Информация", info_message)

        if nkoor:
            output_path = f"{Path(files[-1]).stem}_no_coordinates.csv"
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Address_no_coordinates"])
                writer.writerows([[addr] for addr in nkoor])

        self.quit()

    def extract_barcodes(self) -> None:
        files = self.get_json_files()
        if not files:
            return

        barcode = []
        for file_path in files:
            data = self.json_processor.load_json_file(file_path)
            for offer in data.get("offers", []):
                try:
                    if offer["barcode"] not in barcode and len(offer["barcode"]) > 5:
                        barcode.append(offer["barcode"])
                except KeyError:
                    continue

        if barcode:
            output_path = f"{Path(files[-1]).stem}_barcode.csv"
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["barcode"])
                writer.writerows([[code] for code in barcode])
            mb.showinfo("Информация", "Готово!")
        self.quit()

    def count_unique_offers(self) -> None:
        files = self.get_json_files()
        if not files:
            return

        offers = []
        count = 0
        for file_path in files:
            data = self.json_processor.load_json_file(file_path)
            for offer in data.get("offers", []):
                count += 1
                if offer["description"] not in offers:
                    offers.append(offer["description"])

        mb.showinfo(
            "Информация", f"Всего офферов - {count}\nУникальных офферов - {len(offers)}"
        )
        self.quit()

    def write_test_json(self) -> None:
        files = self.get_json_files()
        if len(files) != 1:
            mb.showinfo("Информация", "Выбери один файл json")
            return

        data = self.json_processor.load_json_file(files[0])
        json_file = {"catalogs": data.get("catalogs", [])}

        for catalog in json_file["catalogs"]:
            catalog["offers"] = [catalog["offers"][0]]

        koor = []
        for offer in data.get("offers", []):
            for catalog in json_file["catalogs"]:
                if offer["id"] == catalog["offers"][0]:
                    koor.append(offer)

        json_file["offers"] = koor
        json_file["target_shops_coords"] = data.get("target_shops_coords", [])

        output_path = f"{Path(files[0]).stem}_test.json"
        with open(output_path, "w") as outfile:
            json.dump(json_file, outfile)

        mb.showinfo("Информация", "Готово!")
        self.quit()

    def convert_image_format(self) -> None:
        files = self.get_image_files()
        if not files:
            return

        output_dir = Path("Картинки формат")
        output_dir.mkdir(exist_ok=True)

        for file_path in files:
            try:
                with Image.open(file_path) as im:
                    output_path = output_dir / f"{Path(file_path).stem}.png"
                    im.save(output_path)
            except Exception as e:
                mb.showerror("Error", f"Failed to process image {file_path}: {str(e)}")

        mb.showinfo("Информация", "Готово!")
        self.quit()

    def compare_prices(self) -> None:
        files = self.get_json_files()
        if not files:
            return

        segment = []
        price_diffs = []
        count = 0

        for file_path in files:
            data = self.json_processor.load_json_file(file_path)
            for offer in data.get("offers", []):
                if offer["description"] not in segment:
                    segment.append(offer["description"])

            for desc in segment:
                prices = []
                try:
                    for offer in data["offers"]:
                        if (
                            desc == offer["description"]
                            and offer["price_new"] not in prices
                        ):
                            prices.append(offer["price_new"])

                    if len(prices) > 1:
                        price_diffs.append(max(prices) - min(prices))
                        count += 1
                except KeyError:
                    print(f"В фиде ошибка, нет новой цены --->{desc}")

        plt.figure(figsize=(10, 8))
        plt.hist(price_diffs, bins=30)
        plt.savefig("Разница цен")

        percentage = int(count * 100 / len(segment)) if segment else 0
        info_message = (
            f"Всего уникальных офферов ---> {len(segment)}\n"
            f"Кол-во офферов, у которых разные цены ----> {count}\n"
            f"Процент офферов с разными ценами --->{percentage} %"
        )
        mb.showinfo("Информация", info_message)
        self.quit()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
