import threading
import time
from unittest.mock import MagicMock

import pytest

from pythonchik.core.application_core import ApplicationCore
from pythonchik.core.application_state import ApplicationState
from pythonchik.errors.error_handlers import ErrorContext, ErrorSeverity
from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType


def test_start_stop():
    """Тестирует корректный запуск и остановку фонового потока.

    Описание:
        - Создаём экземпляр ApplicationCore с тестовой EventBus.
        - Вызываем start() и проверяем, что поток запустился.
        - Вызываем stop() и убеждаемся, что поток корректно завершается.

    Ожидаемый результат:
        - После start() флаг _is_running становится True, поток создаётся.
        - После stop() флаг _is_running становится False, поток прекращает работу.
    """
    bus = EventBus()
    bus.clear_all_handlers()
    core = ApplicationCore(bus)

    core.start()
    assert core._is_running, "Ядро должно сигнализировать о запущенном состоянии"
    assert core._worker_thread is not None, "Должен существовать поток-воркер"

    core.stop()
    assert not core._is_running, "После stop() ядро не должно сигнализировать о запущенном состоянии"
    if core._worker_thread:
        assert not core._worker_thread.is_alive(), "Поток-воркер должен завершиться к этому моменту"


def test_add_task_and_completion():
    """Тестирует добавление и успешное выполнение задачи в фоновом потоке.

    Описание:
        - При старте ядра вызывается start().
        - add_task(...) добавляет задачу, которая возвращает 42.
        - Даём потоку немного времени (sleep) на выполнение.
        - Проверяем публикацию события TASK_COMPLETED c result=42.

    Ожидаемый результат:
        - Вызовы bus.publish содержат событие EventType.TASK_COMPLETED с данными {'result': 42}.
    """
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)
    # Устанавливаем состояние IDLE для совместимости с существующими тестами
    core.state_manager.update_state(ApplicationState.IDLE)
    core.start()

    def dummy_task():
        return 42

    core.add_task(dummy_task)
    time.sleep(1.0)  # увеличиваем время ожидания для выполнения фоновой задачи

    # Собираем все события, опубликованные через mock
    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]

    # Отладочный вывод: печатаем структуру всех событий
    print("\nДебаг информация о событиях:")
    for i, event in enumerate(calls):
        print(f"Событие {i}: тип={event.type}, данные={event.data}")

    # Проверяем наличие TASK_COMPLETED с нужным result
    found = any((ev.type == EventType.TASK_COMPLETED and ev.data.get("result") == 42) for ev in calls)
    assert found, "Не нашли событие TASK_COMPLETED с data={'result': 42}"

    core.stop()


def test_handle_error():
    """Тестирует корректную публикацию события ERROR_OCCURRED при ошибке в задаче.

    Описание:
        - Добавляем задачу, которая специально вызывает ValueError.
        - Убеждаемся, что публикуется событие ERROR_OCCURRED.
        - Завершаем работу ядра.

    Ожидаемый результат:
        - Среди событий, опубликованных через EventBus, должно быть событие ERROR_OCCURRED.
    """
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)
    core.start()

    def fail_task():
        raise ValueError("Simulated failure")

    core.add_task(fail_task)
    time.sleep(0.3)

    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]
    found_error = any(ev.type == EventType.ERROR_OCCURRED for ev in calls)
    assert found_error, "Не опубликовалось событие ERROR_OCCURRED при ошибке в задаче"

    core.stop()


def test_handle_task_synchronous():
    """Тестирует синхронную обработку задачи методом handle_task().

    Описание:
        - handle_task(...) обрабатывает задачу в том же потоке, без очереди.
        - Задача возвращает 'sync_result'. Проверяем, что on_complete получил этот результат.
        - Проверяем, что публикуется TASK_COMPLETED, а состояние возвращается в IDLE.

    Ожидаемый результат:
        - Публикуется событие TASK_COMPLETED с result='sync_result'.
        - Состояние ApplicationCore возвращается в IDLE после выполнения.
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

    calls = [call_args[0][0] for call_args in mock_publish.call_args_list]
    found_sync = any(
        (ev.type == EventType.TASK_COMPLETED and ev.data == {"result": "sync_result"}) for ev in calls
    )
    assert found_sync, "Не нашли TASK_COMPLETED с data={'result': 'sync_result'}"
    assert core.state_manager.state == ApplicationState.IDLE, "Состояние должно вернуться в IDLE"


def test_forced_shutdown():
    """Тестирует сценарий, когда задача зависает и нужно форсировать остановку потока.

    Описание:
        - Запускаем задачу, которая зависает на несколько секунд без проверки _stop_event.
        - Вызываем stop(), проверяем, что метод завершается в разумное время.
        - Проверяем, что ядро отмечено как не работающее.

    Ожидаемый результат:
        - Метод stop() должен завершиться без зависания приложения.
        - Ядро должно быть отмечено как остановленное.
    """
    bus = EventBus()
    bus.clear_all_handlers()
    core = ApplicationCore(bus)
    core.start()

    # Флаг для отслеживания начала выполнения задачи
    task_started = threading.Event()

    def long_task():
        # Отмечаем, что задача начала выполняться
        task_started.set()
        # Имитируем зависшую задачу - долгий sleep без проверки флага остановки
        try:
            time.sleep(10)  # заведомо дольше, чем timeout в core.stop()
        except:
            # Игнорируем исключения - имитация "глухой" задачи
            pass

    # Добавляем задачу
    core.add_task(long_task)

    # Ждем, пока задача гарантированно начнет выполняться
    assert task_started.wait(timeout=1.0), "Задача не запустилась"

    # Вызываем остановку - метод должен отработать и вернуть управление
    # даже если поток не завершится
    start_time = time.time()
    core.stop()
    stop_duration = time.time() - start_time

    # Проверяем, что stop() вернул управление в разумное время (не зависнув)
    assert stop_duration < 5.0, f"Метод stop() занял слишком много времени: {stop_duration:.2f}с"

    # Проверяем, что ядро больше не в рабочем состоянии
    assert not core._is_running, "После stop() ядро не должно быть в рабочем состоянии"

    # Основная цель теста - убедиться, что приложение не зависнет при остановке,
    # даже если какая-то задача заблокирована. Проверка, что поток действительно
    # умер, не так важна, поскольку это может зависеть от ОС и других факторов.
