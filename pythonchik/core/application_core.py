"""
Основная функциональность приложения Pythonchik.

Это ядро (Core) приложения, обрабатывающее задачи в фоновом потоке, управляет общим состоянием,
публикует события через EventBus (ошибки, прогресс, смена состояния) и обеспечивает
потокобезопасный доступ к состоянию.

Содержит:
- ApplicationCore: основной класс ядра, с очередью задач, фоновым потоком, handle_error, state-lock.
"""

import logging
import queue
import threading
from enum import Enum
from typing import Any, Callable, Optional

from pythonchik.utils.error_handler import ErrorContext, ErrorSeverity
from pythonchik.utils.event_system import Event, EventBus, EventType


class ApplicationState(Enum):
    """Состояния приложения.

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


class ApplicationCore:
    """Основное ядро приложения.

    Управляет:
    - Очередью фоновых задач (`_processing_queue`),
    - Потоком-воркером (`_worker_thread`),
    - Общим состоянием (`_state`),
    - Публикует события (ERROR_OCCURRED, TASK_COMPLETED, STATE_CHANGED) через EventBus.

    Note:
        - Потокобезопасность достигается через `_state_lock`.
        - Не держим `_state_lock` во время `event_bus.publish(...)`, избегая взаимной блокировки.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализирует ядро приложения.

        Args:
            event_bus (EventBus): Шина событий, куда будем публиковать события.
        """
        self.logger = logging.getLogger("pythonchik.core")
        self.event_bus = event_bus

        # Очередь для фоновых задач, очередь для ошибок
        self._processing_queue = queue.Queue()
        self._error_queue = queue.Queue()

        # Рабочий поток + состояние
        self._worker_thread: Optional[threading.Thread] = None
        self._is_running = False

        # Лок + текущее состояние
        self._state_lock = threading.Lock()
        self._state = ApplicationState.IDLE

        self.logger.info("ApplicationCore инициализирован.")

    def start(self) -> None:
        """Запускает фоновый поток для обработки `_processing_queue`.

        Если уже запущено, повторный вызов игнорируется.
        Устанавливает `_is_running = True` и крутит `_process_tasks()` до stop().
        """
        if not self._is_running:
            self.logger.info("Запуск фонового потока...")
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
            self.logger.info("Фоновый поток успешно запущен.")
        else:
            self.logger.warning("Попытка повторного запуска — поток уже работает.")

    def stop(self) -> None:
        """Останавливает фоновый поток, ожидает завершения.

        Ставит `_is_running = False`, кладёт None в очередь для разблокировки,
        ждёт join.
        """
        self.logger.info("Попытка остановки фонового потока...")
        self._is_running = False
        # Разблокируем очередь, если она пуста
        self._processing_queue.put(None)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
            self.logger.info("Фоновый поток остановлен.")
        else:
            self.logger.warning("Фоновый поток уже был остановлен.")

    def handle_error(self, error: Exception, error_context: ErrorContext) -> None:
        """Обрабатывает ошибку, возникшую во время задачи.

        Args:
            error (Exception): Исключение.
            error_context (ErrorContext): Доп. инфо об ошибке.

        Публикует событие ERROR_OCCURRED, кладёт ошибку в _error_queue.
        """
        self.logger.error(f"Ошибка в обработке задачи: {error}", exc_info=True)
        self._error_queue.put(error)
        self.event_bus.publish(
            Event(EventType.ERROR_OCCURRED, data={"error": str(error), "context": error_context})
        )

    def _process_tasks(self, task: Optional[Callable[[], Any]] = None) -> None:
        """Фоновая обработка задач в рабочем потоке.

        Если task передан, обрабатываем только этот task (синхронно),
        иначе — бесконечный цикл, пока `_is_running`.

        Args:
            task (Optional[Callable]): конкретная задача для единовременной обработки.
        """
        self.logger.info("Фоновый поток начал обработку задач.")

        if task:
            self.logger.info("Запущена синхронная обработка задачи (handle_task).")
            self._set_state(ApplicationState.PROCESSING)
            try:
                result = task()
                self.logger.info("Синхронная задача выполнена успешно.")
                self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
            except Exception as exc:
                self.logger.exception("Ошибка при выполнении задачи (handle_task).")
                self.handle_error(
                    exc,
                    ErrorContext(
                        operation="Обработка задачи",
                        details={"error": str(exc)},
                        severity=ErrorSeverity.ERROR,
                    ),
                )
            finally:
                if self._processing_queue.empty() and self.state != ApplicationState.ERROR:
                    self._set_state(ApplicationState.IDLE)
            return

        # Бесконечная обработка очереди, пока _is_running = True
        while self._is_running:
            try:
                self.logger.debug("Фоновый поток проверяет очередь...")
                got_task = self._processing_queue.get(timeout=0.5)
                if got_task is None:
                    self.logger.info("Получен сигнал завершения потока (None).")
                    break

                self.logger.info("Получена новая задача из очереди.")
                self._set_state(ApplicationState.PROCESSING)

                try:
                    result = got_task()
                    self.logger.info("Задача успешно выполнена.")
                    self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
                except Exception as exc:
                    self.logger.exception("Ошибка в задаче (фоновая).")
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

                # После выполнения: если очередь пуста, выходим в IDLE (если нет ошибки)
                if self._processing_queue.empty() and self.state != ApplicationState.ERROR:
                    self._set_state(ApplicationState.IDLE)

            except queue.Empty:
                self.logger.debug("Очередь пуста, ожидаем задачи...")
            except Exception as e:
                self.logger.exception("Ошибка в основном цикле фонового потока.")
                self.handle_error(
                    e,
                    ErrorContext(
                        operation="Обработка фоновой задачи",
                        details={"error": str(e)},
                        severity=ErrorSeverity.ERROR,
                    ),
                )

    def _set_state(self, new_state: ApplicationState) -> None:
        """Устанавливает состояние, без публикации STATE_CHANGED.

        Только внутренний метод! Если нужно оповещение, вызывайте _update_state().
        """
        with self._state_lock:
            old_state = self._state
            self.logger.info(f"Смена состояния: {old_state} -> {new_state}")
            self._state = new_state

    def _update_state(self, new_state: ApplicationState) -> None:
        """Меняет состояние и публикует событие STATE_CHANGED, без лока во время publish.

        Args:
            new_state (ApplicationState): Новое состояние.
        """
        # 1) Меняем состояние под локом
        with self._state_lock:
            old_state = self._state
            self.logger.info(f"Смена состояния: {old_state} -> {new_state}")
            self._state = new_state

        # 2) Вызываем publish() уже без лока
        event_data = {"old_state": old_state, "new_state": new_state}
        self.logger.debug(f"Публикую STATE_CHANGED, old={old_state}, new={new_state}")
        self.event_bus.publish(Event(EventType.STATE_CHANGED, data=event_data))

    @property
    def state(self) -> ApplicationState:
        """Текущее состояние приложения.

        Returns:
            ApplicationState: внутреннее состояние.
        """
        with self._state_lock:
            return self._state

    def add_task(self, task: Callable[[], Any]) -> None:
        """Добавляет новую задачу в очередь (фоновую).

        Args:
            task (Callable[[], Any]): функция-задача, будет выполнена в потоке.
        """
        self.logger.info("Добавлена новая задача в очередь.")
        wrapped = self._wrap_task(task)
        self._processing_queue.put(wrapped)
        # Если мы в IDLE, переключаемся в PROCESSING
        if self.state == ApplicationState.IDLE:
            self._set_state(ApplicationState.PROCESSING)

    def _wrap_task(self, task: Callable[[], Any]) -> Callable[[], Any]:
        """Оборачивает задачу, добавляя лог/события ERROR_OCCURRED при исключении."""

        def wrapped_task():
            try:
                return task()
            except Exception as e:
                self.logger.exception("Ошибка в задаче (wrapped).")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
                raise

        return wrapped_task

    def _wrap_task_with_progress(self, task: Callable[[], Any], description: str = "") -> Callable[[], Any]:
        """Оборачивает задачу для отслеживания прогресса.

        Публикует PROGRESS_UPDATED(0%) -> выполняет -> PROGRESS_UPDATED(100%)
        -> TASK_COMPLETED. При исключении PROGRESS_UPDATED(-1), ERROR_OCCURRED.
        """

        def wrapped_task():
            try:
                self.logger.info(f"Начало выполнения задачи: {description}")
                self.event_bus.publish(
                    Event(EventType.PROGRESS_UPDATED, {"progress": 0, "message": f"Начало {description}..."})
                )
                result = task()
                self.event_bus.publish(
                    Event(
                        EventType.PROGRESS_UPDATED, {"progress": 100, "message": f"{description} завершено"}
                    )
                )
                self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
                self.logger.info(f"Задача завершена успешно: {description}")
                return result
            except Exception as e:
                self.logger.exception(f"Ошибка в задаче: {description}")
                self.event_bus.publish(
                    Event(EventType.PROGRESS_UPDATED, {"progress": -1, "message": f"Ошибка: {str(e)}"})
                )
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
                raise

        return wrapped_task

    def handle_task(
        self,
        task: Callable[[], Any],
        description: str = "",
        on_complete: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Синхронно обрабатывает задачу (без очереди).

        Args:
            task: Функция (Callable), выполняющая основную логику.
            description: Описание для PROGRESS_UPDATED.
            on_complete: Колбэк, вызываемый при успехе.
        """
        self.logger.info(f"Поступила задача handle_task: {description}")

        def callback_wrapper():
            try:
                result = task()
                if on_complete:
                    on_complete(result)
                self.logger.info(f"Задача '{description}' успешно выполнена (handle_task).")
                return result
            except Exception as e:
                self.logger.exception(f"Ошибка во время handle_task: {description}")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
                raise

        wrapped = self._wrap_task_with_progress(callback_wrapper, description)
        self._process_tasks(wrapped)

    def process_background_tasks(self) -> None:
        """Вызывается из UI-треда, обрабатывает ошибки в _error_queue и проверяет состояние.

        - Читает накопленные ошибки из _error_queue, публикует EVENT=ERROR_OCCURRED.
        - Если очередь пуста, переключаемся в IDLE (если не ERROR).
        """
        self.logger.debug("Запущена обработка фоновых задач в UI-треде.")
        try:
            # Обработка ошибок из _error_queue
            while not self._error_queue.empty():
                err = self._error_queue.get_nowait()
                self.logger.warning(f"Обнаружена ошибка в фоне: {err}")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(err)}))
                self._error_queue.task_done()

            # Проверяем, пуста ли очередь
            queue_empty = self._processing_queue.empty()

            # Если есть задачи, но мы не в PROCESSING, переключаемся
            if not queue_empty and self.state != ApplicationState.PROCESSING:
                self.logger.info("Фоновые задачи активны -> PROCESSING.")
                self._update_state(ApplicationState.PROCESSING)
            elif queue_empty and self.state == ApplicationState.PROCESSING:
                self.logger.info("Очередь пуста -> IDLE.")
                self._update_state(ApplicationState.IDLE)

        except Exception as e:
            self.logger.exception("Ошибка при process_background_tasks.")
            error_ctx = ErrorContext(
                operation="Обработка фоновых задач",
                details={"error": str(e)},
                severity=ErrorSeverity.ERROR,
            )
            self.event_bus.publish(
                Event(
                    EventType.ERROR_OCCURRED,
                    {"error": f"Ошибка process_background_tasks: {str(e)}", "context": error_ctx},
                )
            )
            self._update_state(ApplicationState.ERROR)
