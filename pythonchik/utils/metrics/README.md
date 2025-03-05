# Система сбора и визуализации метрик

Модуль `metrics.py` предоставляет функциональность для сбора и анализа метрик производительности приложения. Он интегрирован в ключевые компоненты проекта и позволяет отслеживать время выполнения и частоту вызова функций.

## Основные компоненты

### MetricsCollector

Основной класс для сбора и агрегирования метрик. Реализует паттерн Singleton, который обеспечивает единую точку доступа к метрикам из любой части приложения.

```python
from pythonchik.utils.metrics import MetricsCollector

# Получение экземпляра
metrics = MetricsCollector()

# Отслеживание времени выполнения
metrics.start_timer("operation_name")
# ... выполнение операции ...
duration = metrics.stop_timer("operation_name")

# Подсчет событий
metrics.increment_counter("api_calls")

# Получение всех метрик
all_metrics = metrics.get_metrics()

# Сохранение метрик в файл
metrics.save_metrics("metrics.json")
```

### Декораторы

Модуль также предоставляет удобные декораторы для автоматического сбора метрик из функций:

#### track_timing

Отслеживает время выполнения функции и записывает статистику:

```python
from pythonchik.utils.metrics import track_timing

@track_timing(name="my_function", threshold=1.0)
def process_data(data):
    # ... обработка данных ...
    return result
```

#### count_calls

Считает количество вызовов функции:

```python
from pythonchik.utils.metrics import count_calls

@count_calls(name="authenticate_user_calls")
def authenticate_user(username, password):
    # ... проверка аутентификации ...
    return is_authenticated
```

## Интеграция в проект

Система метрик интегрирована в следующие компоненты:

1. **ApplicationCore**: Отслеживает время выполнения задач, количество добавленных и выполненных задач, ошибки.

2. **ImageProcessor**: Измеряет производительность функций обработки изображений:
   - resize_image
   - compress_multiple_images
   - convert_format
   - convert_multiple_images

3. **UI**: Визуализирует собранные метрики через специальный фрейм `MetricsFrame`.

## Просмотр метрик

Для просмотра метрик в пользовательском интерфейсе:

1. Запустите приложение
2. Нажмите кнопку "Метрики" в боковой панели навигации
3. Для обновления данных нажмите кнопку "Обновить метрики"

## Автоматическое сохранение метрик

Метрики автоматически сохраняются в JSON-файл при корректном завершении работы приложения. Путь к файлу: `~/.pythonchik/metrics.json`

## Расширение системы метрик

Для добавления отслеживания новых операций:

1. Импортируйте необходимые компоненты:
   ```python
   from pythonchik.utils.metrics import MetricsCollector, track_timing, count_calls
   ```

2. Используйте декораторы для автоматического отслеживания:
   ```python
   @track_timing(name="custom_operation")
   @count_calls()
   def your_function():
       # ...
   ```

3. Или используйте прямой доступ к MetricsCollector:
   ```python
   metrics = MetricsCollector()
   metrics.start_timer("custom_operation")
   # ... выполнение операции ...
   metrics.stop_timer("custom_operation")
   metrics.increment_counter("custom_counter")
   ```
