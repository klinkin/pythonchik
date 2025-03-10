"""Модуль для сбора, анализа и сохранения метрик производительности.

Предоставляет инструменты для отслеживания метрик производительности приложения,
включая счетчики вызовов функций, измерение времени выполнения операций и
статистический анализ собранных данных. Модуль обеспечивает потокобезопасный
сбор метрик, их сохранение в файлы JSON и удобные декораторы для интеграции
с существующим кодом.

Классы:
    TimingMetric: Структура данных для хранения метрик времени выполнения.
    MetricsCollector: Основной класс для сбора и анализа метрик.

Функции:
    track_timing: Декоратор для измерения времени выполнения функций.
    count_calls: Декоратор для подсчета количества вызовов функций.

Примеры:
    Базовое использование декораторов:

    >>> from pythonchik.utils.metrics import track_timing, count_calls
    >>>
    >>> @track_timing()
    >>> def expensive_operation():
    >>>     # Выполнение затратной операции
    >>>     pass
    >>>
    >>> @count_calls()
    >>> def tracked_function():
    >>>     # Отслеживание количества вызовов
    >>>     pass
    >>>
    >>> # Прямое использование коллектора метрик
    >>> from pythonchik.utils.metrics import MetricsCollector
    >>>
    >>> collector = MetricsCollector()
    >>> collector.start_timer("operation")
    >>> # Выполнение операции
    >>> collector.stop_timer("operation")
    >>>
    >>> # Сохранение метрик в файл, указанный в config.py
    >>> collector.save_metrics()
"""

import asyncio
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from threading import Lock
from time import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from pythonchik.config import METRICS_FILE

T = TypeVar("T")


@dataclass
class TimingMetric:
    """Структура данных для хранения метрик времени выполнения.

    Хранит статистические данные о продолжительности выполнения операций,
    включая общее количество измерений, среднее, минимальное и максимальное
    время, а также историю последних измерений для дополнительного анализа.

    Attributes:
        count: Количество проведенных измерений.
        total_time: Общее накопленное время выполнения.
        avg_time: Среднее время выполнения.
        min_time: Минимальное зарегистрированное время выполнения.
        max_time: Максимальное зарегистрированное время выполнения.
        last_update: Временная метка последнего обновления (Unix timestamp).
        samples: Список последних значений времени выполнения (ограничен 1000 элементами).
    """

    count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_update: float = field(default_factory=time)
    samples: List[float] = field(default_factory=list)


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Потокобезопасный сборщик метрик с расширенными функциями анализа.

    Обеспечивает сбор, агрегацию и сохранение различных метрик производительности,
    таких как счетчики вызовов и время выполнения операций. Реализует паттерн
    Singleton для обеспечения единственного экземпляра сборщика на протяжении
    всего времени работы приложения.

    Attributes:
        _instance: Статический атрибут для реализации паттерна Singleton.
        _lock: Блокировка для обеспечения потокобезопасности.
        _counters: Словарь счетчиков вызовов функций и операций.
        _metrics: Словарь метрик времени выполнения.
        _timers: Словарь активных таймеров.
        _executor: Пул потоков для асинхронного сохранения метрик.

    Examples:
        >>> # Получение экземпляра коллектора
        >>> collector = MetricsCollector()
        >>>
        >>> # Измерение времени выполнения операции
        >>> collector.start_timer("expensive_operation")
        >>> # Выполнение операции
        >>> collector.stop_timer("expensive_operation")
        >>>
        >>> # Инкрементация счетчиков
        >>> collector.increment_counter("api_calls")
        >>>
        >>> # Получение всех метрик
        >>> metrics = collector.get_metrics()
        >>>
        >>> # Сохранение метрик в файл, указанный в config.py
        >>> collector.save_metrics()
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Реализация паттерна Singleton для класса MetricsCollector."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsCollector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Инициализирует объект сборщика метрик, если он еще не инициализирован."""
        if not hasattr(self, "_initialized") or not self._initialized:
            self._lock = Lock()
            self._initialize()
            self._executor = ThreadPoolExecutor(max_workers=1)
            self._initialized = True

    def _initialize(self):
        """Инициализирует внутренние структуры данных для сбора метрик."""
        self._counters = defaultdict(int)
        self._metrics = defaultdict(TimingMetric)
        self._timers = {}

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Увеличивает именованный счетчик на указанное значение.

        Args:
            name: Имя счетчика для увеличения.
            value: Значение, на которое нужно увеличить счетчик. По умолчанию 1.
        """
        with self._lock:
            self._counters[name] += value

    def record_timing(self, name: str, duration: float) -> None:
        """Записывает измерение времени выполнения со статистическим анализом.

        Добавляет новое измерение времени в статистику и обновляет агрегированные
        показатели, такие как минимальное, максимальное и среднее значения.

        Args:
            name: Имя метрики времени выполнения.
            duration: Значение продолжительности выполнения в секундах.

        Note:
            Метод хранит историю последних 1000 измерений для возможного
            дополнительного статистического анализа.
        """
        with self._lock:
            metric = self._metrics[name]
            metric.count += 1
            metric.total_time += duration
            metric.avg_time = metric.total_time / metric.count
            metric.min_time = min(metric.min_time, duration)
            metric.max_time = max(metric.max_time, duration)
            metric.last_update = time()
            metric.samples.append(duration)

            # Keep only last 1000 samples for memory efficiency
            if len(metric.samples) > 1000:
                metric.samples.pop(0)

    def start_timer(self, name: str) -> None:
        """Запускает таймер для именованной операции.

        Args:
            name: Имя операции для измерения времени выполнения.

        Note:
            Для остановки таймера и записи результата необходимо использовать
            метод stop_timer() с тем же именем операции.
        """
        self._timers[name] = time()

    def stop_timer(self, name: str) -> Optional[float]:
        """Останавливает таймер и записывает его продолжительность.

        Args:
            name: Имя операции, для которой необходимо остановить таймер.

        Returns:
            Продолжительность выполнения операции в секундах или None,
            если таймер с указанным именем не был запущен.

        Note:
            Автоматически вызывает метод record_timing() для сохранения
            и анализа результатов измерения.
        """
        if name not in self._timers:
            logger.warning(f"Timer {name} was not started")
            return None

        duration = time() - self._timers[name]
        del self._timers[name]
        self.record_timing(name, duration)
        return duration

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает все собранные метрики.

        Returns:
            Словарь со всеми собранными метриками, включая счетчики
            и статистику времени выполнения.
        """
        with self._lock:
            return {"counters": dict(self._counters), "timings": dict(self._metrics)}

    async def save_metrics_async(self) -> None:
        """Асинхронно сохраняет метрики в JSON файл.

        Выполняет сохранение метрик в файл без блокировки основного потока
        выполнения, используя пул потоков. Метрики сохраняются в файл,
        указанный в METRICS_FILE из config.py.

        Raises:
            Exception: При возникновении ошибки во время сохранения.
        """
        try:
            metrics_data = self.get_metrics()
            await asyncio.get_event_loop().run_in_executor(
                self._executor, lambda: self._save_metrics_to_file(METRICS_FILE, metrics_data)
            )
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def save_metrics(self) -> None:
        """Синхронно сохраняет метрики в JSON файл.

        Метрики сохраняются в файл, указанный в METRICS_FILE из config.py.

        Raises:
            Exception: При возникновении ошибки во время сохранения.
        """
        try:
            self._save_metrics_to_file(METRICS_FILE, self.get_metrics())
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _save_metrics_to_file(self, file_path: Union[str, Path], data: dict) -> None:
        """Внутренний метод для сохранения метрик в файл.

        Args:
            file_path: Путь к файлу для сохранения.
            data: Словарь с метриками для сохранения.
        """
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def reset(self) -> None:
        """Сбрасывает все собранные метрики.

        Очищает все счетчики, метрики времени выполнения и активные таймеры.
        """
        with self._lock:
            self._initialize()


def track_timing(
    name: Optional[str] = None, threshold: Optional[float] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Декоратор для отслеживания времени выполнения функций.

    Автоматически измеряет и записывает время выполнения декорированной функции,
    поддерживает как синхронные, так и асинхронные функции, а также позволяет
    настроить предупреждения при превышении порогового времени выполнения.

    Args:
        name: Опциональное пользовательское имя для метрики. По умолчанию
            используется имя функции.
        threshold: Опциональное пороговое значение продолжительности в секундах.
            Если указано, при превышении этого значения будет залогировано предупреждение.

    Returns:
        Декорированная функция, которая отслеживает время выполнения.

    Examples:
        >>> # Базовое использование
        >>> @track_timing()
        >>> def process_data(data):
        >>>     # Обработка данных
        >>>     pass
        >>>
        >>> # Использование с пользовательским именем и порогом
        >>> @track_timing(name="api_request", threshold=1.0)
        >>> async def fetch_data_from_api():
        >>>     # Асинхронный запрос к API
        >>>     pass
    """

    def decorator(func: Callable) -> Callable:
        metric_name = name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = MetricsCollector()
            collector.start_timer(metric_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = collector.stop_timer(metric_name)
                if threshold is not None and duration is not None and duration > threshold:
                    logger.warning(
                        f"Function {func.__name__} exceeded threshold: {duration:.4f}s > {threshold:.4f}s"
                    )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = MetricsCollector()
            collector.start_timer(metric_name)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = collector.stop_timer(metric_name)
                if threshold is not None and duration is not None and duration > threshold:
                    logger.warning(
                        f"Function {func.__name__} exceeded threshold: {duration:.4f}s > {threshold:.4f}s"
                    )

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    return decorator


def count_calls(name: Optional[str] = None) -> Callable:
    """Декоратор для подсчета вызовов функций.

    Автоматически увеличивает счетчик при каждом вызове декорированной функции,
    что позволяет отслеживать частоту использования функций в приложении.

    Args:
        name: Опциональное пользовательское имя для счетчика. По умолчанию
            используется имя функции с суффиксом "_calls".

    Returns:
        Декорированная функция, которая учитывает количество вызовов.

    Examples:
        >>> # Базовое использование
        >>> @count_calls()
        >>> def frequently_called_function():
        >>>     # Тело функции
        >>>     pass
        >>>
        >>> # С пользовательским именем счетчика
        >>> @count_calls(name="user_login_attempts")
        >>> def authenticate_user(username, password):
        >>>     # Проверка аутентификации
        >>>     pass
    """

    def decorator(func: Callable) -> Callable:
        counter_name = name or f"{func.__name__}_calls"

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = MetricsCollector()
            collector.increment_counter(counter_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator
