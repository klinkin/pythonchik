"""
Модуль реализации событийно-ориентированной архитектуры (Event Bus).

Это усовершенствованная версия, которая:
- Не вызывает подписчиков (обработчики) под локом, снижая риск дедлоков.
- Использует приоритетную очередь для порядка обработки (EventType хранит приоритет).
- Предоставляет интерфейс подписки/отписки на события (thread-safe).
- Поддерживает глобальные обработчики ошибок.
- Логирует ключевые операции (подписка, отписка, публикация, ошибки).

Пример использования:
    event_bus = EventBus()
    handler = MyEventHandler()
    event_bus.subscribe(EventType.DATA_UPDATED, handler)
    event_bus.publish(Event(EventType.DATA_UPDATED, data={"key": "value"}))
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from queue import PriorityQueue
from threading import Lock
from time import time
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class EventPriority(Enum):
    """Уровни приоритета событий для определения порядка обработки.

    LOW: Низкий приоритет для некритичных событий.
    NORMAL: Стандартный приоритет для большинства событий.
    HIGH: Высокий приоритет для важных событий.
    CRITICAL: Наивысший приоритет для критических событий.
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventCategory(Enum):
    """Категории для различных типов событий."""

    SYSTEM = auto()
    DOMAIN = auto()
    UI = auto()
    NETWORK = auto()


class EventType(Enum):
    """Перечисление типов событий с категориями и приоритетами.

    Атрибуты:
        category (EventCategory): Категория события.
        priority (EventPriority): Приоритет события.
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
    """Событие в системе с метаданными и валидацией.

    Args:
        type (EventType): Тип события (с приоритетом и категорией).
        data (Optional[Dict[str, Any]]): Дополнительные данные события.
        source (Optional[str]): Источник события (например, имя модуля).
        timestamp (float): Временная метка (по умолчанию time()).
        id (str): Уникальный идентификатор события (по умолчанию uuid4()).
    """

    type: EventType
    data: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    timestamp: float = None
    id: str = None

    priority_key: int = field(init=False, repr=False)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time()
        if self.id is None:
            from uuid import uuid4

            self.id = str(uuid4())

        # Инвертируем приоритет, чтобы CRITICAL (3) -> -3, что "меньше" для PriorityQueue
        self.priority_key = -self.type.priority.value

    def __lt__(self, other: "Event") -> bool:
        """Сравнение приоритетов: более высокий приоритет - 'меньше' для PriorityQueue.

        Если приоритеты одинаковые, сортировка идёт по времени создания (старые первыми).
        """
        if self.priority_key == other.priority_key:
            return self.timestamp < other.timestamp  # FIFO для одинаковых приоритетов
        return self.priority_key < other.priority_key  # CRITICAL (-3) -> LOW (0)


class EventHandler(ABC, Generic[T]):
    """Абстрактный класс для обработчиков событий с поддержкой типизации.

    Наследуйтесь от него и реализуйте метод handle(event).
    """

    def __init__(self):
        self.event_type = None  # Для дополнительной валидации, если нужно.

    @abstractmethod
    def handle(self, event: Event) -> Optional[T]:
        """Основной метод обработки события.

        Args:
            event (Event): Событие для обработки.

        Returns:
            Optional[T]: Результат обработки, если есть.
        """
        pass


class EventBus:
    """Центральный компонент управления событиями с приоритетной очередью.

    Реализует паттерн Event Bus:
    - Потокобезопасная подписка/отписка.
    - Приоритетная очередь для publish().
    - Обработчики вызываются последовательно в _process_queue() (синхронно).
    - Не вызывает обработчики под локом, избегая дедлоков.
    """

    _instance = None

    def __new__(cls):
        """Синглтон, чтобы иметь общий EventBus во всём приложении."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._logger = logging.getLogger(__name__)
            self._lock = Lock()
            self._queue = PriorityQueue()  # Храним события (Event)
            self._handlers: Dict[EventType, List[EventHandler]] = {}
            for et in EventType:
                self._handlers[et] = []  # Инициализируем списки обработчиков
            self._error_handlers: List[Callable[[Exception], None]] = []
            self._processing = False
            self._initialized = True

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Подписка на события.

        Args:
            event_type (EventType): Тип события для подписки.
            handler (EventHandler): Обработчик события.
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            self._logger.debug(f"Подписка на {event_type}: {handler.__class__.__name__}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Отписка от событий.

        Args:
            event_type (EventType): Тип события.
            handler (EventHandler): Обработчик для удаления.
        """
        with self._lock:
            if event_type in self._handlers:
                before_count = len(self._handlers[event_type])
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
                after_count = len(self._handlers[event_type])
                self._logger.debug(
                    f"Отписка от {event_type}: {handler.__class__.__name__}. "
                    f"Было {before_count}, стало {after_count}."
                )

    def publish(self, event: Event, immediate: bool = True) -> None:
        """
        Публикация события с учётом приоритета.

        Args:
            event (Event): Событие для публикации.
            immediate (bool): Если True (по умолчанию), событие обрабатывается немедленно,
                иначе событие просто кладётся в очередь, а дальнейшая обработка
                произойдёт при явном вызове _process_queue() или в другой момент.
        """
        self._logger.debug(f"Публикую событие: {event.type}, ID={event.id}, приоритет={event.type.priority}")
        self._queue.put(event)

        # Если immediate=True и сейчас не идёт обработка, запускаем _process_queue()
        if immediate and not self._processing:
            self._process_queue()

    def _process_queue(self) -> None:
        """Обработка очереди событий (синхронно), без удержания лока при вызове обработчиков."""
        self._processing = True
        try:
            while not self._queue.empty():
                event = self._queue.get()
                self._logger.debug(f"Взяли событие из очереди: {event.type}, ID={event.id}")
                self._handle_event(event)
        finally:
            self._processing = False
            self._logger.debug("Обработка очереди завершена.")

    def _handle_event(self, event: Event) -> None:
        """Внутренняя обработка одного события, вызывает подписчиков."""
        with self._lock:
            # Копируем список подписчиков под локом, а вызываем колбэки уже вне лока.
            handlers = self._handlers.get(event.type, [])[:]

        self._logger.debug(f"Обработка события {event.type}, подписчиков: {len(handlers)}, ID={event.id}")

        for handler in handlers:
            try:
                if callable(handler):
                    # handler -- это функция, а не класс
                    self._logger.debug(f"Вызываю функцию-обработчик {handler} для {event.type}")
                    handler(event)
                elif hasattr(handler, "handle"):
                    # handler -- EventHandler
                    self._logger.debug(f"Вызываю метод handle() у {handler.__class__.__name__}")
                    handler.handle(event)
                else:
                    raise ValueError(f"Invalid handler type: {type(handler)}")
            except Exception as e:
                self._logger.error(
                    f"Ошибка в обработчике {handler} при событии {event.type}: {str(e)}", exc_info=True
                )
                for error_handler in self._error_handlers:
                    try:
                        error_handler(e)
                    except Exception as eh_error:
                        self._logger.error(f"Ошибка в error_handler: {str(eh_error)}", exc_info=True)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Добавление глобального обработчика ошибок.

        Args:
            handler (Callable[[Exception], None]): Функция, которая примет Exception.
        """
        self._error_handlers.append(handler)
        self._logger.debug(f"Добавлен global error handler: {handler}")

    def clear_all_handlers(self) -> None:
        """Удаляет все зарегистрированные обработчики событий и ошибок."""
        with self._lock:
            for et in self._handlers:
                self._handlers[et].clear()
            self._error_handlers.clear()
            self._logger.debug("Очищены все обработчики событий и ошибок.")

    def get_handlers_count(self, event_type: Optional[EventType] = None) -> int:
        """Возвращает количество подписчиков для указанного event_type (или всех).

        Args:
            event_type (Optional[EventType]): Тип события для подсчета (или None для всех).

        Returns:
            int: Число обработчиков.
        """
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type, []))
            return sum(len(hlist) for hlist in self._handlers.values())
