import time
from unittest.mock import MagicMock

import pytest

from pythonchik.core import ApplicationCore, ApplicationState
from pythonchik.utils.error_handler import ErrorContext, ErrorSeverity
from pythonchik.utils.event_system import Event, EventBus, EventType


def test_start_stop():
    bus = EventBus()
    bus.clear_all_handlers()
    core = ApplicationCore(bus)

    core.start()
    assert core._is_running
    assert core._worker_thread is not None

    core.stop()
    assert not core._is_running
    if core._worker_thread:
        assert not core._worker_thread.is_alive()


def test_add_task_and_completion():
    """
    Проверяем, что при добавлении задачи (add_task) она обрабатывается
    в фоновом потоке, и в итоге публикуется событие TASK_COMPLETED.
    """
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)
    core.start()

    def dummy_task():
        return 42

    core.add_task(dummy_task)
    time.sleep(0.3)  # дать время воркеру обработать задачу

    # Смотрим, какие события реально публиковались
    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]
    # calls — список Event, которые пошли в bus.publish(Event(...))

    # Проверяем, что есть событие type=TASK_COMPLETED, data={'result':42}
    found = any(
        (ev.type == EventType.TASK_COMPLETED and ev.data == {"result": 42})
        for ev in calls
    )
    assert found, "Не нашли событие TASK_COMPLETED с data={'result': 42}"

    core.stop()


def test_handle_error():
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)
    core.start()

    # force an error
    def fail_task():
        raise ValueError("Simulated failure")

    core.add_task(fail_task)
    time.sleep(0.3)

    # ERROR_OCCURRED должен опубликоваться
    # Аналогично проверяем все вызовы
    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]
    found_error = any(ev.type == EventType.ERROR_OCCURRED for ev in calls)
    assert found_error, "Не опубликовалось событие ERROR_OCCURRED"

    core.stop()


def test_handle_task_synchronous():
    """
    Проверяем handle_task(): синхронную обработку задачи (не через очередь).
    Должен опубликоваться TASK_COMPLETED с {'result': 'sync_result'}.
    """
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)

    def dummy_logic():
        return "sync_result"

    def on_complete(res):
        assert res == "sync_result"

    core.handle_task(dummy_logic, description="TestSync", on_complete=on_complete)

    # Смотрим события
    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]
    found_sync = any(
        (ev.type == EventType.TASK_COMPLETED and ev.data == {"result": "sync_result"})
        for ev in calls
    )
    assert found_sync, "Не нашли TASK_COMPLETED с data={'result': 'sync_result'}"

    # Проверим, что state вернулся в IDLE
    assert core.state == ApplicationState.IDLE
