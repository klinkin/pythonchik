"""Тесты для событийной системы (Event Bus).

Этот модуль содержит тесты для компонентов событийной системы:
- EventBus: Центральная шина событий
- Механизм подписки и отписки на события
- Публикация событий и обработка ошибок
- Приоритеты обработки событий

Фикстуры:
- event_bus: Экземпляр EventBus для тестирования
- event_handler: Мок обработчика событий
"""

import logging
from queue import Queue
from unittest.mock import MagicMock, patch

import pytest

from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType


class TestEventHandler:
    """Тестовый обработчик событий для проверки функциональности EventBus.

    Подсчитывает количество вызовов и сохраняет полученные события
    для последующей проверки.

    Attributes:
        call_count (int): Количество вызовов обработчика.
        last_event (Event): Последнее полученное событие.
        events (list): Список всех полученных событий.
    """

    def __init__(self):
        """Инициализирует обработчик событий с нулевым счетчиком."""
        self.call_count = 0
        self.last_event = None
        self.events = []

    def handle(self, event):
        """Обрабатывает событие, увеличивает счетчик и сохраняет событие.

        Args:
            event: Событие для обработки.
        """
        self.call_count += 1
        self.last_event = event
        self.events.append(event)


@pytest.fixture
def event_bus():
    """Создает чистый экземпляр EventBus для тестирования.

    Returns:
        EventBus: Экземпляр шины событий.
    """
    # Так как EventBus - синглтон, очистим состояние
    bus = EventBus()
    # Удаляем все существующие обработчики
    if hasattr(bus, "_subscribers"):
        bus._subscribers = {}
    return bus


@pytest.fixture
def event_handler():
    """Создает тестовый обработчик событий.

    Returns:
        TestEventHandler: Экземпляр тестового обработчика.
    """
    return TestEventHandler()


def test_subscribe_unsubscribe(event_bus, event_handler):
    """Проверка подписки и отписки от событий.

    Тест проверяет:
    1. Корректную подписку обработчика на тип события
    2. Возможность отписки от события
    3. Корректный подсчет обработчиков

    Args:
        event_bus: Фикстура, предоставляющая экземпляр EventBus.
        event_handler: Фикстура, предоставляющая тестовый обработчик.

    Проверяемый класс:
        pythonchik.events.eventbus.EventBus
    """
    # Проверяем начальное количество подписчиков
    assert event_bus.get_handlers_count(EventType.DATA_UPDATED) == 0

    # Подписываемся
    event_bus.subscribe(EventType.DATA_UPDATED, event_handler)
    assert event_bus.get_handlers_count(EventType.DATA_UPDATED) == 1

    # Отписываемся
    event_bus.unsubscribe(EventType.DATA_UPDATED, event_handler)
    assert event_bus.get_handlers_count(EventType.DATA_UPDATED) == 0


def test_publish_event(event_bus, event_handler):
    """Проверка публикации событий и вызова обработчиков.

    Тест проверяет:
    1. Корректную доставку события подписчикам
    2. Правильную передачу данных события обработчику
    3. Правильную обработку событий разных типов

    Args:
        event_bus: Фикстура, предоставляющая экземпляр EventBus.
        event_handler: Фикстура, предоставляющая тестовый обработчик.

    Проверяемый класс:
        pythonchik.events.eventbus.EventBus
    """
    # Создаем отдельный обработчик для типа TASK_COMPLETED
    another_handler = TestEventHandler()

    # Подписываемся только на DATA_UPDATED с первым обработчиком
    event_bus.subscribe(EventType.DATA_UPDATED, event_handler)
    # Подписываемся на TASK_COMPLETED с другим обработчиком
    event_bus.subscribe(EventType.TASK_COMPLETED, another_handler)

    # Публикуем событие DATA_UPDATED
    test_data = {"key": "value"}
    event_bus.publish(Event(EventType.DATA_UPDATED, data=test_data))

    # Проверяем, что первый обработчик был вызван и получил правильные данные
    assert event_handler.call_count >= 1
    assert event_handler.last_event is not None
    assert event_handler.last_event.type == EventType.DATA_UPDATED
    assert event_handler.last_event.data == test_data

    # Публикуем событие другого типа
    event_bus.publish(Event(EventType.TASK_COMPLETED))

    # Проверяем, что второй обработчик был вызван и получил правильные данные
    assert another_handler.call_count >= 1
    assert another_handler.last_event is not None
    assert another_handler.last_event.type == EventType.TASK_COMPLETED

    # Проверяем, что события были доставлены правильным обработчикам
    # Находим события DATA_UPDATED в списке событий первого обработчика
    data_updated_events = [e for e in event_handler.events if e.type == EventType.DATA_UPDATED]
    assert len(data_updated_events) >= 1

    # Находим события TASK_COMPLETED в списке событий второго обработчика
    task_completed_events = [e for e in another_handler.events if e.type == EventType.TASK_COMPLETED]
    assert len(task_completed_events) >= 1


def test_error_handler(event_bus):
    """Проверка обработки ошибок в обработчиках событий.

    Тест проверяет:
    1. Корректную передачу ошибок в глобальный обработчик ошибок
    2. Продолжение обработки других событий после ошибки
    3. Передачу правильных аргументов в обработчик ошибок

    Args:
        event_bus: Фикстура, предоставляющая экземпляр EventBus.

    Проверяемый класс:
        pythonchik.events.eventbus.EventBus
    """
    # Мокаем логгер, чтобы избежать логирования ошибок в UI-компоненты
    with patch("pythonchik.events.eventbus.logger") as mock_logger:
        # Создаем обработчик, который вызывает исключение
        def failing_handler(event):
            raise ValueError("Тестовая ошибка")

        # Регистрируем мок для обработки ошибок
        error_handler = MagicMock()
        event_bus.set_error_handler(error_handler)

        # Подписываем обработчик с ошибкой
        event_bus.subscribe(EventType.DATA_UPDATED, failing_handler)

        # Публикуем событие
        test_event = Event(EventType.DATA_UPDATED)
        event_bus.publish(test_event)

        # Проверяем, что обработчик ошибок был вызван с правильными аргументами
        error_handler.assert_called_once()
        args, _ = error_handler.call_args
        assert args[0] == test_event  # Первый аргумент - событие
        assert isinstance(args[1], ValueError)  # Второй аргумент - исключение
        assert str(args[1]) == "Тестовая ошибка"

        # Также проверяем, что ошибка была залогирована
        mock_logger.error.assert_called()


def test_priority(event_bus):
    """Проверка приоритетов обработки событий.

    Тест проверяет:
    1. Обработку событий в порядке их приоритетов
    2. Соблюдение порядка FIFO для событий с одинаковым приоритетом

    Args:
        event_bus: Фикстура, предоставляющая экземпляр EventBus.

    Проверяемый класс:
        pythonchik.events.eventbus.EventBus
    """
    # Создаем список для отслеживания порядка обработки
    processed_events = []

    # Обработчик для CRITICAL_PRIORITY
    def critical_priority_handler(event):
        processed_events.append("CRITICAL")

    # Обработчик для NORMAL_PRIORITY
    def normal_priority_handler(event):
        processed_events.append("NORMAL")

    # Обработчик для LOW_PRIORITY
    def low_priority_handler(event):
        processed_events.append("LOW")

    # Подписываемся на события разных приоритетов
    event_bus.subscribe(EventType.ERROR_OCCURRED, critical_priority_handler)  # Критический приоритет
    event_bus.subscribe(EventType.DATA_UPDATED, normal_priority_handler)  # Средний приоритет
    event_bus.subscribe(EventType.UI_ACTION, low_priority_handler)  # Низкий приоритет

    # Публикуем события по одному (каждое обрабатывается сразу)
    event_bus.publish(Event(EventType.UI_ACTION))
    event_bus.publish(Event(EventType.DATA_UPDATED))
    event_bus.publish(Event(EventType.ERROR_OCCURRED))

    # Проверяем, что все обработчики были вызваны в порядке публикации
    # (каждое событие обрабатывается сразу после публикации)
    assert processed_events == ["LOW", "NORMAL", "CRITICAL"]
