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

from pythonchik.core.application_state import ApplicationState, ApplicationStateManager
from pythonchik.utils.error_handler import ErrorContext, ErrorSeverity
from pythonchik.utils.event_system import Event, EventBus, EventType


class ApplicationCore:
    """Основное ядро приложения.

    Управляет:
    - Очередью фоновых задач (`_processing_queue`),
    - Потоком-воркером (`_worker_thread`),
    - Публикует события (ERROR_OCCURRED, TASK_COMPLETED) через EventBus.

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

        self.state_manager = ApplicationStateManager(event_bus)

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

    def _process_tasks(self) -> None:
        """Фоновая обработка задач в рабочем потоке.

        Если task передан, обрабатываем только этот task (синхронно),
        иначе — бесконечный цикл, пока `_is_running`.

        Args:
            task (Optional[Callable]): конкретная задача для единовременной обработки.
        """
        self.logger.info("Фоновый поток начал обработку задач.")

        # Бесконечная обработка очереди, пока _is_running = True
        while self._is_running:
            try:
                # self.logger.debug("Фоновый поток проверяет очередь...")
                got_task = self._processing_queue.get(timeout=0.5)
                if got_task is None:
                    self.logger.info("Получен сигнал завершения потока (None).")
                    break

                self.logger.info("Получена новая задача из очереди.")
                self.state_manager.update_state(ApplicationState.PROCESSING)

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
                if self._processing_queue.empty() and self.state_manager.state != ApplicationState.ERROR:
                    self.state_manager.update_state(ApplicationState.IDLE)

            except queue.Empty:
                pass
                # self.logger.debug("Очередь пуста, ожидаем задачи...")
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

    def add_task(self, task: Callable[[], Any]) -> None:
        """Добавляет новую задачу в очередь (фоновую).

        Args:
            task (Callable[[], Any]): функция-задача, будет выполнена в потоке.
        """
        self.logger.info("Добавлена новая задача в очередь.")
        wrapped = self._wrap_task(task)
        self._processing_queue.put(wrapped)

        if self.state_manager.state == ApplicationState.IDLE:
            self.state_manager.update_state(ApplicationState.PROCESSING)

    def _wrap_task(
        self, task: Callable[[], Any], description: str = "", track_progress: bool = True
    ) -> Callable[[], Any]:
        """Оборачивает задачу, добавляя обработку ошибок и опционально отслеживание прогресса.

        Публикует PROGRESS_UPDATED(0%) -> выполняет -> PROGRESS_UPDATED(100%)
        -> TASK_COMPLETED. При исключении PROGRESS_UPDATED(-1), ERROR_OCCURRED.

        Args:
            task: Функция (Callable), выполняющая основную логику.
            description: Описание для PROGRESS_UPDATED (если track_progress=True).
            track_progress: Флаг для включения отслеживания прогресса.

        Returns:
            Callable: Обёрнутая задача с обработкой ошибок и прогресса.
        """

        def wrapped_task():
            try:
                if track_progress:
                    self.logger.info(f"Начало выполнения задачи: {description}")

                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 0, "message": f"Начало выполнения задачи {description}..."},
                        )
                    )

                result = task()

                if track_progress:
                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 100, "message": f"{description} завершено"},
                        )
                    )
                    self.logger.info(f"Задача завершена успешно: {description}")

                return result
            except Exception as e:
                if track_progress:
                    self.logger.exception(f"Ошибка в задаче: {description}")
                    self.event_bus.publish(
                        Event(EventType.PROGRESS_UPDATED, {"progress": -1, "message": f"Ошибка: {str(e)}"})
                    )
                else:
                    self.logger.exception("Ошибка в задаче (wrapped).")
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

        # Обновляем состояние на PROCESSING
        self.state_manager.update_state(ApplicationState.PROCESSING)

        try:
            # Публикуем начало выполнения
            self.event_bus.publish(
                Event(
                    EventType.PROGRESS_UPDATED,
                    {"progress": 0, "message": f"Начало выполнения задачи {description}..."}
                )
            )

            # Выполняем задачу
            result = task()

            # Вызываем callback если есть
            if on_complete:
                on_complete(result)

            # Публикуем успешное завершение
            self.event_bus.publish(
                Event(
                    EventType.PROGRESS_UPDATED,
                    {"progress": 100, "message": f"{description} завершено"}
                )
            )
            self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
            self.logger.info(f"Задача '{description}' успешно выполнена (handle_task).")

            return result

        except Exception as e:
            self.logger.exception(f"Ошибка во время handle_task: {description}")
            self.event_bus.publish(
                Event(EventType.PROGRESS_UPDATED, {"progress": -1, "message": f"Ошибка: {str(e)}"})
            )
            self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
            self.state_manager.update_state(ApplicationState.ERROR)
            raise

        finally:
            # Возвращаем состояние в IDLE если нет ошибки
            if self.state_manager.state != ApplicationState.ERROR:
                self.state_manager.update_state(ApplicationState.IDLE)

    def _process_error_queue(self) -> None:
        """Обрабатывает накопленные ошибки из очереди ошибок.

        Читает все ошибки из _error_queue и публикует их как ERROR_OCCURRED события.
        """
        while not self._error_queue.empty():
            err = self._error_queue.get_nowait()
            self.logger.warning(f"Обнаружена ошибка в фоне: {err}")
            self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(err)}))
            self._error_queue.task_done()

    def _update_state_based_on_queue(self) -> None:
        """Обновляет состояние приложения на основе состояния очереди задач.

        Переключает состояние между PROCESSING и IDLE в зависимости от наличия задач.
        """
        queue_empty = self._processing_queue.empty()

        if not queue_empty and self.state_manager.state != ApplicationState.PROCESSING:
            self.logger.info("Фоновые задачи активны -> PROCESSING.")
            self.state_manager.update_state(ApplicationState.PROCESSING)
        elif queue_empty and self.state_manager.state == ApplicationState.PROCESSING:
            self.logger.info("Очередь пуста -> IDLE.")
            self.state_manager.update_state(ApplicationState.IDLE)

    def process_background_tasks(self) -> None:
        """Вызывается из UI-треда для обработки фоновых задач.

        Разделяет обработку ошибок и обновление состояния приложения
        на отдельные методы для улучшения разделения ответственности.
        """
        self.logger.debug("Запущена обработка фоновых задач в UI-треде.")
        try:
            # Разделяем обработку ошибок и состояния на отдельные методы
            self._process_error_queue()
            self._update_state_based_on_queue()
        except Exception as e:
            self._handle_background_task_error(e)

    def _handle_background_task_error(self, error: Exception) -> None:
        """Централизованная обработка ошибок фоновых задач.

        Args:
            error: Исключение, которое необходимо обработать.
        """
        self.logger.exception("Ошибка при process_background_tasks.")
        error_ctx = ErrorContext(
            operation="Обработка фоновых задач",
            details={"error": str(error)},
            severity=ErrorSeverity.ERROR,
        )
        self.event_bus.publish(
            Event(
                EventType.ERROR_OCCURRED,
                {"error": f"Ошибка process_background_tasks: {str(error)}", "context": error_ctx},
            )
        )

        self.state_manager.update_state(ApplicationState.ERROR)
