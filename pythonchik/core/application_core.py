"""Основная функциональность приложения Pythonchik.

Описание:
    Этот модуль обрабатывает основную логику приложения, управление состоянием
    и обработку событий, отдельно от компонентов пользовательского интерфейса.

Note:
    - Управление состоянием приложения
    - Система обработки событий
    - Многопоточное выполнение задач
    - Обработка ошибок
"""

import logging
import queue
import threading
from enum import Enum
from typing import Any, Callable, Optional

from pythonchik.utils.error_handler import ErrorContext, ErrorSeverity
from pythonchik.utils.event_system import Event, EventBus, EventType


class ApplicationState(Enum):
    """Перечисление возможных состояний приложения.

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

    Это ядро приложения. Оно управляет очередью задач, фоновым потоком и общим
    состоянием приложения. Также отвечает за публикацию событий об ошибках,
    прогрессе выполнения и смене состояния, используя `EventBus`.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализирует ядро приложения.

        Args:
            event_bus (EventBus): Экземпляр шины событий для публикации уведомлений
                о состоянии, ошибках и т.п.

        Note:
            Начальное состояние приложения устанавливается в `ApplicationState.IDLE`.
        """
        self.logger = logging.getLogger("pythonchik.core")
        self.event_bus = event_bus

        self._processing_queue = queue.Queue()
        self._error_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None

        self._is_running = False
        self._state_lock = threading.Lock()
        self._state = ApplicationState.IDLE

        self.logger.info("ApplicationCore инициализирован.")

    def start(self) -> None:
        """Запускает фоновый поток для обработки очереди задач.

        Если поток уже запущен, повторный вызов игнорируется. При первом вызове
        устанавливает флаг `_is_running` в True, создаёт новый поток и начинает
        бесконечно обрабатывать задачи из очереди `_processing_queue`.
        """
        if not self._is_running:
            self.logger.info("Запуск фонового потока...")
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
            self.logger.info("Фоновый поток успешно запущен.")

    def stop(self) -> None:
        """Останавливает фоновый поток.

        Устанавливает `_is_running` в False и, если поток ещё активен,
        дожидается его завершения (join). По окончании выводит лог-сообщение
        о том, что ядро остановлено.
        """
        self.logger.info("Попытка остановки фонового потока...")
        self._is_running = False
        self._processing_queue.put(None)  # Разблокируем очередь, если она пустая
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
            self.logger.info("Фоновый поток остановлен.")
        else:
            self.logger.warning("Фоновый поток уже был остановлен.")

    def handle_error(self, error: Exception, error_context: ErrorContext) -> None:
        """Обрабатывает ошибку, возникшую во время выполнения задачи.

        Кладёт сам объект исключения `error` в `_error_queue` и публикует событие
        `ERROR_OCCURRED` через `event_bus` с подробной информацией из `error_context`.

        Args:
            error (Exception): Исключение, которое возникло.
            error_context (ErrorContext): Дополнительная информация об ошибке.

        Note:
            В дальнейшем ошибки из `_error_queue` могут быть обработаны другими
            компонентами, используя метод `process_background_tasks`.
        """
        self.logger.error(f"Ошибка в обработке задачи: {error}", exc_info=True)
        self._error_queue.put(error)
        self.event_bus.publish(
            Event(EventType.ERROR_OCCURRED, {"error": str(error), "context": error_context})
        )

    def _process_tasks(self, task: Optional[Callable[[], Any]] = None) -> None:
        """Основной метод обработки задач в рабочем потоке.

        Если `task` не равен None, метод синхронно выполняет переданную задачу
        (без входа в цикл ожидания). В противном случае — непрерывно обрабатывает
        задачи из `_processing_queue`, пока `_is_running = True`.

        Args:
            task (Callable[[], Any], optional): Конкретная задача для
                разового выполнения. Если не указана, запускается бесконечная
                обработка очереди.

        Raises:
            Exception: Если во время выполнения задачи произошла ошибка,
                она обрабатывается методом `handle_error`.
        """
        self.logger.info("Фоновый поток начал обработку задач.")

        if task:
            self.logger.info("Запущена синхронная обработка задачи.")
            with self._state_lock:
                self._update_state(ApplicationState.PROCESSING)
            try:
                result = task()
                self.logger.info("Синхронная задача выполнена успешно.")
                self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
            except Exception as exc:
                self.logger.exception("Ошибка при выполнении задачи.")
                self.handle_error(
                    exc,
                    ErrorContext(
                        operation="Обработка задачи",
                        details={"error": str(exc)},
                        severity=ErrorSeverity.ERROR,
                    ),
                )
            finally:
                with self._state_lock:
                    if self._processing_queue.empty():
                        self._update_state(ApplicationState.IDLE)
            return

        # Process queue in a loop
        while self._is_running:
            try:
                task = None
                try:
                    self.logger.debug("Фоновый поток проверяет очередь...")
                    task = self._processing_queue.get(timeout=0.5)
                    if task is None:
                        self.logger.info("Получен сигнал завершения потока.")
                        break  # Выход из цикла

                    self.logger.info("Получена новая задача из очереди.")

                except queue.Empty:
                    # Нет задач в очереди в данный момент
                    self.logger.debug("Очередь пуста, ожидаем задачи...")
                    continue

                self.logger.debug("⏳ Беру лок в _process_tasks для обновления состояния")
                with self._state_lock:
                    self.logger.debug("✅ Лок взят в _process_tasks, обновляю состояние")
                    self._update_state(ApplicationState.PROCESSING)

                try:
                    result = task()
                    self.logger.info("Задача успешно выполнена.")
                    self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))
                except Exception as exc:
                    self.logger.exception("Ошибка в задаче.")
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
                    self.logger.debug("⏳ Беру лок в _process_tasks перед обновлением состояния")
                    with self._state_lock:
                        self.logger.debug(
                            "✅ Лок взят в _process_tasks, обновляю состояние после выполнения задачи"
                        )
                        if self._processing_queue.empty() and self._state != ApplicationState.ERROR:
                            self._update_state(ApplicationState.IDLE)

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

    def _update_state(self, new_state: ApplicationState) -> None:
        """Атомарно обновляет текущее состояние приложения и публикует событие.

        Args:
            new_state (ApplicationState): Новое состояние приложения.

        Note:
            Блокировка `_state_lock` используется для безопасного обновления `_state`.
            После смены состояния публикуется событие `STATE_CHANGED` с новым
            состоянием, чтобы внешние компоненты могли отреагировать.
        """
        self.logger.debug(f"⏳ Беру лок в _update_state (новое состояние: {new_state})")
        with self._state_lock:
            self.logger.debug(f"✅ Лок взят в _update_state, обновляю состояние на {new_state}")
            self.logger.info(f"Смена состояния: {self._state} → {new_state}")
            self._state = new_state

        self.logger.debug(f"📢 Публикую событие STATE_CHANGED после выхода из лока ({new_state})")
        self.event_bus.publish(Event(EventType.STATE_CHANGED, {"state": new_state}))

    @property
    def state(self) -> ApplicationState:
        """Returns текущее состояние приложения.

        Returns:
            ApplicationState: Значение из перечисления, отражающее состояние.
        """
        with self._state_lock:
            return self._state

    def add_task(self, task: Callable[[], Any]) -> None:
        """Добавляет задачу в очередь для фоновой обработки.

        Оборачивает задачу в метод `_wrap_task()` для базовой обработки
        исключений, после чего кладёт её в `_processing_queue`. Если текущее
        состояние было `IDLE`, переключается в `PROCESSING`.

        Args:
            task (Callable[[], Any]): Функция, которая будет выполнена
                в фоновом потоке.

        Note:
            Задача будет автоматически выполнена в порядке поступления
            в очередь. Результат её выполнения (или ошибка) будут
            опубликованы через события `TASK_COMPLETED` или `ERROR_OCCURRED`.
        """
        self.logger.info("Добавлена новая задача в очередь.")
        wrapped_task = self._wrap_task(task)
        self._processing_queue.put(wrapped_task)
        with self._state_lock:
            if self._state == ApplicationState.IDLE:
                self._update_state(ApplicationState.PROCESSING)

    def _wrap_task(self, task: Callable[[], Any]) -> Callable[[], Any]:
        """Оборачивает задачу для базовой обработки исключений.

        Если в процессе выполнения задачи произойдёт ошибка, метод отправляет
        событие `ERROR_OCCURRED`.

        Args:
            task (Callable[[], Any]): Исходная функция-задача.

        Returns:
            Callable[[], Any]: Обёрнутая задача с обработкой исключений.
        """

        def wrapped_task():
            try:
                return task()
            except Exception as e:
                self.logger.exception("Ошибка в задаче.")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
                raise

        return wrapped_task

    def _wrap_task_with_progress(self, task: Callable[[], Any], description: str = "") -> Callable[[], Any]:
        """Оборачивает задачу для отслеживания прогресса выполнения.

        Сначала публикует событие `PROGRESS_UPDATED` с прогрессом 0% и
        сообщением о начале операции, затем выполняет `task()`. По завершении
        отправляет событие `PROGRESS_UPDATED` с 100% прогресса и событие
        `TASK_COMPLETED`. При ошибке публикует событие с отрицательным
        прогрессом (указывает на сбой) и `ERROR_OCCURRED`.

        Args:
            task (Callable[[], Any]): Исходная задача для выполнения.
            description (str, optional): Краткое описание операции
                для удобства отображения. По умолчанию "".

        Returns:
            Callable[[], Any]: Задача, уже обёрнутая для отслеживания
            прогресса в ходе выполнения.
        """

        def wrapped_task():
            try:
                self.logger.info(f"Начало выполнения задачи: {description}")

                # Начальный прогресс
                self.event_bus.publish(
                    Event(EventType.PROGRESS_UPDATED, {"progress": 0, "message": f"Начало {description}..."})
                )

                result = task()

                # Завершение прогресса
                self.event_bus.publish(
                    Event(
                        EventType.PROGRESS_UPDATED, {"progress": 100, "message": f"{description} завершено"}
                    )
                )

                # Успешное завершение задачи
                self.event_bus.publish(Event(EventType.TASK_COMPLETED, {"result": result}))

                self.logger.info(f"Задача завершена успешно: {description}")
                return result

            except Exception as e:
                self.logger.exception(f"Ошибка в задаче: {description}")

                # При ошибке сообщаем, что прогресс = -1 (или любой условный признак сбоя)
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
        """Синхронно обрабатывает задачу с уведомлениями о прогрессе.

        Обернёт задачу `task` в `_wrap_task_with_progress` и выполнит
        её синхронно вызовом `_process_tasks(wrapped_task)`. По завершении
        (если не было ошибки) вызовет колбэк `on_complete`.

        Args:
            task (Callable[[], Any]): Функция, выполняющая основную логику.
            description (str, optional): Описание операции для прогресс-бара.
            on_complete (Callable[[Any], None], optional): Колбэк, который
                будет вызван при успешном завершении задачи, и которому
                передаётся результат.

        Raises:
            Exception: Любая ошибка внутри `task` будет обработана и
                опубликована как событие, затем снова проброшена.

        Note:
            Этот метод НЕ кладёт задачу в очередь, а вызывает `_process_tasks`
            напрямую, т.е. блокирует текущий поток до завершения задачи.
            Будьте осторожны, если вызываете его из UI-треда.
        """
        self.logger.info(f"Поступила задача на обработку: {description}")

        def callback_wrapper():
            try:
                result = task()
                if on_complete:
                    on_complete(result)
                self.logger.info(f"Задача '{description}' успешно выполнена.")
                return result
            except Exception as e:
                self.logger.exception(f"Ошибка во время выполнения задачи: {description}")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(e)}))
                raise

        wrapped_task = self._wrap_task_with_progress(callback_wrapper, description)
        self._process_tasks(wrapped_task)

    def process_background_tasks(self) -> None:
        """Обрабатывает фоновые задачи и ошибки в главном потоке.

        Этот метод следует вызывать периодически из UI-треда (например, каждые
        100 мс через `root.after(...)`), чтобы:
          1. Выгружать ошибки из `_error_queue` и публиковать событие
             `ERROR_OCCURRED` для каждой найденной ошибки.
          2. Проверять, пуста ли очередь `_processing_queue`, и обновлять
             состояние (IDLE/PROCESSING) при необходимости.

        Raises:
            Exception: Любые сбои, возникшие при чтении очередей, обрабатываются
                и публикуются в виде события `ERROR_OCCURRED`.
        """
        self.logger.debug("Запущена обработка фоновых задач.")

        try:
            # Обработка ошибок, накопившихся в _error_queue
            while not self._error_queue.empty():
                error = self._error_queue.get_nowait()
                self.logger.warning(f"Обнаружена ошибка в фоне: {error}")
                self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(error)}))
                self._error_queue.task_done()

            # Проверка, пуста ли очередь задач
            # self.logger.debug("⏳ Беру лок в process_background_tasks")
            # with self._state_lock:
            #     self.logger.debug("✅ Лок взят в process_background_tasks, проверяю состояние очереди")

            queue_empty = self._processing_queue.empty()

            if not queue_empty and self.state != ApplicationState.PROCESSING:
                self.logger.info("Фоновые задачи активны. Переключение в состояние PROCESSING.")
                self._update_state(ApplicationState.PROCESSING)
            elif queue_empty and self.state == ApplicationState.PROCESSING:
                self.logger.info("Очередь пуста. Переключение в состояние IDLE.")
                self._update_state(ApplicationState.IDLE)

        except Exception as e:
            # Если что-то пошло не так при чтении очередей
            self.logger.exception("Ошибка при обработке фоновых задач.")

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
