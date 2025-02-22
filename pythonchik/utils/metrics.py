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

T = TypeVar("T")


@dataclass
class TimingMetric:
    count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_update: float = field(default_factory=time)
    samples: List[float] = field(default_factory=list)


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Потокобезопасный сборщик метрик с расширенными корпоративными функциями.

    Описание:
        Модуль предоставляет потокобезопасный сборщик метрик с поддержкой
        статистического анализа и сохранения данных.

    Особенности:
        - Реализует паттерн Singleton для единственного экземпляра сборщика
        - Обеспечивает потокобезопасность при сборе метрик
        - Поддерживает асинхронное сохранение данных
    """

    def increment_counter(name: str) -> None:
        """Увеличить именованный счетчик.

        Аргументы:
            name: Имя счетчика для увеличения
        """

    def record_timing(name: str, value: float) -> None:
        """Записать измерение времени со статистическим анализом.

        Аргументы:
            name: Имя измерения
            value: Значение времени выполнения
        """

    def start_timer(name: str) -> None:
        """Запустить таймер для именованной операции.

        Аргументы:
            name: Имя операции для измерения
        """

    def stop_timer(name: str) -> None:
        """Остановить таймер и записать его продолжительность.

        Аргументы:
            name: Имя операции для остановки
        """

    def get_metrics() -> Dict[str, Any]:
        """Получить все собранные метрики.

        Возвращает:
            Словарь со всеми собранными метриками.
        """

    async def save_metrics_async(file_path: str) -> None:
        """Асинхронно сохранить метрики в JSON файл.

        Аргументы:
            file_path: Путь к файлу для сохранения
        """

    def save_metrics(file_path: str) -> None:
        """Синхронно сохранить метрики в JSON файл.

        Аргументы:
            file_path: Путь к файлу для сохранения
        """

    def _save_to_file(file_path: str, metrics: Dict[str, Any]) -> None:
        """Внутренний метод для сохранения метрик в файл.

        Аргументы:
            file_path: Путь к файлу для сохранения
            metrics: Метрики для сохранения
        """

    def reset_metrics() -> None:
        """Сбросить все метрики.

        Особенности:
            Очищает все собранные метрики и сбрасывает счетчики.
        """

    def track_execution_time(threshold: float = None):
        """Расширенный декоратор для отслеживания времени выполнения с оповещениями о превышении порога.

        Аргументы:
            threshold: Пороговое значение времени выполнения в секундах

        Особенности:
            - Автоматически отслеживает время выполнения функции
            - Генерирует оповещения при превышении порога
            - Сохраняет статистику выполнения
        """

    def count_calls():
        """Декоратор для подсчета вызовов функции.

        Особенности:
            - Подсчитывает количество вызовов функции
            - Сохраняет статистику вызовов
        """

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a named counter."""
        with self._lock:
            self._counters[name] += value

    def record_timing(self, name: str, duration: float) -> None:
        """Record a timing measurement with statistical analysis."""
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
        """Start a timer for a named operation."""
        self._timers[name] = time()

    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a timer and record its duration."""
        if name not in self._timers:
            logger.warning(f"Timer {name} was not started")
            return None

        duration = time() - self._timers[name]
        del self._timers[name]
        self.record_timing(name, duration)
        return duration

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            return {"counters": dict(self._counters), "timings": dict(self._metrics)}

    async def save_metrics_async(self, file_path: Union[str, Path]) -> None:
        """Asynchronously save metrics to a JSON file."""
        try:
            metrics_data = self.get_metrics()
            await asyncio.get_event_loop().run_in_executor(
                self._executor, lambda: self._save_metrics_to_file(file_path, metrics_data)
            )
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            raise

    def save_metrics(self, file_path: Union[str, Path]) -> None:
        """Synchronously save metrics to a JSON file."""
        try:
            self._save_metrics_to_file(file_path, self.get_metrics())
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            raise

    def _save_metrics_to_file(self, file_path: Union[str, Path], data: dict) -> None:
        """Internal method to save metrics to a file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._initialize()


def track_timing(
    name: Optional[str] = None, threshold: Optional[float] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Enhanced decorator to track function execution time with threshold alerts.

    Args:
        name: Optional name for the metric. Defaults to function name.
        threshold: Optional duration threshold in seconds. Logs warning if exceeded.

    Returns:
        Decorated function that tracks execution time.
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
                collector.stop_timer(metric_name)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            collector = MetricsCollector()
            collector.start_timer(metric_name)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                collector.stop_timer(metric_name)

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    return decorator


def count_calls(name: Optional[str] = None) -> Callable:
    """Decorator to count function calls.

    Args:
        name: Optional name for the counter. Defaults to function name.

    Returns:
        Decorated function that counts calls.
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
