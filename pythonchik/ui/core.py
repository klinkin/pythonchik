"""Основная функциональность приложения Pythonchik.

Описание:
    Этот модуль обрабатывает основную логику приложения, управление состоянием
    и обработку событий, отдельно от компонентов пользовательского интерфейса.

Особенности:
    - Управление состоянием приложения
    - Система обработки событий
    - Многопоточное выполнение задач
    - Обработка ошибок
"""

import logging
from collections import defaultdict
from enum import Enum, auto
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any, Callable, Optional

from pythonchik.utils.error_handler import ErrorContext, ErrorSeverity
from pythonchik.utils.event_handlers import ErrorHandler, StateChangeHandler, UIActionHandler
from pythonchik.utils.event_system import Event, EventBus, EventHandler, EventType


class ApplicationState(Enum):
    """Перечисление возможных состояний приложения.

    Описание:
        Определяет все возможные состояния, в которых может находиться приложение.
    """

    INITIALIZING = "initializing"  # Начальная загрузка приложения
    IDLE = "idle"  # Приложение готово к работе
    PROCESSING = "processing"  # Обработка задач
    WAITING = "waiting"  # Ожидание ответа от внешних сервисов
    ERROR = "error"  # Состояние ошибки
    READY = "ready"  # Готовность к работе
    PAUSED = "paused"  # Временная приостановка обработки
    SHUTTING_DOWN = "shutting_down"  # Завершение работы приложения


class ApplicationCore:
    """Обработчик основной функциональности приложения.

    Описание:
        Ядро приложения. Управляет очередью задач и фоновым потоком.

    Особенности:
        - Управление состоянием
        - Обработка событий
        - Фоновая обработка задач
        - Обработка ошибок
        - Не знает ничего о Tkinter.

    Пример использования:
        core = ApplicationCore()
        core.add_task(some_coroutine)
        core.process_background_tasks()
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализация ядра приложения.

        Описание:
            Создает новый экземпляр ядра приложения и инициализирует все необходимые компоненты.
        """
        self.logger = logging.getLogger("pythonchik.core")
        self.event_bus = event_bus

        self._processing_queue = queue.Queue()
        self._error_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None

        self._is_running = False
        self._state_lock = threading.Lock()

        self._state = ApplicationState.IDLE

    def start(self):
        """Запуск фонового потока."""
        if not self._is_running:
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
            self.logger.info("Core started worker thread.")

    def stop(self):
        """Остановка фонового потока."""
        self._is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        self.logger.info("Core stopped.")

    def get_state(self) -> ApplicationState:
        """Получение текущего состояния приложения.

        Возвращает:
            Текущее состояние приложения
        """
        with self._state_lock:
            return self._state

    def _process_tasks(self) -> None:
        """Обработка задач в рабочем потоке."""
        while self._is_running:
            try:
                try:
                    task = self._processing_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                with self._state_lock:
                    self._update_state(self.STATE_PROCESSING)

                try:
                    result = task()
                    self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
                # except Exception as e:
                #     error_context = ErrorContext(
                #         operation="Обработка задачи", details={"error": str(e)}, severity=ErrorSeverity.ERROR
                #     )
                #     self.event_bus.publish(
                #         Event(EventType.ERROR_OCCURRED, {"error": str(e), "context": error_context})
                #     )
                #     with self._state_lock:
                #         self._update_state(self.STATE_ERROR)

                except Exception as exc:
                    self.handle_error(
                        exc,
                        ErrorContext(
                            operation="Обработка задачи",
                            details={"error": str(exc)},
                            severity=ErrorSeverity.ERROR,
                        ),
                    )

                finally:
                    self._processing_queue.task_done()
                    with self._state_lock:
                        if self._processing_queue.empty() and self._state != self.STATE_ERROR:
                            self._update_state(self.STATE_IDLE)

            except Exception as e:
                error_context = ErrorContext(
                    operation="Обработка фоновой задачи",
                    details={"error": str(e)},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте очередь задач и системные ресурсы",
                )
                self.event_bus.publish(
                    Event(
                        EventType.ERROR_OCCURRED,
                        {"error": f"Ошибка обработки задачи: {str(e)}", "context": error_context},
                    )
                )
                with self._state_lock:
                    self._update_state(self.STATE_ERROR)

    def _update_state(self, new_state: ApplicationState) -> None:
        """Атомарное обновление состояния с уведомлением.

        Аргументы:
            new_state: Новое состояние приложения
        """
        with self._state_lock:
            self._state = new_state
            self.event_bus.publish(Event(EventType.STATE_CHANGED, {"state": new_state}))

    @property
    def state(self) -> ApplicationState:
        """Получение текущего состояния приложения.

        Возвращает:
            Текущее состояние приложения
        """
        with self._state_lock:
            return self._state

    def add_task(self, task: Callable[[], Any]) -> None:
        """Добавление новой задачи в очередь обработки.

        Описание:
            Добавляет новую функцию в очередь задач для выполнения.

        Аргументы:
            task: Функция для выполнения

        Особенности:
            Задача автоматически добавляется в очередь и будет выполнена в фоновом режиме
        """
        self._processing_queue.put(task)

    def _wrap_task_with_progress(self, task: Callable[[], Any], description: str = "") -> Callable[[], Any]:
        """Оборачивает задачу для отслеживания прогресса.

        Аргументы:
            task: Исходная задача
            description: Описание операции

        Возвращает:
            Обернутую задачу с отслеживанием прогресса
        """

        def wrapped_task():
            # Публикуем начальный прогресс
            self.event_bus.publish(
                Event(
                    type=EventType.PROGRESS_UPDATED,
                    data={"progress": 0, "message": f"Начало {description}..."},
                )
            )

            try:
                result = task()

                # Публикуем завершение прогресса
                self.event_bus.publish(
                    Event(
                        type=EventType.PROGRESS_UPDATED,
                        data={"progress": 100, "message": f"{description} завершено"},
                    )
                )
                return result

            except Exception as e:
                # Публикуем ошибку
                self.event_bus.publish(Event(type=EventType.ERROR_OCCURRED, data={"error": str(e)}))
                raise

        return wrapped_task

    def handle_task(
        self,
        task: Callable[[], Any],
        description: str = "",
        on_complete: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Обработка задачи с обновлениями прогресса.

        Описание:
            Обрабатывает задачу и отправляет уведомления о прогрессе.

        Аргументы:
            task: Функция для выполнения
            description: Описание операции для обновлений прогресса
            on_complete: Опциональный обработчик завершения задачи

        Особенности:
            - Отслеживание прогресса
            - Обработка успешного выполнения и ошибок
            - Автоматическое обновление UI
            - Поддержка обратного вызова при завершении
        """

        def callback_wrapper():
            result = task()
            if on_complete:
                on_complete(result)
            return result

        wrapped_task = self._wrap_task_with_progress(callback_wrapper, description)
        self.add_task(wrapped_task)

    def process_background_tasks(self) -> None:
        """Обработка фоновых задач в очереди.

        This method runs in the main thread every 100ms
        to handle errors from _error_queue and check if the queue is empty,
        updating application state accordingly.
        """

        try:
            # Process errors in the error queue
            while not self._error_queue.empty():
                error = self._error_queue.get_nowait()
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(error)}))
                self._error_queue.task_done()

            # Update application state if needed
            with self._state_lock:
                queue_empty = self._processing_queue.empty()

                if not queue_empty and self.state != ApplicationState.PROCESSING:
                    self._update_state(ApplicationState.PROCESSING)
                elif queue_empty and self.state == ApplicationState.PROCESSING:
                    self._update_state(ApplicationState.IDLE)

        except Exception as e:
            error_context = ErrorContext(
                operation="Обработка фоновых задач",
                details={"error": str(e)},
                severity=ErrorSeverity.ERROR,
            )
            self.event_bus.publish(
                Event(
                    type=EventType.ERROR_OCCURRED,
                    data={"error": f"Ошибка обработки фоновых задач: {str(e)}", "context": error_context},
                )
            )
            self._update_state(ApplicationState.ERROR)
