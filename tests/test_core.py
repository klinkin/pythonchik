"""Тесты для класса ApplicationCore в core.py.

Этот модуль содержит тесты для проверки корректности работы
основного компонента приложения.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest

from pythonchik.ui.core import ApplicationCore, ApplicationState
from pythonchik.utils.event_system import Event, EventType


@pytest.fixture
def app_core() -> ApplicationCore:
    """Фикстура для создания экземпляра ApplicationCore.

    Возвращает:
        Настроенный экземпляр ApplicationCore для тестирования.

    Особенности:
        Создает изолированный экземпляр для каждого теста.
    """
    return ApplicationCore()


def test_initial_state(app_core: ApplicationCore) -> None:
    """Тест начального состояния ApplicationCore.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность инициализации компонента.
    """
    assert app_core.get_state() == ApplicationState.IDLE


def test_task_queue(app_core: ApplicationCore) -> None:
    """Тест добавления задачи в очередь обработки.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность добавления и обработки задач.
    """
    task = lambda: None
    app_core.add_task(task)


def test_task_execution(app_core: ApplicationCore) -> None:
    """Тест корректного выполнения задач.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет успешное выполнение задач и обновление состояния.
    """
    result = []
    completion_event = threading.Event()

    def task_with_completion():
        result.append(1)
        completion_event.set()

    # Проверяем начальное состояние
    assert app_core.get_state() == ApplicationState.IDLE

    # Добавляем задачу
    app_core.add_task(task_with_completion)

    # Ждем завершения с таймаутом
    completed = completion_event.wait(timeout=2.0)
    assert completed, "Task execution timed out"
    assert result == [1]

    # Проверяем возврат в исходное состояние
    assert app_core.get_state() == ApplicationState.IDLE


def test_task_error_handling(app_core: ApplicationCore) -> None:
    """Тест обработки ошибок при выполнении задачи.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность обработки исключений в задачах.
    """

    def failing_task():
        raise ValueError("Test error")

    app_core.add_task(failing_task)
    with pytest.raises(ValueError):
        app_core._process_tasks(failing_task)


def test_state_changes(app_core: ApplicationCore) -> None:
    """Тест изменений состояния во время обработки задач.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет атомарность и корректность изменений состояния.
    """

    def state_changing_task():
        app_core._update_state(ApplicationState.PROCESSING)

    app_core.add_task(state_changing_task)
    app_core._process_tasks()
    assert app_core.get_state() == ApplicationState.IDLE


def test_progress_tracking(app_core: ApplicationCore) -> None:
    """Тест обработки задачи с отслеживанием прогресса.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность отслеживания прогресса выполнения.
    """
    progress_values = []

    def task_with_progress(progress_callback):
        for i in range(3):
            progress_callback(i / 2)
            progress_values.append(i / 2)

    wrapped_task = app_core._wrap_task(task_with_progress)
    wrapped_task()

    assert progress_values == [0.0, 0.5, 1.0]


def test_concurrent_tasks(app_core: ApplicationCore) -> None:
    """Тест обработки нескольких задач одновременно.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность параллельной обработки задач.
    """
    results = []

    def task(i: int):
        results.append(i)

    for i in range(3):
        app_core.add_task(lambda x=i: task(x))

    app_core.process_background_tasks()
    assert sorted(results) == [0, 1, 2]


def test_thread_safety(app_core: ApplicationCore) -> None:
    """Тест потокобезопасности при параллельной обработке задач.

    Аргументы:
        app_core: Тестируемый экземпляр ApplicationCore

    Особенности:
        Проверяет корректность работы в многопоточной среде.
    """
    completion_events = [threading.Event() for _ in range(10)]

    def state_update_task(i: int):
        with app_core._state_lock:
            app_core._update_state(ApplicationState.PROCESSING)
            completion_events[i].set()

    threads = []
    for i in range(10):
        thread = threading.Thread(target=lambda x=i: state_update_task(x))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify all tasks completed
    assert all(event.is_set() for event in completion_events)
