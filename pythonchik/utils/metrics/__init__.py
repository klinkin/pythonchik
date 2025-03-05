"""Пакет метрик для мониторинга производительности приложения Pythonchik.

Этот пакет предоставляет инструменты для сбора, анализа и визуализации
метрик производительности, таких как время выполнения операций и
количество вызовов функций. Он использует паттерн Singleton для обеспечения
единой точки сбора метрик во всем приложении.

Основные возможности:
- Сбор временных метрик выполнения функций и блоков кода
- Подсчет количества вызовов операций различного типа
- Автоматическое сохранение метрик в JSON-файл
- Отображение метрик в пользовательском интерфейсе
- Встроенные декораторы для упрощения сбора метрик

Основные компоненты:
- MetricsCollector: Основной класс для сбора и агрегации метрик
- TimingMetric: Класс для представления временных метрик
- track_timing: Декоратор для измерения времени выполнения функций
- count_calls: Декоратор для подсчета количества вызовов функций
- start_timer/stop_timer: Методы для ручного замера времени выполнения блоков кода

Примеры использования:

    # Получение экземпляра коллектора метрик
    >>> from pythonchik.utils.metrics import MetricsCollector
    >>> collector = MetricsCollector.instance

    # Использование декоратора для замера времени
    >>> from pythonchik.utils.metrics import track_timing
    >>>
    >>> @track_timing
    >>> def process_image(image_path):
    ...     # Выполнение операции с измерением времени
    ...     pass
    >>>
    >>> process_image('image.jpg')  # Время автоматически фиксируется

    # Использование ручного замера времени
    >>> from pythonchik.utils.metrics import MetricsCollector
    >>>
    >>> collector = MetricsCollector.instance
    >>> collector.start_timer("database_query")
    >>> # Код, время выполнения которого нужно измерить
    >>> result = execute_database_query()
    >>> duration = collector.stop_timer("database_query")
    >>> print(f"Запрос выполнялся {duration:.2f} мс")

    # Подсчет вызовов функции
    >>> from pythonchik.utils.metrics import count_calls
    >>>
    >>> @count_calls("api_requests")
    >>> def call_external_api(data):
    ...     # Вызов внешнего API
    ...     return response

    # Получение собранных метрик
    >>> metrics = collector.get_metrics()
    >>> print(f"Общее количество запросов к API: {metrics['counters'].get('api_requests', 0)}")
    >>> print(f"Среднее время обработки изображений: {metrics['timings'].get('process_image', 0)} мс")

    # Сохранение метрик в файл
    >>> collector.save_metrics('/path/to/metrics.json')
"""

from pythonchik.utils.metrics.collector import MetricsCollector, TimingMetric
from pythonchik.utils.metrics.decorators import count_calls, track_timing

__all__ = ["MetricsCollector", "TimingMetric", "track_timing", "count_calls"]
