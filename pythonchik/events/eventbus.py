"""Модуль реализации событийно-ориентированной архитектуры (Event Bus).

Обеспечивает слабое связывание компонентов через механизм публикации
и подписки на события. Модуль реализует паттерн Наблюдатель (Observer)
в масштабе всего приложения.

Возможности:
- Потокобезопасная подписка/отписка на события
- Приоритезация обработки событий через очередь с приоритетами
- Обработчики вызываются вне блокировок, снижая риск дедлоков
- Возможность глобальной обработки ошибок
- Подробное логирование операций и ошибок

Классы:
- EventBus: Центральный компонент для управления событиями
- EventHandlerWrapper: Обертка для безопасного вызова обработчиков

Примеры:
    Базовое использование:

    >>> from pythonchik.events.eventbus import EventBus
    >>> from pythonchik.events.events import Event, EventType
    >>>
    >>> # Получение экземпляра шины событий
    >>> event_bus = EventBus()
    >>>
    >>> # Подписка на событие
    >>> def on_data_updated(event):
    ...     print(f"Данные обновлены: {event.data}")
    ...
    >>> event_bus.subscribe(EventType.DATA_UPDATED, on_data_updated)
    >>>
    >>> # Публикация события
    >>> event_bus.publish(Event(EventType.DATA_UPDATED, data={"key": "value"}))
    Данные обновлены: {'key': 'value'}

    Обработка ошибок:

    >>> def global_error_handler(event, exception):
    ...     print(f"Ошибка при обработке {event.type}: {exception}")
    ...
    >>> event_bus.set_error_handler(global_error_handler)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from queue import PriorityQueue
from threading import Lock
from time import time
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar

from pythonchik.events.events import Event, EventType
from pythonchik.events.handlers import EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """Центральный компонент управления событиями с приоритетной очередью.

    Реализует паттерн "Шина событий" (Event Bus) для слабого связывания
    компонентов системы. Обеспечивает механизм публикации событий и
    подписки на них с соблюдением приоритетов обработки.

    Attributes:
        _subscribers (Dict): Словарь подписчиков по типам событий.
        _handlers_lock (Lock): Блокировка для потокобезопасных операций с подписчиками.
        _error_handler (Callable): Функция для централизованной обработки ошибок.

    Note:
        Класс реализован как синглтон, чтобы обеспечить один экземпляр
        шины событий для всего приложения.
    """

    _instance = None

    def __new__(cls):
        """Реализует паттерн Синглтон для шины событий.

        Returns:
            EventBus: Единственный экземпляр класса EventBus.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализирует шину событий при первом создании экземпляра."""
        # Инициализируем только один раз
        if not hasattr(self, "_initialized"):
            self._subscribers: Dict[EventType, List[EventHandler]] = {}
            self._handlers_lock = Lock()
            self._error_handler = None
            self._initialized = True
            logger.debug("EventBus инициализирована")

    def subscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Подписывает обработчик на указанный тип события.

        Регистрирует обработчик для получения уведомлений о событиях
        указанного типа. Операция потокобезопасна.

        Args:
            event_type: Тип события для подписки.
            handler: Обработчик, который будет вызван при публикации события.

        Returns:
            bool: True если подписка успешна, False если обработчик уже подписан.

        Examples:
            >>> event_bus = EventBus()
            >>> event_bus.subscribe(EventType.USER_LOGIN, user_login_handler)
        """
        with self._handlers_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            # Проверка на дубликаты
            if handler in self._subscribers[event_type]:
                logger.warning(f"Попытка повторной подписки обработчика {handler} на событие {event_type}")
                return False

            self._subscribers[event_type].append(handler)
            logger.debug(f"Добавлен обработчик {handler} для события {event_type}")
            return True

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Отписывает обработчик от указанного типа события.

        Удаляет регистрацию обработчика для указанного типа события.
        Операция потокобезопасна.

        Args:
            event_type: Тип события для отписки.
            handler: Обработчик, который больше не должен получать события.

        Returns:
            bool: True если отписка успешна, False если обработчик не был подписан.

        Examples:
            >>> event_bus = EventBus()
            >>> event_bus.unsubscribe(EventType.USER_LOGIN, user_login_handler)
        """
        with self._handlers_lock:
            if event_type not in self._subscribers:
                logger.warning(f"Попытка отписки от отсутствующего типа события {event_type}")
                return False

            if handler not in self._subscribers[event_type]:
                logger.warning(f"Попытка отписки необработчика {handler} от события {event_type}")
                return False

            self._subscribers[event_type].remove(handler)
            logger.debug(f"Удален обработчик {handler} для события {event_type}")

            # Очистка пустого списка
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

            return True

    def publish(self, event: Event) -> None:
        """Публикует событие для всех подписанных обработчиков.

        Уведомляет всех подписчиков о наступлении события с учетом
        приоритета типа события.

        Args:
            event: Экземпляр события для публикации.

        Examples:
            >>> event_bus = EventBus()
            >>> event = Event(EventType.FILE_CREATED, data={"path": "/tmp/file.txt"})
            >>> event_bus.publish(event)
        """
        handlers = []

        # Собираем обработчики без удержания блокировки во время вызовов
        with self._handlers_lock:
            if event.type in self._subscribers:
                handlers = list(self._subscribers[event.type])

        # Формируем приоритетную очередь
        priority_queue = PriorityQueue()
        for handler in handlers:
            # Обертываем для безопасного вызова
            wrapper = EventHandlerWrapper(handler, event, self._error_handler)
            # Приоритет = (приоритет_типа, отрицательное_время) для FIFO при равных приоритетах
            priority = (event.type.priority, -time())
            priority_queue.put((priority, wrapper))

        # Обработка событий в порядке приоритета
        while not priority_queue.empty():
            _, handler_wrapper = priority_queue.get()
            handler_wrapper.call()

    def set_error_handler(self, handler: Callable[[Event, Exception], None]) -> None:
        """Устанавливает обработчик ошибок для всех событий.

        Регистрирует функцию, которая будет вызываться при возникновении
        исключений в обработчиках событий.

        Args:
            handler: Функция для обработки ошибок.
                Первый аргумент - событие, второй - возникшее исключение.

        Examples:
            >>> def global_error_handler(event, exception):
            ...     logger.error(f"Ошибка при обработке {event.type}: {exception}")
            ...
            >>> event_bus.set_error_handler(global_error_handler)
        """
        self._error_handler = handler
        logger.debug(f"Установлен глобальный обработчик ошибок: {handler}")

    def clear_all_handlers(self) -> None:
        """Удаляет все зарегистрированные обработчики событий и ошибок.

        Этот метод используется в основном для тестирования, чтобы
        обеспечить чистое состояние EventBus между тестами.

        Returns:
            None
        """
        with self._handlers_lock:
            self._subscribers = {}
            self._error_handler = None
            logger.debug("Очищены все обработчики событий и ошибок.")

    def get_handlers_count(self, event_type: Optional[EventType] = None) -> int:
        """Возвращает количество зарегистрированных обработчиков.

        Args:
            event_type: Тип события для подсчета обработчиков.
                Если None, возвращает общее количество.

        Returns:
            int: Число обработчиков.
        """
        with self._handlers_lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            return sum(len(hlist) for hlist in self._subscribers.values())


class EventHandlerWrapper:
    """Безопасная обертка для вызова обработчика события.

    Инкапсулирует вызов обработчика события с обработкой исключений
    и логированием. Используется внутри EventBus для безопасного
    выполнения обработчиков.

    Attributes:
        handler (EventHandler): Обработчик события.
        event (Event): Событие для обработки.
        error_handler (Callable): Функция для обработки ошибок (опционально).
    """

    def __init__(
        self,
        handler: EventHandler,
        event: Event,
        error_handler: Optional[Callable[[Event, Exception], None]] = None,
    ) -> None:
        """Инициализирует обертку обработчика.

        Args:
            handler: Обработчик события для вызова.
            event: Событие, которое будет передано обработчику.
            error_handler: Функция для обработки ошибок (опционально).
        """
        self.handler = handler
        self.event = event
        self.error_handler = error_handler

    def call(self) -> None:
        """Вызывает обработчик события с безопасной обработкой ошибок.

        Если вызов обработчика приведет к ошибке, она будет перехвачена,
        залогирована и передана в error_handler, если он указан.
        """
        try:
            if callable(self.handler):
                # handler -- это функция, а не класс
                logger.debug(f"Вызываю функцию-обработчик {self.handler} для {self.event.type}")
                self.handler(self.event)
            elif hasattr(self.handler, "handle"):
                # handler -- EventHandler
                logger.debug(f"Вызываю метод handle() у {self.handler.__class__.__name__}")
                self.handler.handle(self.event)
            else:
                raise ValueError(f"Неверный тип обработчика: {type(self.handler)}")
        except Exception as e:
            logger.error(
                f"Ошибка в обработчике {self.handler} при событии {self.event.type}: {str(e)}", exc_info=True
            )
            if self.error_handler:
                try:
                    self.error_handler(self.event, e)
                except Exception as eh_error:
                    logger.error(f"Ошибка в error_handler: {str(eh_error)}", exc_info=True)
