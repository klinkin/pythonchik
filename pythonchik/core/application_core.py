"""Ядро приложения для управления задачами и состоянием.

Этот модуль предоставляет основную функциональность ядра приложения:
- Управление жизненным циклом приложения (запуск/остановка)
- Многопоточную обработку задач через очередь
- Контроль состояния приложения
- Механизм публикации событий о результатах обработки задач

Классы:
- ApplicationCore: Основное ядро приложения
- TaskFunc: Тип для колбэков задач

Функции:
- _force_kill_thread: Утилита для форсированной остановки потока

Примеры:
    Базовое использование:

    >>> from pythonchik.core.application_core import ApplicationCore
    >>> from pythonchik.events.eventbus import EventBus
    >>>
    >>> # Создание экземпляра ядра приложения
    >>> event_bus = EventBus()
    >>> app_core = ApplicationCore(event_bus)
    >>>
    >>> # Запуск ядра
    >>> app_core.start()
    >>>
    >>> # Добавление задачи
    >>> def example_task():
    ...     return "Результат выполнения задачи"
    ...
    >>> app_core.add_task(example_task)
    >>>
    >>> # Остановка ядра
    >>> app_core.stop()
"""

import ctypes
import logging
import queue
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from pythonchik.core.application_state import ApplicationState, ApplicationStateManager
from pythonchik.errors.error_handlers import ErrorContext, ErrorSeverity
from pythonchik.events.eventbus import EventBus
from pythonchik.events.events import Event, EventType
from pythonchik.utils.metrics import MetricsCollector, count_calls, track_timing

# Определение типа для функций задач
TaskFunc = Callable[[], Any]


def _force_kill_thread(thread: threading.Thread) -> None:
    """Форсирует остановку потока путём посылки SystemExit.

    Используется в крайних случаях, когда нормальная остановка потока
    через флаги или события не работает. Опасный метод, так как может
    привести к утечкам ресурсов и повреждению данных.

    Args:
        thread: Поток, который нужно форсированно завершить.

    Raises:
        RuntimeError: Если процедура форсированного завершения завершилась некорректно.

    Note:
        Использовать только в крайних случаях, когда другие методы не работают.
        Перед вызовом данной функции следует попытаться остановить поток
        нормальными способами (через флаги, события и т.д.).
    """
    if not thread.is_alive():
        return
    thread_id = thread.ident
    if thread_id is None:
        return

    # Посылаем исключение SystemExit в поток (ОПАСНО, использовать с осторожностью).
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
    if res == 0:
        # Поток уже завершается или идентификатор некорректен
        return
    elif res > 1:
        # Если вернулось больше 1, нужно отменить
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
        raise RuntimeError("Не удалось корректно форсировать остановку потока")


class ApplicationCore:
    """Основное ядро приложения.

    Управляет фоновым потоком, очередью задач, состоянием приложения и
    публикует события через EventBus. Обеспечивает многопоточную обработку
    задач с контролем состояния и обработкой ошибок.

    Attributes:
        event_bus (EventBus): Экземпляр шины событий для публикации.
        state_manager (ApplicationStateManager): Менеджер состояния приложения.
        _task_queue (queue.Queue): Очередь задач для обработки.
        _worker_thread (threading.Thread): Рабочий поток обработки задач.
        _stop_event (threading.Event): Событие для сигнала остановки потока.
        _is_running (bool): Флаг, указывающий, запущено ли ядро.
        _max_queue_size (int): Максимальный размер очереди задач.
        _logger (logging.Logger): Логгер для отладки и информационных сообщений.
        metrics (MetricsCollector): Коллектор метрик для мониторинга производительности.

    Note:
        Для взаимодействия с другими компонентами используется EventBus,
        что обеспечивает слабую связанность и расширяемость.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Инициализирует ядро приложения.

        Создает экземпляр ядра приложения с необходимыми очередями задач,
        устанавливает начальное состояние и подготавливает рабочий поток.

        Args:
            event_bus: Шина событий для публикации результатов и ошибок.

        Examples:
            >>> event_bus = EventBus()
            >>> app_core = ApplicationCore(event_bus)
        """
        self.logger = logging.getLogger("pythonchik.core")
        self.event_bus = event_bus

        # Инициализация коллектора метрик
        self.metrics = MetricsCollector()

        # Очередь для фоновых задач, очередь для ошибок
        self._processing_queue = queue.Queue()
        self._error_queue = queue.Queue()

        # Флаг работы потока, флаг завершения
        self._is_running = False
        self._is_shutting_down = False

        # Поток-воркер
        self._worker_thread: Optional[threading.Thread] = None

        # Событие для кооперативной остановки текущих задач
        self._stop_event = threading.Event()

        self.state_manager = ApplicationStateManager(event_bus)
        self.logger.info("ApplicationCore инициализирован.")

    @count_calls()
    def start(self) -> None:
        """Запускает фоновый поток для обработки очереди задач.

        Создает и запускает рабочий поток для обработки задач из очереди.
        При вызове устанавливает флаг _is_running в True и начинает выполнение
        метода _process_tasks в отдельном потоке.

        Note:
            Если поток уже запущен, повторный вызов игнорируется с выводом
            предупреждения в лог.

        Examples:
            >>> app_core = ApplicationCore(event_bus)
            >>> app_core.start()  # Запуск обработки задач
        """
        # Начинаем измерение времени работы ядра
        self.metrics.start_timer("core_uptime")

        if self._is_running:
            self.logger.warning("Попытка повторного запуска — поток уже работает.")
            return

        self.logger.info("Запуск фонового потока...")
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self._worker_thread.start()
        self.logger.info("Фоновый поток успешно запущен.")

    @count_calls()
    def stop(self) -> None:
        """Останавливает фоновый поток обработки задач.

        Выполняет корректное завершение работы фонового потока (graceful shutdown).
        Процесс включает несколько шагов:
        1. Установка флагов завершения работы
        2. Сигнализирование о необходимости остановки через событие
        3. Очистка очереди задач
        4. Ожидание завершения потока с таймаутом
        5. Принудительное завершение потока, если он не остановился добровольно

        Note:
            Если поток не завершается в течение таймаута (2 секунды),
            производится попытка форсированной остановки, что может
            привести к утечкам ресурсов.

        Examples:
            >>> app_core = ApplicationCore(event_bus)
            >>> app_core.start()
            >>> # ... выполнение задач ...
            >>> app_core.stop()  # Корректное завершение работы
        """
        # Фиксируем общее время работы ядра
        uptime = self.metrics.stop_timer("core_uptime")
        if uptime:
            self.logger.info(f"Общее время работы ядра: {uptime:.2f} секунд")

        self.logger.info("Начало graceful shutdown...")
        self._is_shutting_down = True
        self._stop_event.set()  # Событие для прерывания задач
        self._is_running = False

        # Сохраняем метрики перед завершением работы
        try:
            metrics_path = Path.home() / ".pythonchik" / "metrics.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics.save_metrics(str(metrics_path))
            self.logger.info(f"Метрики сохранены в {metrics_path}")
        except Exception as e:
            self.logger.error(f"Не удалось сохранить метрики: {e}")

        # Очистка очереди, отправка сигнала завершения
        while not self._processing_queue.empty():
            try:
                self._processing_queue.get_nowait()
            except queue.Empty:
                break

        # Ставим в очередь специальный сигнал None, чтобы поток прервал цикл.
        self._processing_queue.put(None)

        # Ожидаем нормального завершения потока
        if self._worker_thread and self._worker_thread.is_alive():
            self.logger.info("Ожидаем завершения фонового потока...")
            self._worker_thread.join(timeout=2.0)
            if self._worker_thread.is_alive():
                # Если всё ещё жив, пытаемся форсировать завершение (НЕБЕЗОПАСНО)
                self.logger.warning("Поток не завершился вовремя, форсируем остановку!")
                _force_kill_thread(self._worker_thread)

        self.logger.info("Фоновый поток остановлен или уже был остановлен.")

    @count_calls()
    def add_task(self, task: Callable[[], Any], description: str = "", track_progress: bool = True) -> None:
        """Добавляет задачу в очередь для выполнения в фоновом потоке.

        Задача помещается в очередь для последующего выполнения рабочим потоком.
        Если текущее состояние приложения IDLE, оно изменяется на PROCESSING.

        Args:
            task: Функция без аргументов, которая будет выполнена в фоновом потоке.
                Возвращаемое значение функции будет опубликовано как событие TASK_COMPLETED.
            description: Описание задачи для логирования и отслеживания. По умолчанию пустая строка.
            track_progress: Флаг для отслеживания прогресса выполнения.
                Если True, публикуются события о начале и завершении задачи.
                По умолчанию True.

        Raises:
            RuntimeError: Если приложение находится в процессе завершения работы.
            queue.Full: Если очередь задач переполнена.

        Examples:
            >>> def example_task():
            ...     # Выполнение какой-то работы
            ...     return "Результат работы"
            ...
            >>> app_core.add_task(example_task, "Обработка данных")
        """
        if self._is_shutting_down:
            raise RuntimeError("Нельзя добавлять задачи во время завершения работы приложения.")

        self.logger.info("Добавлена новая задача в очередь.")
        # Увеличиваем счетчик задач
        self.metrics.increment_counter("tasks_added")

        wrapped = self._wrap_task(task, description, track_progress)
        self._processing_queue.put_nowait(wrapped)

        # Если состояние было IDLE, переключаем на PROCESSING
        if self.state_manager.state == ApplicationState.IDLE:
            self.state_manager.update_state(ApplicationState.PROCESSING)

    def _process_tasks(self) -> None:
        """Фоновая обработка задач из очереди.

        Внутренний метод, выполняемый в рабочем потоке. Циклически извлекает
        задачи из очереди и выполняет их. Цикл продолжается до тех пор, пока
        не будет получен сигнал завершения (None) или установлен флаг _stop_event.

        В случае возникновения исключения в задаче, состояние приложения
        изменяется на ERROR, а исключение логируется и публикуется как событие.

        Note:
            Этот метод не должен вызываться напрямую. Он запускается
            автоматически при вызове метода start().
        """
        self.logger.info("Фоновый поток начал обработку задач.")
        while self._is_running:
            if self._stop_event.is_set():
                # Кооперативная остановка: прерываем цикл, если запросили shutdown
                self.logger.info("Воркер завершает работу по сигналу _stop_event.")
                break

            try:
                task = self._processing_queue.get(timeout=0.5)
            except queue.Empty:
                continue  # Ждём задачи

            if task is None:
                self.logger.info("Получен сигнал завершения потока (None).")
                break

            self.state_manager.update_state(ApplicationState.PROCESSING)
            try:
                # Если в процессе взятия задачи из очереди уже запросили остановку:
                if self._stop_event.is_set():
                    self.logger.info("Задача прервана во время shutdown.")
                    raise KeyboardInterrupt("Задача прервана во время shutdown")

                # Начинаем отслеживание времени выполнения задачи
                self.metrics.start_timer("task_execution")

                result = task()  # Выполняем задачу

                # Завершаем отслеживание времени и увеличиваем счетчик выполненных задач
                task_time = self.metrics.stop_timer("task_execution")
                self.metrics.increment_counter("tasks_completed")
                if task_time:
                    self.logger.debug(f"Задача выполнена за {task_time:.4f} секунд")

                self.event_bus.publish(
                    Event(EventType.TASK_COMPLETED, {"result": result, "execution_time": task_time})
                )

            except (KeyboardInterrupt, RuntimeError) as exc:
                self.logger.warning(f"Задача прервана во время shutdown: {exc}")
                # Увеличиваем счетчик прерванных задач
                self.metrics.increment_counter("tasks_interrupted")
                break
            except Exception as exc:
                self.logger.exception("Ошибка в задаче (фоновая).")
                # Увеличиваем счетчик ошибок
                self.metrics.increment_counter("task_errors")
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

            # Состояние IDLE, если очередь пуста и нет ошибки
            if self._processing_queue.empty() and self.state_manager.state != ApplicationState.ERROR:
                self.state_manager.update_state(ApplicationState.IDLE)

        self.logger.info("Фоновый поток завершил обработку задач.")

    def _wrap_task(
        self, task: Callable[[], Any], description: str = "", track_progress: bool = True
    ) -> Callable[[], Any]:
        """Оборачивает задачу, добавляя обработку ошибок и отслеживание прогресса.

        Args:
            task (Callable[[], Any]): Функция, реализующая логику задачи.
            description (str): Описание для сообщений о прогрессе.
            track_progress (bool): Флаг, указывающий на необходимость публиковать события о прогрессе.

        Returns:
            Callable[[], Any]: Функция-обёртка, проверяющая флаги остановки и публикующая события.
        """

        @track_timing(name=f"task_{description}" if description else None)
        def wrapped_task():
            # Проверяем событие остановки до старта задачи
            if self._stop_event.is_set():
                raise KeyboardInterrupt("Задача прервана до запуска (shutdown инициирован)")

            try:
                # Публикуем прогресс 0% — начало задачи
                if track_progress:
                    self.logger.info(f"Начало выполнения задачи: {description}")
                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 0, "message": f"Начало выполнения задачи {description}..."},
                        )
                    )

                result = task()

                # Публикуем прогресс 100% — успешное завершение задачи
                if track_progress:
                    message = f"Задача завершена успешно: {description}"

                    self.event_bus.publish(
                        Event(
                            EventType.PROGRESS_UPDATED,
                            {"progress": 100, "message": message},
                        )
                    )
                    self.logger.info(message)

                return result
            except Exception as e:
                # Если есть трекинг прогресса — показываем ошибку
                if track_progress:
                    self.logger.exception(f"Ошибка в задаче: {description}")
                    self.event_bus.publish(
                        Event(EventType.PROGRESS_UPDATED, {"progress": -1, "message": f"Ошибка: {str(e)}"})
                    )
                raise

        return wrapped_task

    def handle_error(self, error: Exception, error_context: ErrorContext) -> None:
        """Обрабатывает ошибку, возникшую во время выполнения фоновой задачи.

        Публикует событие ERROR_OCCURRED, добавляет ошибку в очередь ошибок и
        устанавливает состояние приложения в ApplicationState.ERROR.

        Args:
            error (Exception): Исключение, которое возникло.
            error_context (ErrorContext): Дополнительный контекст об ошибке (операция, детали и т.д.).
        """
        self.logger.error(f"Ошибка в обработке задачи: {error}", exc_info=True)
        self._error_queue.put(error)
        self.event_bus.publish(
            Event(EventType.ERROR_OCCURRED, data={"error": error, "context": error_context})
        )
        self.state_manager.update_state(ApplicationState.ERROR)

    def handle_task(
        self,
        task: Callable[[], Any],
        description: str = "",
        on_complete: Optional[Callable[[Any], None]] = None,
    ) -> Any:
        """Синхронно обрабатывает задачу в текущем потоке (без помещения в очередь).

        Args:
            task (Callable[[], Any]): Функция с основной логикой задачи.
            description (str): Описание задачи для логгирования и прогресса.
            on_complete (Optional[Callable[[Any], None]]): Колбэк, вызываемый при успешном завершении задачи.

        Returns:
            Любое значение, возвращаемое самой задачей.

        Raises:
            Exception: Любая ошибка, возникшая в процессе выполнения задачи.
        """
        self.logger.info(f"Поступила задача handle_task: {description}")
        self.state_manager.update_state(ApplicationState.PROCESSING)

        try:
            self.event_bus.publish(
                Event(
                    EventType.PROGRESS_UPDATED,
                    {"progress": 0, "message": f"Начало выполнения задачи {description}..."},
                )
            )

            result = task()
            if on_complete:
                on_complete(result)

            self.event_bus.publish(
                Event(EventType.PROGRESS_UPDATED, {"progress": 100, "message": f"{description} завершено"})
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
            if self.state_manager.state != ApplicationState.ERROR:
                self.state_manager.update_state(ApplicationState.IDLE)

    def process_background_tasks(self) -> None:
        """Вызывается из UI-треда для обработки ошибок и обновления состояния приложения.

        Считывает все ошибки из очереди ошибок и публикует их, затем обновляет состояние
        приложения (PROCESSING, IDLE и т.д.) в зависимости от ситуации в очереди задач.

        Raises:
            Exception: Любая ошибка, возникшая при обработке фоновых задач.
        """
        self.logger.debug("Запущена обработка фоновых задач в UI-треде.")
        try:
            self._process_error_queue()
            self._update_state_based_on_queue()
        except Exception as e:
            self._handle_background_task_error(e)

    def _process_error_queue(self) -> None:
        """Обрабатывает накопленные ошибки из очереди ошибок."""
        while not self._error_queue.empty():
            err = self._error_queue.get_nowait()
            self.logger.warning(f"Обнаружена ошибка в фоне: {err}")
            self.event_bus.publish(Event(EventType.ERROR_OCCURRED, {"error": str(err)}))
            self._error_queue.task_done()

    def _update_state_based_on_queue(self) -> None:
        """Обновляет состояние приложения в зависимости от наличия задач в очереди."""
        if not self._processing_queue.empty() and self.state_manager.state != ApplicationState.PROCESSING:
            self.logger.info("Фоновые задачи активны -> PROCESSING.")
            self.state_manager.update_state(ApplicationState.PROCESSING)
        elif self._processing_queue.empty() and self.state_manager.state == ApplicationState.PROCESSING:
            self.logger.info("Очередь пуста -> IDLE.")
            self.state_manager.update_state(ApplicationState.IDLE)

    def _handle_background_task_error(self, error: Exception) -> None:
        """Обрабатывает ошибку, возникшую в процессе фоновых задач.

        Args:
            error (Exception): Исключение, которое нужно обработать.
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
