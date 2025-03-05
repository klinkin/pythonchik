"""Module for centralized application state management."""

import logging
import threading
from enum import Enum
from typing import Optional

from pythonchik.utils.event_system import Event, EventBus, EventType


class ApplicationState(Enum):
    """Единый enum состояний приложения.

    Attributes:
        INITIALIZING: Начальная загрузка приложения.
        IDLE: Готово к работе, нет активных фоновых задач.
        PROCESSING: Идёт обработка задач.
        WAITING: Ожидание внешних ресурсов/сервисов.
        ERROR: Приложение перешло в состояние ошибки.
        READY: Приложение готово к работе.
        PAUSED: Приостановка обработки.
        SHUTTING_DOWN: Завершение работы приложения.
    """

    INITIALIZING = "initializing"
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    READY = "ready"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"


class ApplicationStateManager:
    """Централизованное управление состоянием приложения.

    Этот класс служит единственным источником истины для состояния приложения.
    Все изменения состояния распространяются через систему событий для обеспечения
    согласованности между всеми компонентами.

    Note:
        - Потокобезопасность достигается через `_state_lock`.
        - Не держим `_state_lock` во время `event_bus.publish(...)`, избегая взаимной блокировки.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализирует менеджер состояния.

        Args:
            event_bus: Шина событий для публикации изменений состояния
        """
        self.logger = logging.getLogger("pythonchik.core.state_manager")

        self.event_bus = event_bus

        # Лок + текущее состояние
        self._state_lock = threading.Lock()
        self._state = ApplicationState.IDLE

    @property
    def state(self) -> ApplicationState:
        """Текущее состояние приложения.

        Returns:
            ApplicationState: внутреннее состояние.
        """
        with self._state_lock:
            return self._state

    def update_state(self, new_state: ApplicationState) -> None:
        """Меняет состояние и публикует событие STATE_CHANGED, без лока во время publish.

        Централизованный метод для всех изменений состояния, гарантирующий консистентность
        и корректную публикацию событий.

        Args:
            new_state (ApplicationState): Новое состояние.

        Raises:
            ValueError: Если передано некорректное состояние.
        """
        if not isinstance(new_state, ApplicationState):
            raise ValueError(f"Invalid state: {new_state}. Must be an ApplicationState enum value.")

        if new_state == self._state:
            return

        # 1) Меняем состояние под локом
        with self._state_lock:
            old_state = self._state
            self.logger.info(f"Смена состояния: {old_state} -> {new_state}")
            self._state = new_state

        # 2) Вызываем publish() уже без лока
        event_data = {"old_state": old_state, "new_state": new_state}
        self.logger.debug(f"Публикую STATE_CHANGED, old={old_state}, new={new_state}")
        self.event_bus.publish(Event(EventType.STATE_CHANGED, data=event_data))
