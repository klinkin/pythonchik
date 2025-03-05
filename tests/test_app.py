import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pytest

from pythonchik.core.application_core import ApplicationCore
from pythonchik.ui.app import ModernApp


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
    mock_event_bus = MagicMock()
    with patch("pythonchik.ui.app.ApplicationCore", return_value=mock_core):
        app = ModernApp(core=mock_core, event_bus=mock_event_bus)
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


def test_select_frame_by_name(app):
    """Test if frame selection updates UI components correctly."""
    app.select_frame_by_name("json")
    assert app.navigation_frame.current_tab == "json"

    app.select_frame_by_name("image")
    assert app.navigation_frame.current_tab == "image"
