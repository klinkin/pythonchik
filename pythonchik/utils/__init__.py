"""Модуль утилит и вспомогательных функций приложения Pythonchik.

Этот модуль предоставляет широкий набор утилит и вспомогательных функций для:
- Обработки и преобразования JSON файлов
- Работы с изображениями (сжатие, изменение размера, конвертация форматов)
- Сохранения данных в CSV формате
- Создания ZIP-архивов
- Отслеживания производительности (метрики, измерение времени выполнения)
- Управления настройками приложения
- Пакетной обработки нескольких файлов

Подмодули:
- image: Функции для обработки и манипуляции изображениями
- settings: Управление пользовательскими настройками приложения
- metrics: Сбор и анализ метрик производительности приложения

Весь модуль интегрирован с централизованной системой обработки ошибок
приложения, что обеспечивает согласованное логирование и обработку
исключений на всех уровнях.

Основные функции:
- process_multiple_files: Пакетная обработка нескольких файлов заданной функцией
- save_to_csv: Сохранение данных в CSV файл с указанными заголовками
- load_json_file: Загрузка и парсинг JSON файла с обработкой ошибок
- create_archive: Создание ZIP-архива с указанными файлами
- validate_json_structure: Валидация JSON данных согласно ожидаемой структуре

Примеры:
    Обработка нескольких JSON файлов:

    >>> from pythonchik.utils import process_multiple_files, load_json_file
    >>>
    >>> def extract_cities(data):
    ...     return [location['city'] for location in data['locations']]
    >>>
    >>> files = ['data1.json', 'data2.json']
    >>> cities = process_multiple_files(files, load_json_file, extract_cities)
    >>> print(cities)  # ['Москва', 'Санкт-Петербург', 'Новосибирск', ...]

    Работа с изображениями:

    >>> from pythonchik.utils.image import compress_image, convert_image_format
    >>>
    >>> # Сжатие изображения
    >>> compressed_path = compress_image('photo.jpg', quality=80)
    >>> print(f"Сжатое изображение сохранено в {compressed_path}")
    >>>
    >>> # Конвертация формата
    >>> webp_path = convert_image_format('photo.jpg', 'webp')
    >>> print(f"Конвертированное изображение сохранено в {webp_path}")

    Отслеживание производительности:

    >>> from pythonchik.utils.metrics import MetricsCollector, timed
    >>>
    >>> # Замер времени выполнения функции
    >>> @timed("data_processing")
    >>> def process_data(items):
    ...     # Длительная обработка данных
    ...     return result
    >>>
    >>> # Вызов функции с отслеживанием времени
    >>> result = process_data(data)
    >>>
    >>> # Получение метрик
    >>> collector = MetricsCollector.instance
    >>> metrics = collector.get_metrics()
    >>> print(f"Время выполнения: {metrics['timings']['data_processing']} мс")
"""

import csv
import json
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from pythonchik.errors.error_handlers import ErrorContext, ErrorHandler, ErrorSeverity, FileOperationError

T = TypeVar("T")


def process_multiple_files(
    files: List[str], processor_func: Callable[[Dict[str, Any], Any], T], *args: Any
) -> List[T]:
    """Обрабатывает несколько файлов с помощью указанной функции.

    Последовательно обрабатывает список файлов, применяя к каждому заданную
    функцию обработки с дополнительными аргументами. При возникновении ошибки
    обработки одного файла, функция продолжает работу с остальными файлами.

    Args:
        files: Список путей к файлам для обработки.
        processor_func: Функция для обработки каждого файла. Должна принимать
            словарь с данными из JSON файла как первый аргумент.
        *args: Дополнительные аргументы, которые будут переданы в processor_func.

    Returns:
        Список результатов обработки файлов. Каждый элемент списка представляет
        собой результат применения processor_func к соответствующему файлу.

    Raises:
        FileNotFoundError: Если один из файлов не найден.

    Examples:
        >>> files = ['data1.json', 'data2.json']
        >>> def count_unique_offers(data):
        ...     return len(set(offer['id'] for offer in data['offers']))
        >>> results = process_multiple_files(files, count_unique_offers)
        >>> print(results)  # [10, 8]
    """
    results = []
    error_handler = ErrorHandler()

    for file_path in files:
        try:
            data = load_json_file(file_path)
            result = processor_func(data, *args)
            if isinstance(result, list | tuple):
                results.extend(result if isinstance(result, list) else [result])
        except FileNotFoundError as e:
            error_handler.handle_error(
                FileOperationError(str(e), file_path, "Обработка файла"),
                "Обработка файла",
                ErrorSeverity.ERROR,
            )
            raise
        except Exception as e:
            error = FileOperationError(str(e), file_path, "Обработка файла")
            error_handler.handle_error(error, "Обработка файла", ErrorSeverity.ERROR)
            continue
    return results


def save_to_csv(data: List[Any], header: List[str], output_path: str) -> None:
    """Сохраняет данные в CSV файл.

    Записывает переданные данные в CSV файл с указанными заголовками.
    Каждый элемент данных записывается в отдельную строку. Автоматически
    создает директорию для файла, если она не существует.

    Args:
        data: Список данных для сохранения в CSV. Каждый элемент
            будет записан в отдельную строку файла.
        header: Список заголовков столбцов CSV файла.
        output_path: Полный путь для сохранения CSV файла.
            Если директория не существует, она будет создана.

    Raises:
        PermissionError: При отсутствии прав для создания файла или директории.
        OSError: При ошибке записи данных в файл.
        FileOperationError: При возникновении других проблем с файловыми операциями.

    Examples:
        >>> data = ['Адрес 1', 'Адрес 2']
        >>> header = ['Адрес']
        >>> save_to_csv(data, header, 'addresses.csv')
    """
    error_handler = ErrorHandler()
    try:
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows([[item] for item in data])
    except PermissionError as e:
        error_handler.handle_error(
            FileOperationError("Отказано в доступе", output_path, "Сохранение CSV"),
            "Сохранение CSV",
            ErrorSeverity.ERROR,
        )
        raise PermissionError("Отказано в доступе")
    except OSError as e:
        error_handler.handle_error(
            FileOperationError("Ошибка при записи в CSV файл", output_path, "Сохранение CSV"),
            "Сохранение CSV",
            ErrorSeverity.ERROR,
        )
        raise OSError("Ошибка при записи в CSV файл")
    except Exception as e:
        error = FileOperationError(str(e), output_path, "Сохранение CSV")
        error_handler.handle_error(error, "Сохранение CSV", ErrorSeverity.ERROR)
        raise error


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Загружает и парсит JSON файл.

    Загружает JSON файл по указанному пути и преобразует его в словарь Python.
    Поддерживает обработку файлов в кодировке UTF-8 и централизованно обрабатывает
    все возможные исключения при чтении и парсинге.

    Args:
        file_path: Полный путь к JSON файлу для загрузки.

    Returns:
        Словарь, содержащий распарсенные JSON данные.

    Raises:
        FileNotFoundError: Если файл не найден или недоступен для чтения.
        JSONDecodeError: При некорректном формате JSON.
        UnicodeDecodeError: При проблемах с кодировкой файла.
        FileOperationError: При других ошибках файловых операций.

    Examples:
        >>> try:
        ...     data = load_json_file('data.json')
        ...     print(data['catalogs'][0]['name'])
        ... except FileOperationError as e:
        ...     print(f'Ошибка при загрузке файла: {e}')
        'Основной каталог'
    """
    error_handler = ErrorHandler()
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        error_handler.handle_error(
            FileOperationError("JSON файл не найден", file_path, "Загрузка JSON"),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise FileNotFoundError("JSON файл не найден")
    except json.JSONDecodeError as e:
        error_handler.handle_error(
            FileOperationError("Некорректный формат JSON", file_path, "Загрузка JSON"),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise json.JSONDecodeError("Некорректный формат JSON", e.doc, e.pos)
    except UnicodeDecodeError as e:
        error_handler.handle_error(
            FileOperationError("Некорректная кодировка файла", file_path, "Загрузка JSON"),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, "Некорректная кодировка файла")
    except Exception as e:
        error = FileOperationError(str(e), file_path, "Загрузка JSON")
        error_handler.handle_error(error, "Загрузка JSON", ErrorSeverity.ERROR)
        raise error


def create_archive(files: List[str], archive_path: str) -> None:
    """Создает ZIP-архив с указанными файлами.

    Создает ZIP-архив и добавляет в него все указанные файлы, используя сжатие
    DEFLATED для уменьшения размера. Автоматически создает директорию для архива,
    если она не существует, и предварительно проверяет существование всех файлов.

    Args:
        files: Список путей к файлам для включения в архив.
        archive_path: Полный путь, по которому будет сохранен ZIP-архив.

    Raises:
        FileNotFoundError: Если один или несколько файлов не найдены.
        PermissionError: При отсутствии прав для создания архива.
        OSError: При ошибке сжатия или записи архива.
        FileOperationError: При других ошибках файловых операций.

    Examples:
        >>> files = ['image1.png', 'image2.png']
        >>> create_archive(files, 'output/images.zip')
    """
    error_handler = ErrorHandler()
    try:
        archive_dir = Path(archive_path).parent
        if not archive_dir.exists():
            archive_dir.mkdir(parents=True, exist_ok=True)

        # Проверим все файлы перед созданием архива
        for file_path in files:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                error_handler.handle_error(
                    FileOperationError(f"Файл не найден: {file_path}", file_path, "Создание архива"),
                    "Создание архива",
                    ErrorSeverity.ERROR,
                )
                raise FileNotFoundError(f"Файл не найден: {file_path}")

        # Создаем архив только если все файлы существуют
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                arcname = Path(file_path).name
                zipf.write(file_path, arcname=arcname)
    except FileNotFoundError:
        # Пробрасываем исключение FileNotFoundError напрямую
        raise
    except PermissionError as e:
        error_handler.handle_error(
            FileOperationError("Отказано в доступе", archive_path, "Создание архива"),
            "Создание архива",
            ErrorSeverity.ERROR,
        )
        raise PermissionError("Отказано в доступе")
    except OSError as e:
        error_handler.handle_error(
            FileOperationError("Не удалось создать архив", archive_path, "Создание архива"),
            "Создание архива",
            ErrorSeverity.ERROR,
        )
        raise OSError("Не удалось создать архив")
    except Exception as e:
        error = FileOperationError(str(e), archive_path, "Создание архива")
        error_handler.handle_error(error, "Создание архива", ErrorSeverity.ERROR)
        raise
