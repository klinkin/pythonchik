import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        btn_info = tk.Button(self, text="1) Собрать адреса из json", command=self.show_adress)
        btn_warn = tk.Button(self, text="2) Сжать картинки в 2 раза", command=self.show_image)
        btn_koor = tk.Button(self, text="3) Проверить матчинг адресов с координатами", command=self.koor)
        btn_barcode = tk.Button(self, text="4) Собрать barcode из json", command=self.barcode)
        btn_uniq = tk.Button(
            self,
            text="5) Показать кол-во уникальных офферов, сколько всего",
            command=self.uniq,
        )
        btn_test = tk.Button(self, text="6) Записать тестовый json", command=self.test)
        btn_image_format = tk.Button(self, text="7) Поменять формат картинкам", command=self.image_format)
        btn_price = tk.Button(self, text="8) Сравнить цены", command=self.price)
        opts = {"padx": 60, "pady": 25, "expand": True, "fill": tk.BOTH}
        btn_info.pack(**opts)
        btn_warn.pack(**opts)
        btn_koor.pack(**opts)
        btn_barcode.pack(**opts)
        btn_uniq.pack(**opts)
        btn_test.pack(**opts)
        btn_image_format.pack(**opts)
        btn_price.pack(**opts)

    def show_adress(self):
        import json

        import pandas as pd

        root = tk.Tk()
        root.withdraw()
        file = fd.askopenfilenames()
        adress = []
        if len(file) > 0:
            for i in file:
                with open(i, encoding="utf-8") as f:
                    data = json.load(f)
                for j in data["catalogs"]:
                    try:
                        adress.append(j["target_regions"][0])
                    except:
                        adress.append(j["target_shops"][0])
        else:
            mb.showinfo("Информация", "Выбери файл/ы json")
        df = pd.DataFrame({"Adress": adress})
        df.to_excel(f"{i.split('/')[-1].replace('.json', '')}.xlsx", index=False)
        mb.showinfo("Информация", "Готово!")
        quit()

    def show_image(self):
        import os
        import shutil
        import zipfile

        from PIL import Image

        root = tk.Tk()
        root.withdraw()
        files = fd.askopenfilenames()
        if len(files) > 0:
            os.mkdir("Картинки Сжатые")
            for i in files:
                im = Image.open(i)
                width, height = im.size
                new_size = (width // 2, height // 2)
                resized_image = im.resize(new_size)
                resized_image.save(
                    f"Картинки Сжатые\\{i.split('/')[-1].replace('.png', '').replace('.jpg', '').replace('.webp', '')}.png",
                    optimize=True,
                    quality=50,
                )
            fantasy_zip = zipfile.ZipFile("Картинки Сжатые.zip", "w")
            for folder, subfolders, files in os.walk("Картинки Сжатые"):
                for file in files:
                    fantasy_zip.write(
                        os.path.join(folder, file),
                        os.path.relpath(os.path.join(folder, file), "Картинки Сжатые"),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
            fantasy_zip.close()
            shutil.rmtree("Картинки Сжатые")
            mb.showinfo("Информация", "Готово!")
            quit()
        else:
            mb.showinfo("Информация", "Выбери изображение/я")

    def koor(self):
        import json

        import pandas as pd

        root = tk.Tk()
        root.withdraw()
        files = fd.askopenfilenames()
        segment = []
        koor = []
        nkoor = []
        count = 0
        if len(files) > 0:
            for j in files:
                with open(f"{j}", encoding="utf-8") as f:
                    data = json.load(f)
                for i in data["catalogs"]:
                    segment.append(i["target_shops"][0])
                for i in data["target_shops_coords"]:
                    koor.append(i)
                for i in segment:
                    if i not in koor:
                        nkoor.append(str(i))
                    else:
                        count += 1
        else:
            mb.showinfo("Информация", "Файл/файлы json")
        mb.showinfo(
            "Информация",
            "Всего каталогов - "
            + str(len(segment))
            + "\n"
            + "Всего координат - "
            + str(len(koor))
            + "\n"
            + "Для адресов нашлись координаты - "
            + str(count)
            + "\n"
            + "Для этих адресов нет координат: "
            + "\n"
            + ", \n".join(nkoor),
        )
        df = pd.DataFrame({"Adress_no_coor": nkoor})
        df.to_excel(f"{j.split('/')[-1].replace('.json', '') + '_No_Coor'}.xlsx", index=False)
        quit()

    def barcode(self):
        import json

        import pandas as pd

        root = tk.Tk()
        root.withdraw()
        file = fd.askopenfilenames()
        barcode = []
        if len(file) > 0:
            for j in file:
                with open(f"{j}", encoding="utf-8") as f:
                    data = json.load(f)
                for i in data["offers"]:
                    try:
                        if i["barcode"] not in barcode and len(i["barcode"]) > 5:
                            barcode.append(i["barcode"])
                    except:
                        print("null")
        else:
            mb.showinfo("Информация", "Выбери файл/ы json")
        df = pd.DataFrame({"barcode": barcode})
        df.to_excel(f"{j.split('/')[-1].replace('.json', '') + '_barcode'}.xlsx", index=False)
        mb.showinfo("Информация", "Готово!")
        quit()

    def uniq(self):
        import json

        root = tk.Tk()
        root.withdraw()
        file = fd.askopenfilenames()
        offers = []
        count = 0
        if len(file) > 0:
            for j in file:
                with open(f"{j}", encoding="utf-8") as f:
                    data = json.load(f)
                for i in data["offers"]:
                    count += 1
                    if i["description"] not in offers:
                        offers.append(i["description"])
        else:
            mb.showinfo("Информация", "Выбери файл/ы json")
        mb.showinfo(
            "Информация",
            "Всего офферов - " + str(count) + "\n" + "Уникальных офферов - " + str(len(offers)),
        )
        quit()

    def test(self):
        import json

        root = tk.Tk()
        root.withdraw()
        file = fd.askopenfilenames()
        if len(file) == 1:
            with open(file[0], encoding="utf-8") as f:
                data = json.load(f)
            koor = []
            json_file = {}
            json_file["catalogs"] = data["catalogs"]
            for i in json_file["catalogs"]:
                i["offers"] = [i["offers"][0]]
            for i in data["offers"]:
                for j in json_file["catalogs"]:
                    if i["id"] == j["offers"][0]:
                        koor.append(i)
            json_file["offers"] = koor
            try:
                json_file["target_shops_coords"] = data["target_shops_coords"]
            except:
                print("Нет координат")
            with open(
                file[0]
                .split(
                    "/",
                )[-1]
                .replace(".json", ""),
                "w",
            ) as outfile:
                json.dump(json_file, outfile)
            mb.showinfo("Информация", "Готово!")
            quit()
        else:
            mb.showinfo("Информация", "Выбери файл json")

    def image_format(self):
        import os

        from PIL import Image

        root = tk.Tk()
        root.withdraw()
        file = fd.askopenfilenames()
        if len(file) > 0:
            os.mkdir("Картинки формат")
            for i in file:
                try:
                    im = Image.open(i)
                    im.save(
                        f"Картинки формат\\{i.split('/')[-1].replace('.tif', '').replace('.png', '').replace('.jpg', '').replace('.webp', '')}.png"
                    )
                    im.close()
                except:
                    print("Не получилось")
            mb.showinfo("Информация", "Готово!")
            quit()
        else:
            mb.showinfo("Информация", "Выбери изображение/я")

    def price(self):
        import json

        import matplotlib.pyplot as pl
        import numpy as np

        root = tk.Tk()
        root.withdraw()
        files = fd.askopenfilenames()
        segment = []
        price = []
        count = 0
        if len(files) > 0:
            for file in files:
                with open(f"{file}", encoding="utf-8") as f:
                    data = json.load(f)
                for i in data["offers"]:
                    if i["description"] not in segment:
                        segment.append(i["description"])
                for i in segment:
                    mass = []
                    try:
                        for j in data["offers"]:
                            if i == j["description"]:
                                if j["price_new"] not in mass:
                                    mass.append(j["price_new"])
                        if max(mass) - min(mass) != 0:
                            price.append(max(mass) - min(mass))
                        if len(mass) > 1:
                            count += 1
                    except:
                        print("В фиде ошибка, нет новой цены --->" + str(i))
            pl.figure(figsize=(10, 8))
            a = np.array(price)
            fig = pl.hist(a)
            pl.savefig("Разница цен")
            mb.showinfo(
                "Информация",
                "Всего уникальных офферов ---> "
                + str(len(segment))
                + "\n"
                + "Кол-во офферов, у которых разные цены ----> "
                + str(count)
                + "\n"
                + "Процент офферов с разными ценами --->"
                + str(int(count * 100 / len(segment)))
                + " %",
            )
            quit()
        else:
            mb.showinfo("Информация", "Выбери файл/ы json")


if __name__ == "__main__":
    app = App()
    app.title("Меню")
    app.mainloop()
