import csv
import json
import zipfile
from pathlib import Path
from typing import Any

from pythonchik.utils.error_handler import ErrorContext, ErrorHandler, ErrorSeverity, FileOperationError


def process_multiple_files(files: list[str], processor_func: Any, *args: Any) -> list[Any]:
    """Обработка нескольких файлов с помощью указанной функции.

    Функция последовательно обрабатывает список файлов, применяя к каждому
    заданную функцию обработки с дополнительными аргументами. При возникновении
    ошибки обработки одного файла, функция продолжает работу с остальными файлами.

    Args:
        files (list[str]): Список путей к файлам для обработки. Каждый путь должен
            указывать на существующий и доступный для чтения файл.
        processor_func (Any): Функция для обработки каждого файла. Должна принимать
            словарь с данными из JSON файла как первый аргумент.
        *args (Any): Дополнительные Args, которые будут переданы в processor_func.

    Returns:
        list[Any]: Список результатов обработки файлов. Каждый элемент списка
            представляет собой результат применения processor_func к соответствующему файлу.

    Note:
        - Продолжает обработку при ошибках отдельных файлов
        - Автоматически обрабатывает ошибки и логирует их
        - Поддерживает как одиночные значения, так и списки в результатах

    Пример использования:
        >>> files = ['data1.json', 'data2.json']
        >>> def count_unique_offers(data):
        ...     return len(set(offer['id'] for offer in data['offers']))
        >>> results = process_multiple_files(files, count_unique_offers)
        >>> print(results)  # Количество уникальных предложений в каждом файле
        [10, 8]
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
                FileOperationError(
                    str(e),
                    context=ErrorContext(
                        operation="Обработка файла",
                        details={"file_path": file_path},
                        severity=ErrorSeverity.ERROR,
                        recovery_action="Проверьте наличие файла",
                    ),
                ),
                "Обработка файла",
                ErrorSeverity.ERROR,
            )
            raise
        except Exception as e:
            error = FileOperationError(
                str(e),
                context=ErrorContext(
                    operation="Обработка файла",
                    details={"file_path": file_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте формат и доступность файла",
                ),
            )
            error_handler.handle_error(error, "Обработка файла", ErrorSeverity.ERROR)
            continue
    return results


def save_to_csv(data: list[Any], header: list[str], output_path: str) -> None:
    """Сохранить данные в CSV файл.

    Функция записывает переданные данные в CSV файл с указанными заголовками.
    Каждый элемент данных записывается в отдельную строку. Функция автоматически
    создает директорию для файла, если она не существует.

    Args:
        data (list[Any]): Список данных для сохранения в CSV. Каждый элемент
            будет записан в отдельную строку файла.
        header (list[str]): Список заголовков столбцов CSV файла.
        output_path (str): Полный путь для сохранения CSV файла.
            Если директория не существует, она будет создана.

    Returns:
        None

    Исключения:
        FileOperationError: Возникает в следующих случаях:
            - Недостаточно прав для создания файла или директории
            - Ошибка при записи данных
            - Проблемы с кодировкой

    Note:
        - Автоматически создает директории при необходимости
        - Использует кодировку UTF-8
        - Каждый элемент данных записывается в отдельную строку

    Пример использования:
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
            FileOperationError(
                "Отказано в доступе",
                context=ErrorContext(
                    operation="Сохранение CSV",
                    details={"output_path": output_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте права доступа к файлу",
                ),
            ),
            "Сохранение CSV",
            ErrorSeverity.ERROR,
        )
        raise PermissionError("Отказано в доступе")
    except OSError as e:
        error_handler.handle_error(
            FileOperationError(
                "Ошибка при записи в CSV файл",
                context=ErrorContext(
                    operation="Сохранение CSV",
                    details={"output_path": output_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте возможность записи в файл",
                ),
            ),
            "Сохранение CSV",
            ErrorSeverity.ERROR,
        )
        raise OSError("Ошибка при записи в CSV файл")
    except Exception as e:
        error = FileOperationError(
            str(e),
            context=ErrorContext(
                operation="Сохранение CSV",
                details={"output_path": output_path},
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте права доступа и путь к файлу",
            ),
        )
        error_handler.handle_error(error, "Сохранение CSV", ErrorSeverity.ERROR)
        raise error


def load_json_file(file_path: str) -> dict[str, Any]:
    """Загрузка и парсинг JSON файла.

    Функция загружает JSON файл по указанному пути и преобразует его в словарь Python.
    Поддерживает обработку файлов в кодировке UTF-8. При возникновении ошибок
    во время чтения или парсинга файла, генерирует исключение с подробным описанием
    проблемы и рекомендациями по её устранению.

    Args:
        file_path (str): Полный путь к JSON файлу для загрузки. Путь должен быть
            доступен для чтения и указывать на корректный JSON файл.

    Returns:
        Dict[str, Any]: Словарь, содержащий распарсенные JSON данные. Структура словаря
            соответствует структуре исходного JSON файла.

    Исключения:
        FileOperationError: Возникает в следующих случаях:
            - Файл не найден или недоступен для чтения
            - Некорректный формат JSON
            - Проблемы с кодировкой файла

    Пример использования:
        >>> try:
        ...     data = load_json_file('data.json')
        ...     print(data['catalogs'][0]['target_shops'])
        ... except FileOperationError as e:
        ...     print(f'Ошибка при загрузке файла: {e}')
        ['Магазин 1', 'Магазин 2']
    """
    error_handler = ErrorHandler()
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        error_handler.handle_error(
            FileOperationError(
                "JSON файл не найден",
                context=ErrorContext(
                    operation="Загрузка JSON",
                    details={"file_path": file_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте путь к файлу",
                ),
            ),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise FileNotFoundError("JSON файл не найден")
    except json.JSONDecodeError as e:
        error_handler.handle_error(
            FileOperationError(
                "Некорректный формат JSON",
                context=ErrorContext(
                    operation="Загрузка JSON",
                    details={"file_path": file_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте формат JSON файла",
                ),
            ),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise json.JSONDecodeError("Некорректный формат JSON", e.doc, e.pos)
    except UnicodeDecodeError as e:
        error_handler.handle_error(
            FileOperationError(
                "Некорректная кодировка файла",
                context=ErrorContext(
                    operation="Загрузка JSON",
                    details={"file_path": file_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте кодировку файла",
                ),
            ),
            "Загрузка JSON",
            ErrorSeverity.ERROR,
        )
        raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, "Некорректная кодировка файла")
    except Exception as e:
        error = FileOperationError(
            str(e),
            context=ErrorContext(
                operation="Загрузка JSON",
                details={"file_path": file_path},
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте формат и кодировку файла",
            ),
        )
        error_handler.handle_error(error, "Загрузка JSON", ErrorSeverity.ERROR)
        raise error


def create_archive(files: list[str], archive_path: str) -> None:
    """Создание ZIP-архива с указанными файлами.

    Функция создает ZIP-архив и добавляет в него все указанные файлы,
    используя сжатие DEFLATED для уменьшения размера архива. Автоматически
    создает директорию для архива, если она не существует.

    Args:
        files (list[str]): Список путей к файлам для включения в архив.
            Каждый путь должен указывать на существующий файл.
        archive_path (str): Полный путь, по которому будет сохранен ZIP-архив.
            Если директория не существует, она будет создана автоматически.

    Returns:
        None

    Исключения:
        FileOperationError: Возникает в следующих случаях:
            - Один или несколько файлов не найдены
            - Недостаточно прав для создания архива
            - Ошибка при сжатии файлов

    Note:
        - Автоматически создает директории при необходимости
        - Использует DEFLATED сжатие для оптимизации размера
        - Сохраняет файлы в поддиректории 'compressed_images'

    Пример использования:
        >>> files = ['image1.png', 'image2.png']
        >>> create_archive(files, 'output/images.zip')
    """
    error_handler = ErrorHandler()
    try:
        archive_dir = Path(archive_path).parent
        if not archive_dir.exists():
            archive_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    arcname = file_path_obj.name
                    zipf.write(file_path, arcname=arcname)
                else:
                    error_handler.handle_error(
                        FileOperationError(
                            f"Файл не найден: {file_path}",
                            context=ErrorContext(
                                operation="Создание архива",
                                details={"file_path": file_path},
                                severity=ErrorSeverity.ERROR,
                                recovery_action="Проверьте наличие файла",
                            ),
                        ),
                        "Создание архива",
                        ErrorSeverity.ERROR,
                    )
                    raise FileNotFoundError(f"Файл не найден: {file_path}")
    except PermissionError as e:
        error_handler.handle_error(
            FileOperationError(
                "Отказано в доступе",
                context=ErrorContext(
                    operation="Создание архива",
                    details={"archive_path": archive_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте права доступа",
                ),
            ),
            "Создание архива",
            ErrorSeverity.ERROR,
        )
        raise PermissionError("Отказано в доступе")
    except OSError as e:
        error_handler.handle_error(
            FileOperationError(
                "Не удалось создать архив",
                context=ErrorContext(
                    operation="Создание архива",
                    details={"archive_path": archive_path},
                    severity=ErrorSeverity.ERROR,
                    recovery_action="Проверьте возможность создания архива",
                ),
            ),
            "Создание архива",
            ErrorSeverity.ERROR,
        )
        raise OSError("Не удалось создать архив")
    except Exception as e:
        error = FileOperationError(
            str(e),
            context=ErrorContext(
                operation="Создание архива",
                details={"archive_path": archive_path},
                severity=ErrorSeverity.ERROR,
                recovery_action="Проверьте права доступа и наличие файлов",
            ),
        )
        error_handler.handle_error(error, "Создание архива", ErrorSeverity.ERROR)
        raise
