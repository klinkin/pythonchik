import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

# Mock _tkinter before importing App
tk_mock = MagicMock()
tk_mock.TK_VERSION = "8.6"
sys.modules["_tkinter"] = tk_mock
import tkinter as tk
from pythonchik.main import App


@pytest.fixture
def app():
    with (
        patch("tkinter.Tk.getvar", return_value="8.6"),
        patch("tkinter.Tk._loadtk", return_value=None),
    ):
        return App()


@pytest.fixture
def mock_json_data():
    return {
        "catalogs": [
            {
                "target_regions": ["Test Region"],
                "target_shops": ["Test Shop"],
                "offers": ["test_offer_id"],
            }
        ],
        "offers": [
            {
                "id": "test_offer_id",
                "description": "Test Product",
                "barcode": "123456789",
                "price_new": 100,
            }
        ],
        "target_shops_coords": ["Test Shop"],
    }


@pytest.fixture
def mock_image():
    img = Image.new("RGB", (100, 100), color="red")
    return img


def test_show_address(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("builtins.open", create=True),
        patch("csv.writer") as mock_writer,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data

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
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch("builtins.open", create=True),
        patch("csv.writer") as mock_writer,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data

        app.check_coordinates()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        expected_message = (
            "Всего каталогов - 1\n"
            "Всего координат - 1\n"
            "Для адресов нашлись координаты - 1\n"
            "Для этих адресов нет координат:\n"
        )
        mock_info.assert_called_once_with("Информация", expected_message)
        mock_quit.assert_called_once()


def test_count_unique_offers(app, mock_json_data):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = mock_json_data

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
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("builtins.open", create=True),
        patch("csv.writer") as mock_writer,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data

        app.extract_barcodes()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_write_test_json(app, mock_json_data, tmp_path):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("builtins.open", create=True),
        patch("json.dump") as mock_dump,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        test_file = tmp_path / "test.json"
        mock_dialog.return_value = [str(test_file)]
        mock_load.return_value = mock_json_data

        app.write_test_json()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_dump.assert_called_once()
        mock_info.assert_called_once_with("Информация", "Готово!")
        mock_quit.assert_called_once()


def test_compare_prices(app, mock_json_data):
    with (
        patch("tkinter.filedialog.askopenfilenames") as mock_dialog,
        patch("pythonchik.main.JsonProcessor.load_json_file") as mock_load,
        patch("matplotlib.pyplot.figure") as mock_figure,
        patch("matplotlib.pyplot.hist") as mock_hist,
        patch("matplotlib.pyplot.savefig") as mock_savefig,
        patch("tkinter.messagebox.showinfo") as mock_info,
        patch.object(app, "quit") as mock_quit,
    ):
        mock_dialog.return_value = ["test.json"]
        mock_load.return_value = mock_json_data

        app.compare_prices()

        mock_dialog.assert_called_once()
        mock_load.assert_called_once()
        mock_figure.assert_called_once()
        mock_hist.assert_called_once()
        mock_savefig.assert_called_once()
        mock_info.assert_called_once()
        mock_quit.assert_called_once()


def test_json_processor_load_file_not_found(app):
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = FileNotFoundError
        with patch("tkinter.messagebox.showerror") as mock_error:
            result = app.json_processor.load_json_file("nonexistent.json")
            assert result == {}
            mock_error.assert_called_once_with(
                "Error", "File not found: nonexistent.json"
            )


def test_json_processor_invalid_json(app):
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
        with patch("tkinter.messagebox.showerror") as mock_error:
            result = app.json_processor.load_json_file("invalid.json")
            assert result == {}
            mock_error.assert_called_once_with("Error", "Invalid JSON file format")


def test_no_files_selected(app):
    with patch("tkinter.filedialog.askopenfilenames") as mock_dialog:
        mock_dialog.return_value = []
        with patch("tkinter.messagebox.showinfo") as mock_info:
            app.show_address()
            mock_info.assert_called_once_with("Информация", "Выберите файл(ы) JSON")
