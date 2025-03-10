# Pythonchik

Pythonchik — мощная многопоточная система обработки и анализа данных, обеспечивающая надежное и эффективное выполнение задач.

## Обзор

Этот проект представляет собой модульную систему, реализующую высоконадежную обработку данных с богатыми возможностями централизованного управления ошибками, событийной системой и структурированным логированием. Система спроектирована для работы с разнообразными источниками данных, обеспечивая их эффективную обработку, визуализацию и хранение.

## Технологии и архитектура

Проект использует современную архитектуру, основанную на следующих принципах и технологиях:

- **Модульная структура**: Четкое разделение ответственности между компонентами
- **Событийно-ориентированная архитектура**: Слабое связывание компонентов через шину событий
- **Многопоточность**: Параллельная обработка задач для повышения производительности
- **Контейнеризация**: Поддержка Docker для упрощения развертывания
- **Типизация**: Строгая типизация с использованием аннотаций типов Python
- **Тестирование**: Обширный набор автоматизированных тестов (unit, integration)

Технологический стек:
- Python 3.10+
- CustomTkinter (UI компоненты)
- Matplotlib (визуализация данных)
- Pillow (обработка изображений)
- Pydantic (валидация данных)
- Poetry (управление зависимостями)
- Pytest (тестирование)

## Установка и запуск

### Установка через Poetry (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/pythonchik.git
cd pythonchik

# Установка зависимостей с помощью Poetry
poetry install

# Запуск приложения
poetry run python -m pythonchik.main
```

### Установка с помощью pip

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/pythonchik.git
cd pythonchik

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python -m pythonchik.main
```

### Использование Docker

```bash
# Сборка образа
docker build -t pythonchik .

# Запуск контейнера
docker run -v $(pwd)/data:/app/data pythonchik
```

## Основные компоненты

### Ядро системы (Core)

Ядро системы отвечает за управление жизненным циклом приложения, обработку задач в многопоточном режиме и корректное отслеживание состояния.

- **ApplicationCore**: Главный компонент, управляющий очередями задач и рабочими потоками
- **StateManager**: Компонент для контроля и мониторинга состояния системы
- **TaskProcessor**: Обработчик задач с поддержкой приоритетов и зависимостей

### Система обработки ошибок (Errors)

Централизованная система обработки ошибок предоставляет единый подход к управлению и восстановлению после сбоев.

- **ErrorHandler**: Обрабатывает различные типы ошибок с контекстной информацией
- **Классы ошибок**: Иерархия специализированных классов для разных типов ошибок
- **Механизмы восстановления**: Стратегии для восстановления после ошибок

### Событийная система (Events)

Система событий обеспечивает слабое связывание компонентов через механизм публикации и подписки.

- **EventBus**: Центральная шина для передачи событий между компонентами
- **Подписчики и Издатели**: Интерфейсы для работы с событиями
- **Приоритеты обработки**: Механизм для определения порядка обработки событий

### Система логирования (Logging)

Расширяемая система логирования с поддержкой структурированных форматов и ротацией логов.

- **ContextLogger**: Расширенный логгер с поддержкой контекстных полей
- **JSONFormatter**: Форматирование логов в JSON для удобного анализа
- **Ротация логов**: Управление размером и количеством лог-файлов

### Сервисы (Services)

Набор специализированных сервисов для выполнения конкретных задач.

- **DataProcessingService**: Обработка и анализ данных
- **ImageProcessingService**: Работа с изображениями
- **FileService**: Операции с файлами и архивами

### Пользовательский интерфейс (UI)

Современный и интуитивно понятный интерфейс на базе CustomTkinter.

- **Адаптивный дизайн**: Поддержка разных размеров экрана
- **Темная и светлая темы**: Переключение режимов отображения
- **Компонентный подход**: Модульные и переиспользуемые компоненты интерфейса

### Система метрик (Metrics)

Инструменты для отслеживания производительности и диагностики.

- **MetricsCollector**: Сбор и агрегация метрик производительности
- **Декораторы измерения времени**: Автоматическое отслеживание времени выполнения функций
- **Визуализация метрик**: Отображение статистики в пользовательском интерфейсе

## Архитектура

Система построена на принципах модульности, обеспечивая низкую связанность компонентов:

```
┌───────────────────────────────────────────────────────────────┐
│                          UI Layer                             │
└───────────────────────────────────────────────────────────────┘
                               ▲
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Application Core                         │
├───────────┬───────────┬───────────┬───────────┬───────────────┤
│  Task     │  State    │  Event    │  Error    │  Logging      │
│ Processor │ Management│  System   │ Handling  │  System       │
└───────────┴───────────┴───────────┴───────────┴───────────────┘
                               ▲
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Service Layer                            │
├───────────┬───────────┬───────────┬───────────────────────────┤
│  Data     │  Image    │  File     │  Other                    │
│ Processing│ Processing│ Operations│  Services                 │
└───────────┴───────────┴───────────┴───────────────────────────┘
                               ▲
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      Utility Layer                            │
└───────────────────────────────────────────────────────────────┘
```

## Примеры использования

### Обработка JSON-данных

```python
from pythonchik.services import DataProcessingService
from pythonchik.events.eventbus import EventBus

# Создание необходимых экземпляров
bus = EventBus()
service = DataProcessingService(bus)

# Извлечение адресов из JSON-файла
addresses = service.extract_addresses("data.json")
print(f"Найдено {len(addresses)} адресов")

# Проверка координат в JSON-данных
invalid_coords = service.check_coordinates("data.json")
print(f"Найдено {len(invalid_coords)} записей с недопустимыми координатами")
```

### Обработка изображений

```python
from pythonchik.services import ImageProcessingService
from pythonchik.events.eventbus import EventBus

# Создание необходимых экземпляров
bus = EventBus()
service = ImageProcessingService(bus)

# Сжатие изображения
compressed_path = service.compress_image("image.jpg", quality=80)
print(f"Сжатое изображение сохранено в {compressed_path}")

# Извлечение штрих-кодов из изображения
barcodes = service.extract_barcodes("product.jpg")
print(f"Найдено {len(barcodes)} штрих-кодов")
```

### Использование метрик

```python
from pythonchik.utils.metrics import MetricsCollector, track_timing

# Декоратор для измерения времени выполнения
@track_timing(name="process_data", threshold=1.0)
def process_large_dataset(data):
    # Длительная обработка данных
    result = analyze(data)
    return result

# Ручное измерение времени выполнения
collector = MetricsCollector.instance
collector.start_timer("database_query")
results = query_database()
duration = collector.stop_timer("database_query")
print(f"Запрос выполнялся {duration:.2f} мс")

# Получение и сохранение метрик
metrics = collector.get_metrics()
collector.save_metrics("performance_metrics.json")
```

## Разработка и тестирование

### Запуск тестов

```bash
# Запуск всех тестов
make test

# Запуск с покрытием кода
make coverage

# Запуск линтеров
make lint
```

### Структура проекта

```
pythonchik/
├── core/                # Компоненты ядра системы
├── ui/                  # Компоненты пользовательского интерфейса
├── events/              # Система событий
├── errors/              # Обработка ошибок
├── utils/               # Утилиты
│   ├── metrics/         # Система метрик
│   └── settings/        # Управление настройками
├── services/            # Сервисы для различных операций
├── models/              # Модели данных
└── main.py              # Точка входа в приложение

tests/                   # Тесты
├── core/                # Тесты компонентов ядра
├── ui/                  # Тесты пользовательского интерфейса
└── ...

docs/                    # Документация
examples/                # Примеры использования
```

## Лицензия

[MIT](LICENSE) © Pythonchik Team

## Контрибьюторы

- Core Team
- Список всех контрибьюторов можно найти в разделе [Contributors](https://github.com/yourusername/pythonchik/contributors)
