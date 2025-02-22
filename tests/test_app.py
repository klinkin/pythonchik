import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pytest

from pythonchik.ui.app import ModernApp
from pythonchik.ui.core import ApplicationCore


@pytest.fixture
def mock_settings_manager():
    settings_manager = MagicMock()
    settings_manager.get_theme.return_value = "light"
    return settings_manager


@pytest.fixture
def mock_core(mock_settings_manager):
    core = MagicMock(spec=ApplicationCore)
    core.settings_manager = mock_settings_manager
    return core


@pytest.fixture
def app(monkeypatch, mock_core):
    with patch("pythonchik.ui.app.ApplicationCore", return_value=mock_core):
        app = ModernApp()
        yield app
        app.destroy()


def test_app_initialization(app, mock_core):
    """Test if the app initializes correctly with proper settings."""
    assert isinstance(app, ctk.CTk)
    assert app.core == mock_core
    assert app.title() == "Pythonchik by Dima Svirin"
    assert app.winfo_width() >= 1200
    assert app.winfo_height() >= 800


def test_ui_components_creation(app):
    """Test if all UI components are created and properly configured."""
    assert hasattr(app, "navigation_frame")
    assert hasattr(app, "action_menu")
    assert hasattr(app, "result_frame")
    assert hasattr(app, "log_frame")


def test_tab_switching(app):
    """Test if tab switching functions work correctly."""
    app.show_json_tab()
    assert app.navigation_frame.current_tab == "json"

    app.show_image_tab()
    assert app.navigation_frame.current_tab == "image"

    app.show_analysis_tab()
    assert app.navigation_frame.current_tab == "analysis"


def test_appearance_mode_change(app, mock_settings_manager):
    """Test if appearance mode changes correctly."""
    app.change_appearance_mode("Тёмная")
    mock_settings_manager.set_theme.assert_called_once_with("dark")

    app.change_appearance_mode("Светлая")
    mock_settings_manager.set_theme.assert_called_with("light")


def test_select_frame_by_name(app):
    """Test if frame selection updates UI components correctly."""
    app.select_frame_by_name("json")
    assert app.navigation_frame.current_tab == "json"

    app.select_frame_by_name("image")
    assert app.navigation_frame.current_tab == "image"


def test_error_handling(app):
    """Test if error handling works correctly."""
    test_error = Exception("Test error")
    app._handle_error(test_error, "test operation")
    assert "Ошибка при test operation" in app.log_frame.get_log()


@patch("tkinter.filedialog.askopenfilenames")
@patch("pythonchik.utils.load_json_file")
def test_extract_addresses(mock_load_json, mock_file_dialog, app):
    """Test if address extraction works correctly."""
    mock_file_dialog.return_value = ["/path/to/test.json"]
    mock_load_json.return_value = {"addresses": ["Test Address 1", "Test Address 2"]}

    app.extract_addresses()
    mock_load_json.assert_called_once()
    assert "Начало обработки файлов" in app.log_frame.get_log()


@patch("tkinter.filedialog.askopenfilenames")
@patch("pythonchik.utils.image.ImageProcessor.compress_multiple_images")
def test_compress_images(mock_compress, mock_file_dialog, app):
    """Test if image compression works correctly."""
    mock_file_dialog.return_value = ["/path/to/image.jpg"]
    mock_compress.return_value = ["/path/to/compressed/image.jpg"]

    app.compress_images()
    mock_compress.assert_called_once()
    assert "Начало процесса сжатия изображений" in app.log_frame.get_log()
