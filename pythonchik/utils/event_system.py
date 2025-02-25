"""Модуль реализации событийно-ориентированной архитектуры.

Описание:
    Данный модуль предоставляет реализацию системы событий для приложения,
    обеспечивая слабую связанность между компонентами через надежную иерархию событий.

Note:
    - Поддержка приоритетов событий
    - Асинхронная обработка событий
    - Типобезопасные обработчики событий
    - Система обработки ошибок

Пример использования:
    event_bus = EventBus()
    event_handler = MyEventHandler()
    event_bus.subscribe(EventType.DATA_UPDATED, event_handler)
    await event_bus.publish(Event(EventType.DATA_UPDATED, data={"key": "value"}))
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from queue import PriorityQueue
from threading import Lock
from time import time
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class EventPriority(Enum):
    """Уровни приоритета событий для определения порядка обработки.

    Описание:
        Определяет различные уровни приоритета для обработки событий в системе.

    Note:
        - LOW: Низкий приоритет для некритичных событий
        - NORMAL: Стандартный приоритет для большинства событий
        - HIGH: Высокий приоритет для важных событий
        - CRITICAL: Наивысший приоритет для критических событий
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventCategory(Enum):
    """Категории для различных типов событий.

    Описание:
        Определяет основные категории событий в системе для их логической группировки.
    """

    SYSTEM = auto()
    DOMAIN = auto()
    UI = auto()
    NETWORK = auto()


class EventType(Enum):
    """Перечисление типов событий приложения с категориями.

    Описание:
        Определяет все возможные типы событий в системе с их категориями и приоритетами.

    Note:
        - Системные события: изменение состояния, ошибки, настройки
        - Доменные события: обновление данных, обработка файлов
        - События UI: действия пользователя, обновление прогресса
        - Сетевые события: статус сети
    """

    # Системные события
    STATE_CHANGED = (EventCategory.SYSTEM, EventPriority.HIGH)
    ERROR_OCCURRED = (EventCategory.SYSTEM, EventPriority.CRITICAL)
    SETTINGS_CHANGED = (EventCategory.SYSTEM, EventPriority.NORMAL)

    # Доменные события
    DATA_UPDATED = (EventCategory.DOMAIN, EventPriority.NORMAL)
    FILE_PROCESSED = (EventCategory.DOMAIN, EventPriority.NORMAL)
    TASK_COMPLETED = (EventCategory.DOMAIN, EventPriority.NORMAL)
    RESOURCE_LOADED = (EventCategory.DOMAIN, EventPriority.NORMAL)

    # События UI
    UI_ACTION = (EventCategory.UI, EventPriority.LOW)
    PROGRESS_UPDATED = (EventCategory.UI, EventPriority.LOW)

    # Сетевые события
    NETWORK_STATUS = (EventCategory.NETWORK, EventPriority.HIGH)

    def __init__(self, category: EventCategory, priority: EventPriority):
        self.category = category
        self.priority = priority


@dataclass
class Event:
    """Базовый класс события с метаданными и валидацией.

    Описание:
        Представляет событие в системе с его типом, данными и метаинформацией.

    Args:
        type: Тип события
        data: Дополнительные данные события (опционально)
        source: Источник события (опционально)
        timestamp: Временная метка события (опционально)
        id: Уникальный идентификатор события (опционально)

    Note:
        - Автоматическая генерация временной метки
        - Автоматическая генерация уникального ID
        - Поддержка сравнения приоритетов
    """

    type: EventType
    data: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    timestamp: float = None
    id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time()
        if self.id is None:
            from uuid import uuid4

            self.id = str(uuid4())

    def __lt__(self, other):
        return self.type.priority.value > other.type.priority.value


class EventHandler(ABC, Generic[T]):
    """Абстрактный базовый класс для обработчиков событий с типобезопасностью.

    Описание:
        Определяет интерфейс для обработчиков событий с поддержкой типизации.

    Note:
        - Типобезопасность через Generic[T]
        - Абстрактный метод handle для реализации
    """

    def __init__(self):
        self.event_type = None

    @abstractmethod
    def handle(self, event: Event) -> Optional[T]:
        pass


class EventBus:
    """Центральный компонент управления событиями с приоритетной очередью и восстановлением после ошибок.

    Описание:
        Реализует паттерн Event Bus для управления событиями в приложении.

    Note:
        - Синглтон для глобального доступа
        - Приоритетная очередь событий
        - Асинхронная обработка
        - Механизм восстановления после ошибок
        - Потокобезопасность
    """

    _instance = None
    _handlers: Dict[EventType, List[EventHandler]] = {}
    _queue = PriorityQueue()
    _lock = Lock()
    _processing = False
    _error_handlers: List[Callable[[Exception], None]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._logger = logging.getLogger(__name__)
            self._handlers = {event_type: [] for event_type in EventType}
            self._initialized = True

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Подписка на события с типобезопасностью и обработкой приоритетов.

        Описание:
            Регистрирует обработчик для указанного типа события.

        Args:
            event_type: Тип события для подписки
            handler: Реализация типобезопасного обработчика событий
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            self._logger.debug(f"Подписка на {event_type}: {handler.__class__.__name__}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Безопасная отписка от событий.

        Описание:
            Удаляет обработчик для указанного типа события.

        Args:
            event_type: Тип события для отписки
            handler: Обработчик для удаления
        """
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
                self._logger.debug(f"Отписка от {event_type}: {handler.__class__.__name__}")

    def publish(self, event: Event) -> None:
        """Публикация события с обработкой приоритетов и восстановлением после ошибок.

        Описание:
            Помещает событие в очередь и запускает его обработку.

        Args:
            event: Объект события для публикации
        """
        self._queue.put(event)
        if not self._processing:
            self._process_queue()

    def _process_queue(self) -> None:
        """Обработка очереди событий с учетом приоритетов.

        Описание:
            Последовательно обрабатывает события из очереди.
        """
        self._processing = True
        try:
            while not self._queue.empty():
                event = self._queue.get()
                self._handle_event(event)
        finally:
            self._processing = False

    def _handle_event(self, event: Event) -> None:
        """Обработка одного события с восстановлением после ошибок.

        Описание:
            Обрабатывает одно событие, вызывая все соответствующие обработчики.

        Args:
            event: Событие для обработки
        """
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                if callable(handler):
                    handler(event)
                elif hasattr(handler, "handle"):
                    handler.handle(event)
                else:
                    raise ValueError(f"Invalid handler type: {type(handler)}")
            except Exception as e:
                self._logger.error(f"Error handling {event.type}: {str(e)}")
                for error_handler in self._error_handlers:
                    try:
                        error_handler(e)
                    except Exception as eh_error:
                        self._logger.error(f"Error in error handler: {str(eh_error)}")

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Добавление глобального обработчика ошибок.

        Описание:
            Регистрирует функцию для обработки ошибок событий.

        Args:
            handler: Функция обработки ошибок
        """
        self._error_handlers.append(handler)

    def clear_all_handlers(self) -> None:
        """Безопасная очистка всех обработчиков.

        Описание:
            Удаляет все зарегистрированные обработчики событий и ошибок.
        """
        with self._lock:
            self._handlers = {event_type: [] for event_type in EventType}
            self._error_handlers = []
            self._logger.debug("Все обработчики очищены")

    def get_handlers_count(self, event_type: Optional[EventType] = None) -> int:
        """Получение количества зарегистрированных обработчиков.

        Описание:
            Подсчитывает количество обработчиков для указанного типа события или всех событий.

        Args:
            event_type: Опциональный тип события для подсчета обработчиков

        Returns:
            int: Количество обработчиков
        """
        if event_type:
            return len(self._handlers.get(event_type, []))
        return sum(len(handlers) for handlers in self._handlers.values())

    def emit(self, event: Event) -> None:
        """Псевдоним для метода publish для обеспечения совместимости.

        Описание:
            Перенаправляет вызов к методу publish.

        Args:
            event: Событие для отправки
        """
        self.publish(event)
