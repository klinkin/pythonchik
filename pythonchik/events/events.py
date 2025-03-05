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
    timestamp: float = field(default_factory=time)
    id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))

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
