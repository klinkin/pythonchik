import csv
import json
import zipfile
from pathlib import Path
from typing import Any


def process_multiple_files(files: list[str], processor_func: Any, *args: Any) -> list[Any]:
    """Обработка нескольких файлов с помощью указанной функции.

    Функция последовательно обрабатывает список файлов, применяя к каждому
    заданную функцию обработки с дополнительными аргументами.

    Аргументы:
        files: Список путей к файлам для обработки
        processor_func: Функция для обработки каждого файла
        *args: Дополнительные аргументы для функции обработки

    Возвращает:
        List[Any]: Список результатов обработки файлов

    Пример использования:
        >>> files = ['data1.json', 'data2.json']
        >>> results = process_multiple_files(files, count_unique_offers)
        >>> print(results)
        [(10, 5), (8, 4)]
    """
    results = []
    for file_path in files:
        data = load_json_file(file_path)
        result = processor_func(data, *args)
        if isinstance(result, list | tuple):
            results.extend(result if isinstance(result, list) else [result])
    return results


def save_to_csv(data: list[Any], header: list[str], output_path: str) -> None:
    """Сохранить данные в CSV файл.

    Функция записывает переданные данные в CSV файл с указанными заголовками.
    Каждый элемент данных записывается в отдельную строку.

    Аргументы:
        data: Список данных для сохранения в CSV
        header: Список заголовков столбцов
        output_path: Путь для сохранения CSV файла

    Возвращает:
        None

    Пример использования:
        >>> data = ['Адрес 1', 'Адрес 2']
        >>> header = ['Адрес']
        >>> save_to_csv(data, header, 'addresses.csv')

    Исключения:
        PermissionError: Если нет прав на запись в файл
        OSError: Если произошла ошибка при записи в файл
    """
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows([[item] for item in data])
    except PermissionError as e:
        raise PermissionError(f"Отказано в доступе при записи в файл {output_path}") from e
    except OSError as e:
        raise OSError(f"Ошибка при записи в CSV файл {output_path}: {str(e)}") from e


def load_json_file(file_path: str) -> dict[str, Any]:
    """Загрузка и парсинг JSON файла.

    Функция загружает JSON файл по указанному пути и преобразует его в словарь Python.
    Поддерживает обработку файлов в кодировке UTF-8.

    Аргументы:
        file_path (str): Полный путь к JSON файлу для загрузки

    Возвращает:
        Dict[str, Any]: Словарь, содержащий распарсенные JSON данные

    Исключения:
        FileNotFoundError: Если файл не существует по указанному пути
        json.JSONDecodeError: Если содержимое файла не является корректным JSON
        UnicodeDecodeError: Если файл содержит символы в неподдерживаемой кодировке

    Пример использования:
        >>> data = load_json_file('data.json')
        >>> print(data['catalogs'][0]['target_shops'])
        ['Магазин 1', 'Магазин 2']
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"JSON файл не найден: {file_path}") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Некорректный формат JSON в файле {file_path}: {str(e)}", e.doc, e.pos)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"Некорректная кодировка файла {file_path}: {str(e)}", *e.args[1:])


def create_archive(files: list[str], archive_path: str) -> None:
    """Создание ZIP-архива с указанными файлами.

    Функция создает ZIP-архив и добавляет в него все указанные файлы,
    используя сжатие DEFLATED для уменьшения размера архива.

    Аргументы:
        files: Список путей к файлам для включения в архив
        archive_path: Путь, по которому будет сохранен ZIP-архив

    Возвращает:
        None

    Пример использования:
        >>> files = ['image1.png', 'image2.png']
        >>> create_archive(files, 'images.zip')

    Исключения:
        FileNotFoundError: Если какой-либо из входных файлов не существует
        PermissionError: Если возникают проблемы с правами доступа
        OSError: Если возникают другие ошибки ввода-вывода
    """
    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if Path(file_path).exists():
                    # Use arcname with unique path to avoid name conflicts
                    arcname = f"compressed_images/{Path(file_path).name}"
                    zipf.write(file_path, arcname=arcname)
                else:
                    raise FileNotFoundError(f"Файл не найден: {file_path}")
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))
    except PermissionError as e:
        raise PermissionError(f"Отказано в доступе при создании архива: {str(e)}")
    except OSError as e:
        if not isinstance(e, FileNotFoundError | PermissionError):
            raise OSError(f"Не удалось создать архив: {str(e)}")
