"""Управление состоянием приложения.

Этот модуль предоставляет инструменты для отслеживания и управления
состоянием приложения в централизованном виде:
- Перечисление состояний приложения (ApplicationState)
- Менеджер состояний (ApplicationStateManager)
- Публикация событий о смене состояния

Компоненты:
- ApplicationState: Перечисление всех возможных состояний приложения
- ApplicationStateManager: Класс для управления и отслеживания состояния

Примеры:
    Базовое использование:

    >>> from pythonchik.core.application_state import ApplicationState, ApplicationStateManager
    >>> from pythonchik.events.eventbus import EventBus
    >>>
    >>> event_bus = EventBus()
    >>> state_manager = ApplicationStateManager(event_bus)
    >>>
    >>> # Получение текущего состояния
    >>> current_state = state_manager.state  # ApplicationState.INITIALIZING
    >>>
    >>> # Изменение состояния
    >>> state_manager.update_state(ApplicationState.IDLE)
    >>> print(state_manager.state)  # ApplicationState.IDLE
"""

import logging
import threading
from enum import Enum
from typing import List, Optional

from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType


class ApplicationState(Enum):
    """Перечисление всех возможных состояний приложения.

    Определяет все состояния, в которых может находиться приложение в процессе
    своего жизненного цикла, от инициализации до завершения работы.

    Attributes:
        INITIALIZING: Начальная загрузка и инициализация приложения.
        IDLE: Приложение в режиме ожидания, готово к работе, нет активных задач.
        PROCESSING: Выполняется обработка задач в фоновом режиме.
        WAITING: Ожидание ответа от внешних ресурсов или сервисов.
        ERROR: Приложение находится в состоянии ошибки, требуется вмешательство.
        READY: Приложение полностью инициализировано и готово к работе.
        PAUSED: Обработка временно приостановлена пользователем.
        SHUTTING_DOWN: Идет процесс завершения работы приложения.

    Examples:
        >>> # Проверка текущего состояния
        >>> if state_manager.state == ApplicationState.ERROR:
        ...     print("Приложение находится в состоянии ошибки")
        ... elif state_manager.state == ApplicationState.PROCESSING:
        ...     print("Идет обработка данных")
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

    Управляет жизненным циклом приложения, отслеживает состояние и обеспечивает
    согласованность между всеми компонентами через публикацию событий.

    Хранит текущее состояние приложения и историю изменений, обеспечивает
    потокобезопасное изменение состояния и оповещение всех компонентов
    о смене состояния через EventBus.

    Attributes:
        _state (ApplicationState): Текущее состояние приложения.
        _state_history (List[ApplicationState]): История изменений состояния.
        _state_lock (threading.RLock): Блокировка для потокобезопасного доступа.
        _event_bus (EventBus): Шина событий для публикации изменений.
        _logger (logging.Logger): Логгер для отладочных сообщений.

    Note:
        - Потокобезопасность обеспечивается через `_state_lock`.
        - Блокировка _state_lock не удерживается во время публикации событий,
          чтобы избежать взаимных блокировок (deadlocks).
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализирует менеджер состояния приложения.

        Создает экземпляр менеджера с начальным состоянием INITIALIZING,
        настраивает логгер и подготавливает внутренние структуры данных.

        Args:
            event_bus: Экземпляр шины событий для публикации изменений состояния.

        Examples:
            >>> event_bus = EventBus()
            >>> state_manager = ApplicationStateManager(event_bus)
        """
        self._state = ApplicationState.INITIALIZING
        self._state_history = [self._state]  # Храним историю состояний
        self._state_lock = threading.RLock()  # Блокировка для потокобезопасности
        self._event_bus = event_bus
        self._logger = logging.getLogger("pythonchik.state")
        self._logger.info(f"ApplicationStateManager инициализирован: {self._state.value}")

    @property
    def state(self) -> ApplicationState:
        """Возвращает текущее состояние приложения.

        Предоставляет потокобезопасный доступ к текущему состоянию приложения.

        Returns:
            Текущее состояние приложения из перечисления ApplicationState.

        Examples:
            >>> current_state = state_manager.state
            >>> if current_state == ApplicationState.ERROR:
            ...     # Обработка ошибки
        """
        with self._state_lock:
            return self._state

    def update_state(self, new_state: ApplicationState) -> None:
        """Обновляет состояние приложения и публикует событие об изменении.

        Потокобезопасно изменяет состояние приложения на указанное,
        добавляет его в историю и публикует событие STATE_CHANGED через
        EventBus для оповещения всех компонентов.

        Args:
            new_state: Новое состояние приложения из перечисления ApplicationState.

        Note:
            Если новое состояние совпадает с текущим, изменение игнорируется и
            событие не публикуется, чтобы избежать циклических обновлений.

        Examples:
            >>> # Перевод приложения в состояние ошибки
            >>> state_manager.update_state(ApplicationState.ERROR)
            >>>
            >>> # Возврат в состояние ожидания после решения проблемы
            >>> state_manager.update_state(ApplicationState.IDLE)
        """
        if not isinstance(new_state, ApplicationState):
            raise ValueError(f"Invalid state: {new_state}. Must be an ApplicationState enum value.")

        if new_state == self._state:
            return

        # 1) Меняем состояние под локом
        with self._state_lock:
            old_state = self._state
            self._logger.info(f"Смена состояния: {old_state.name} -> {new_state.name}")
            self._state = new_state
            self._state_history.append(self._state)

        # 2) Вызываем publish() уже без лока
        event_data = {"old_state": old_state, "new_state": new_state}
        self._logger.debug(f"Публикую STATE_CHANGED, old={old_state}, new={new_state}")
        self._event_bus.publish(Event(EventType.STATE_CHANGED, data=event_data))
