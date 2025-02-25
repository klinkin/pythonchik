"""Тесты для класса ApplicationCore в core.py.

Этот модуль содержит тесты для проверки корректности работы
основного компонента приложения.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest

from pythonchik.core import ApplicationCore, ApplicationState
from pythonchik.utils.event_system import Event, EventBus, EventType


@pytest.fixture
def app_core() -> ApplicationCore:
    """Фикстура для создания экземпляра ApplicationCore.

    Returns:
        Настроенный экземпляр ApplicationCore для тестирования.

    Note:
        Создает изолированный экземпляр для каждого теста.
    """
    event_bus = EventBus()
    return ApplicationCore(event_bus)


def test_initial_state(app_core: ApplicationCore) -> None:
    """Тест начального состояния ApplicationCore.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность инициализации компонента.
    """
    assert app_core.state == ApplicationState.IDLE


def test_start_stop(app_core: ApplicationCore) -> None:
    """Тест запуска и остановки фонового потока.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность запуска и остановки фонового потока.
    """
    app_core.start()
    assert app_core._is_running is True
    assert app_core._worker_thread is not None
    assert app_core._worker_thread.is_alive()

    app_core.stop()
    assert app_core._is_running is False
    assert not app_core._worker_thread.is_alive()


def test_task_processing(app_core: ApplicationCore) -> None:
    """Тест обработки задач.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность обработки задач и изменения состояния.
    """
    result = []

    def test_task():
        result.append(1)
        return True

    app_core.start()
    app_core.add_task(test_task)

    # Даем время на выполнение задачи
    import time

    time.sleep(0.1)

    assert len(result) == 1
    assert result[0] == 1
    assert app_core.state == ApplicationState.IDLE

    app_core.stop()


def test_error_handling(app_core: ApplicationCore) -> None:
    """Тест обработки ошибок.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность обработки ошибок в задачах.
    """
    error_events = []

    def on_error(event: Event) -> None:
        error_events.append(event)

    app_core.event_bus.subscribe(EventType.ERROR_OCCURRED, on_error)

    def failing_task():
        raise ValueError("Test error")

    app_core.start()
    app_core.add_task(failing_task)

    # Даем время на выполнение задачи
    import time

    time.sleep(0.1)

    assert len(error_events) > 0
    assert "Test error" in str(error_events[0].data)

    app_core.stop()


def test_task_with_progress(app_core: ApplicationCore) -> None:
    """Тест обработки задач с отслеживанием прогресса.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность отслеживания прогресса выполнения задачи.
    """
    progress_events = []

    def on_progress(event: Event) -> None:
        progress_events.append(event)

    app_core.event_bus.subscribe(EventType.PROGRESS_UPDATED, on_progress)

    def test_task():
        return "Success"

    app_core.start()
    app_core.handle_task(test_task, description="Test Operation")

    # Даем время на выполнение задачи
    import time

    time.sleep(0.1)

    assert len(progress_events) >= 2  # Начало и конец
    assert progress_events[0].data["progress"] == 0
    assert progress_events[-1].data["progress"] == 100
    assert "Test Operation" in progress_events[0].data["message"]

    app_core.stop()


def test_multiple_tasks(app_core: ApplicationCore) -> None:
    """Тест обработки нескольких задач.

    Args:
        app_core: Тестируемый экземпляр ApplicationCore

    Note:
        Проверяет корректность обработки нескольких задач в очереди.
    """
    results = []

    def task(value: int) -> None:
        results.append(value)

    app_core.start()
    for i in range(3):
        app_core.add_task(lambda i=i: task(i))

    # Даем время на выполнение задач
    import time

    time.sleep(0.2)

    assert len(results) == 3
    assert sorted(results) == [0, 1, 2]
    assert app_core.state == ApplicationState.IDLE

    app_core.stop()
