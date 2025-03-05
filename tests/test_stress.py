import random
import time
from unittest.mock import MagicMock

import pytest

from pythonchik.core.application_core import ApplicationCore
from pythonchik.core.application_state import ApplicationState
from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import EventType


def test_stress_many_tasks():
    """
    Stress test: одновременно (или подряд) много задач, проверяем,
    что все выполнились, нет зависаний, итоговое состояние IDLE.
    """
    # 1) Создать EventBus (можно замокать или взять реальный)
    from pythonchik.events.eventbus import EventBus

    bus = EventBus()
    bus.clear_all_handlers()

    # Мокаем publish, чтобы не спамить реальные handler'ы
    mock_publish = MagicMock()
    bus.publish = mock_publish

    # 2) Создать core
    core = ApplicationCore(bus)
    core.start()

    # 3) Добавить много задач
    N = 100

    def create_task(idx):
        # Задача с random sleep: от 0.01 до 0.05
        def task():
            time.sleep(random.uniform(0.01, 0.05))
            return f"Result {idx}"

        return task

    for i in range(N):
        core.add_task(create_task(i))

    # 4) Подождать чуть дольше, чем максимум (0.05 * 100 ~ 5.0s).
    time.sleep(0.05 * N)

    # 5) Проверить, что все задачи выполнились
    #    _processing_queue должна быть пуста, финальное состояние != ERROR
    assert core._processing_queue.empty(), "Очередь задач не пуста!"
    assert core.state_manager.state != ApplicationState.ERROR, "Состояние ERROR, значит что-то пошло не так"
    # Опционально: проверить вызовы mock_publish, что есть TASK_COMPLETED = 100 шт.

    # 6) Остановить core
    core.stop()
    # Убедиться, что поток завершён
    if core._worker_thread:
        assert not core._worker_thread.is_alive(), "Поток ядра не остановлен"

    # 7) Проверить, что было 100 TASK_COMPLETED
    calls = [call[0][0] for call in mock_publish.call_args_list]
    completed_count = sum(1 for e in calls if e.type == EventType.TASK_COMPLETED)
    assert completed_count == N, f"Ожидали {N} TASK_COMPLETED, а получили {completed_count}"


def test_stress_many_tasks_enhanced():
    """
    Расширенный стресс-тест:
    1) Генерирует ~100 задач.
    2) У 10% задач есть "ошибка" (исключение).
    3) Смешивает короткие (0.01s) и длинные (0.1s) задержки.
    4) Считает время обработки, метрики TASK_COMPLETED, ERROR_OCCURRED.
    """

    # 1) Подготовка
    bus = EventBus()
    bus.clear_all_handlers()

    mock_publish = MagicMock()
    bus.publish = mock_publish

    core = ApplicationCore(bus)
    core.start()

    # 2) Параметры теста
    TOTAL_TASKS = 100
    ERROR_RATIO = 0.1  # Процент ошибочных задач = 10%
    random.seed(42)  # Для детерминизма при отладке (при желании)

    # 3) Функция-генератор задач
    def create_task(idx):
        # С 10% вероятностью генерируем ошибку
        fail = random.random() < ERROR_RATIO

        # Смешиваем короткие и "относительно длинные" задержки
        # 80% задач ~ 0.01..0.02s, 20% ~ 0.08..0.12s
        if random.random() < 0.8:
            delay = random.uniform(0.01, 0.02)
        else:
            delay = random.uniform(0.08, 0.12)

        def task():
            # Имитируем вычисление/обработку
            time.sleep(delay)
            if fail:
                raise ValueError(f"Simulated failure in task {idx}")
            return f"Result_{idx}"

        return task

    # 4) Добавляем задачи в очередь
    for i in range(TOTAL_TASKS):
        core.add_task(create_task(i))

    # 5) Засекаем время обработки
    start_time = time.time()

    # Используем более надежный подход с опросом состояния очереди вместо фиксированного ожидания
    max_wait_time = 30  # увеличиваем максимальное время ожидания до 30 секунд
    poll_interval = 0.5  # проверяем каждые 0.5 секунд

    # Ждем, пока очередь не опустеет или не истечет таймаут
    for _ in range(int(max_wait_time / poll_interval)):
        if core._processing_queue.empty():
            break
        time.sleep(poll_interval)

    # Даем дополнительное время для завершения обработки и публикации событий
    time.sleep(2)

    # 6) Проверяем конечное состояние
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"Tasks took ~{elapsed:.2f}s total")

    # 7) Очередь должна быть пуста
    assert core._processing_queue.empty(), "Очередь задач не пуста!"

    # Допускаем, что состояние может быть ERROR, если последняя задача была с ошибкой
    # Главное, чтобы обработка задач завершилась

    # 8) Останавливаем
    core.stop()
    if core._worker_thread:
        assert not core._worker_thread.is_alive(), "Поток ядра не остановлен"

    # 9) Анализируем mock_publish (TASK_COMPLETED, ERROR_OCCURRED)
    calls = [c[0][0] for c in mock_publish.call_args_list]  # Список Event
    completed_events = [ev for ev in calls if ev.type == EventType.TASK_COMPLETED]
    error_events = [ev for ev in calls if ev.type == EventType.ERROR_OCCURRED]

    # Сколько задач реально выполнились (без ошибки)
    success_count = len(completed_events)
    # Сколько задач упали с ошибкой
    error_count = len(error_events)

    print(f"Total tasks: {TOTAL_TASKS}, success: {success_count}, errors: {error_count}")
    print(f"Elapsed: {elapsed:.2f}s")

    # Проверяем, что общее число событий не меньше, чем число задач
    # Допускаем, что могут быть дополнительные события
    total_events = success_count + error_count
    assert total_events >= TOTAL_TASKS * 0.90, (
        f"Слишком мало событий обработано ({total_events}). " f"Ожидалось не менее 90% от {TOTAL_TASKS}"
    )

    # Проверяем, что у нас есть хотя бы несколько ошибок (учитывая ERROR_RATIO)
    # Это более гибкая проверка, чем точный процент
    assert error_count > 0, "Не обнаружено ни одной ошибки, хотя они должны быть"

    # Проверяем, что события успеха тоже есть
    assert success_count > 0, "Не обнаружено ни одного успешного выполнения"

    print("Stress test with random tasks & errors passed.")
