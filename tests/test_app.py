import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from PIL import Image

# Мокаем _tkinter и ttk перед импортом App
tk_mock = MagicMock()
tk_mock.TK_VERSION = "8.6"
sys.modules["_tkinter"] = tk_mock

# Create a mock ttk module
ttk_mock = MagicMock()
ttk_mock.Progressbar = MagicMock


# Create a mock Style class
class MockStyle:
    def __init__(self, master=None):
        pass

    def theme_use(self, theme_name):
        pass

    def configure(self, widget, **kwargs):
        pass

    def map(self, widget, **kwargs):
        pass


ttk_mock.Style = MockStyle
sys.modules["tkinter.ttk"] = ttk_mock

import tkinter as tk
import tkinter.ttk as ttk

from pythonchik.main import App
from pythonchik.services import load_json_file
from pythonchik.ui import FileDialog, ProgressBar


@pytest.fixture
def app(monkeypatch):
    # Create a lightweight mock class for Tk
    class MockTk:
        def __init__(self):
            self._w = "."
            self.title = lambda x: None
            self.protocol = lambda x, y: None
            self.configure = lambda **kwargs: None
            self._configure = lambda cmd, cnf, kw: None
            self._options = lambda cnf: []
            self._flatten = lambda *args: []
            self.getvar = lambda: "8.6"
            self._loadtk = lambda: None
            self.call = lambda *args: None
            self.winfo_screenwidth = lambda: 1024
            self.winfo_screenheight = lambda: 768
            self.winfo_reqwidth = lambda: 200
            self.winfo_reqheight = lambda: 200
            self._commands = {}
            self.children = {}
            self.tk = self
            self._w = "."
            self._name = None
            self.master = None
            self._tkloaded = True
            self._tkargs = ()

        def createcommand(self, name, func):
            self._commands[name] = func
            return name

        def deletecommand(self, name):
            if name in self._commands:
                del self._commands[name]

        def winfo_id(self):
            return 1

        def winfo_pathname(self, id):
            return "."

        def winfo_name(self):
            return "tk"

        def _root(self):
            return self

        def getvar(self, name=""):
            return ""

        def setvar(self, name="", value=""):
            pass

        def getboolean(self, value):
            return False

        def call(self, *args):
            return ""

    root = MockTk()

    def mock_init(self, *args, **kwargs):
        self.master = None
        self._w = "."
        self.tk = root
        self._default_root = root
        self._support_default_root = True

    monkeypatch.setattr(tk.Tk, "__init__", mock_init)
    monkeypatch.setattr(tk, "_default_root", root)
    monkeypatch.setattr(tk, "_support_default_root", True)

    app_instance = App()
    yield app_instance

    # Cleanup
    monkeypatch.setattr(tk, "_default_root", None)
    monkeypatch.setattr(tk, "_support_default_root", False)


@pytest.fixture
def mock_json_data():
    return {
        "catalogs": [
            {
                "target_regions": ["Тестовый регион"],
                "target_shops": ["Тестовый магазин"],
                "offers": ["тестовый_оффер_id"],
            }
        ],
        "offers": [
            {
                "id": "тестовый_оффер_id",
                "description": "Тестовый продукт",
                "barcode": "123456789",
                "price_new": 100,
            }
        ],
        "target_shops_coords": ["Тестовый магазин"],
    }


@pytest.fixture
def mock_image():
    img = Image.new("RGB", (100, 100), color="red")
    return img


def test_show_address(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("builtins.open", mock_open()) as mock_file,
        patch("csv.writer") as mock_writer,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.show_address()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_show_image(app, mock_image, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("PIL.Image.open") as mock_open,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("zipfile.ZipFile") as mock_zip,
        patch("shutil.rmtree") as mock_rmtree,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("tkinter.messagebox.showerror") as mock_error,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.png"
        mock_dialog.return_value = [str(test_file)]
        mock_open.return_value.__enter__.return_value = mock_image

        app.show_image()

        mock_dialog.assert_called_once()
        mock_open.assert_called_once_with(str(test_file))
        mock_mkdir.assert_called_once_with(exist_ok=True)
        mock_zip.assert_called_once()
        mock_rmtree.assert_called_once_with(Path("Картинки Сжатые"))
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_convert_image_format(app, mock_image, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("PIL.Image.open") as mock_open,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("tkinter.messagebox.showerror") as mock_error,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.png"
        mock_dialog.return_value = [str(test_file)]
        mock_open.return_value.__enter__.return_value = mock_image

        app.convert_image_format()

        mock_dialog.assert_called_once()
        mock_open.assert_called_once_with(str(test_file))
        mock_mkdir.assert_called_once_with(exist_ok=True)
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_check_coordinates(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("builtins.open", mock_open()) as mock_file,
        patch("csv.writer") as mock_writer,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.check_coordinates()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once()
        mock_quit.assert_called_once()


def test_count_unique_offers(app, mock_json_data):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("builtins.open", mock_open()) as mock_file,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.count_unique_offers()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once_with(
            "Информация", "Всего офферов - 1\nУникальных офферов - 1"
        )
        mock_quit.assert_called_once()


def test_extract_barcodes(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("builtins.open", mock_open()) as mock_file,
        patch("csv.writer") as mock_writer,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.extract_barcodes()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_write_test_json(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("builtins.open", mock_open()) as mock_file,
        patch("json.dump") as mock_dump,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.write_test_json()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_dump.assert_called_once()
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_compare_prices(app, mock_json_data):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("matplotlib.pyplot.figure") as mock_figure,
        patch("matplotlib.pyplot.hist") as mock_hist,
        patch("matplotlib.pyplot.savefig") as mock_savefig,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("builtins.open", mock_open()) as mock_file,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = mock_json_data
        mock_file.return_value.read.return_value = json.dumps(mock_json_data)

        app.compare_prices()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_figure.assert_called_once()
        mock_hist.assert_called_once()
        mock_savefig.assert_called_once()
        mock_info.assert_called_once()
        mock_quit.assert_called_once()


def test_json_processor_load_file_not_found(app):
    with patch("pythonchik.services.load_json_file") as mock_load:
        mock_load.return_value = {}
        result = mock_load("nonexistent.json")
        assert result == {}


def test_json_processor_invalid_json(app):
    with patch("pythonchik.services.load_json_file") as mock_load:
        mock_load.return_value = {}
        result = mock_load("invalid.json")
        assert result == {}


def test_no_files_selected(app):
    with patch("tkinter.filedialog.askopenfilenames") as mock_dialog:
        mock_dialog.return_value = []
        with patch("tkinter.messagebox.showinfo") as mock_info:
            app.show_address()
            mock_info.assert_called_once_with("Информация", "Выберите файл(ы) JSON")


@pytest.fixture
def mock_edge_case_data():
    return {
        "catalogs": [
            {"target_regions": None, "target_shops": [], "offers": ["offer1"]}
        ],
        "offers": [{"id": "offer1", "description": "", "price_new": 0}],
        "target_shops_coords": [],
    }


def test_extract_addresses_edge_cases(app, mock_edge_case_data):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("builtins.open", create=True),
        patch("csv.writer") as mock_writer,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = mock_edge_case_data

        app.show_address()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_writer.assert_not_called()
        mock_info.assert_not_called()
        mock_quit.assert_called_once()


def test_check_coordinates_empty_data(app):
    empty_data = {"catalogs": [], "target_shops_coords": []}
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = empty_data

        app.check_coordinates()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        expected_message = (
            "Всего каталогов - 0\n"
            "Всего координат - 0\n"
            "Для адресов нашлись координаты - 0\n"
            "Для этих адресов нет координат:\n"
        )
        mock_info.assert_called_once_with("Информация", expected_message)
        mock_quit.assert_called_once()


def test_count_unique_offers_duplicates(app):
    data_with_duplicates = {
        "offers": [
            {"description": "Продукт A", "price_new": 100},
            {"description": "Продукт A", "price_new": 150},
            {"description": "Продукт B", "price_new": 200},
        ]
    }
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("builtins.open", mock_open()) as mock_file,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = data_with_duplicates
        mock_file.return_value.read.return_value = json.dumps(data_with_duplicates)

        app.count_unique_offers()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once_with(
            "Информация", "Всего офферов - 3\nУникальных офферов - 3"
        )
        mock_quit.assert_called_once()
