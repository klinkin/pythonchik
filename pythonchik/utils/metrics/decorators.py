"""Декораторы для автоматического сбора метрик производительности.

Предоставляет декораторы для автоматического отслеживания вызовов функций
и измерения времени их выполнения. Может использоваться как с синхронными,
так и с асинхронными функциями.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from pythonchik.utils.metrics.collector import MetricsCollector

T = TypeVar("T")
logger = logging.getLogger(__name__)


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
