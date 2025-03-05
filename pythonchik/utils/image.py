"""Модуль обработки и управления изображениями.

Предоставляет инструменты для выполнения различных операций над изображениями:
- Изменение размера изображений
- Сжатие и оптимизация
- Конвертация форматов
- Пакетная обработка множественных файлов

Модуль использует библиотеку Pillow (PIL) для работы с изображениями и
обеспечивает обработку ошибок через централизованную систему.

Классы:
- ImageProcessor: Основной класс для обработки изображений

Примеры:
    Изменение размера одного изображения:

    >>> from pythonchik.utils.image import ImageProcessor
    >>> ImageProcessor.resize_image(
    ...     "input/photo.jpg",
    ...     "output/",
    ...     progress_callback=lambda progress, msg: print(f"{progress:.0%}: {msg}")
    ... )

    Пакетная обработка нескольких изображений:

    >>> files = ["input/img1.jpg", "input/img2.png", "input/img3.jpeg"]
    >>> ImageProcessor.compress_multiple_images(files, "output/")
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, UnidentifiedImageError

from pythonchik import config
from pythonchik.errors.error_handlers import ErrorHandler, ErrorSeverity, ImageProcessingError
from pythonchik.utils.metrics import count_calls, track_timing


class ImageProcessor:
    """Класс для обработки и манипуляции изображениями.

    Предоставляет набор статических методов для выполнения различных
    операций с изображениями, таких как изменение размера, оптимизация,
    конвертация форматов и пакетная обработка. Поддерживает отслеживание
    прогресса и централизованную обработку ошибок.

    Attributes:
        Класс не имеет атрибутов состояния, все методы статические.

    Note:
        - Поддерживает форматы: JPEG, PNG, GIF, BMP, TIFF и другие (через Pillow)
        - Использует оптимизацию и настраиваемое качество из конфигурации
        - Предоставляет коллбэки для отслеживания прогресса выполнения
        - Интегрируется с системой обработки ошибок приложения
    """

    @staticmethod
    @track_timing(name="resize_image")
    @count_calls()
    def resize_image(
        image_path: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], Any]] = None,
        error_handler: Optional[ErrorHandler] = None,
    ) -> None:
        """Изменяет размер изображения и сохраняет в формате PNG.

        Загружает изображение из указанного пути, изменяет его размер в соответствии
        с коэффициентом IMAGE_RESIZE_RATIO из конфигурации, оптимизирует и сохраняет
        в указанную директорию в формате PNG с настраиваемым качеством.

        Args:
            image_path: Путь к исходному изображению, которое нужно обработать.
            output_dir: Директория для сохранения результата обработки.
            progress_callback: Опциональная функция обратного вызова для отслеживания прогресса.
                Принимает параметры (прогресс от 0.0 до 1.0, сообщение о статусе).
            error_handler: Опциональный обработчик ошибок. Если не указан,
                ошибки будут проброшены вызывающему коду.

        Raises:
            ImageProcessingError: Если произошла ошибка при обработке изображения.
            FileNotFoundError: Если исходный файл не найден.

        Examples:
            >>> # Простое изменение размера
            >>> ImageProcessor.resize_image("input/photo.jpg", "output/")
            >>>
            >>> # С отслеживанием прогресса
            >>> def on_progress(progress, message):
            ...     print(f"Прогресс: {progress:.0%}, {message}")
            ...
            >>> ImageProcessor.resize_image("input/photo.jpg", "output/",
            ...                            progress_callback=on_progress)
        """
        try:
            output_dir_path = Path(output_dir)
            if not output_dir_path.exists():
                raise ImageProcessingError(
                    f"Директория не существует: {output_dir}",
                    image_path="none",
                    operation="Проверка директории",
                )
            if not os.access(str(output_dir_path), os.W_OK):
                raise ImageProcessingError(
                    f"Нет прав на запись в директорию: {output_dir}",
                    image_path="none",
                    operation="Проверка прав доступа",
                )

            if progress_callback is not None:
                progress_callback(0, f"Обработка {Path(image_path).name}...")

            with Image.open(image_path) as im:
                width, height = im.size
                new_size = (
                    width // config.IMAGE_RESIZE_RATIO,
                    height // config.IMAGE_RESIZE_RATIO,
                )
                with im.resize(new_size) as resized_image:
                    output_path = output_dir_path / f"{Path(image_path).stem}.png"
                    resized_image.save(output_path, optimize=True, quality=config.IMAGE_QUALITY)

                    if progress_callback is not None:
                        progress_callback(100, f"Обработано {Path(image_path).name}")

        except FileNotFoundError:
            error = ImageProcessingError(
                f"Файл не найден: {image_path}", image_path=image_path, operation="Чтение файла"
            )
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error
        except PermissionError as e:
            error = ImageProcessingError(str(e), image_path=image_path, operation="Доступ к файлу")
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error
        except (UnidentifiedImageError, OSError) as e:
            error = ImageProcessingError(
                f"Ошибка при обработке изображения {image_path}: {str(e)}",
                image_path=image_path,
                operation="Обработка изображения",
            )
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error

    @staticmethod
    @track_timing(name="compress_multiple_images")
    @count_calls()
    def compress_multiple_images(
        files: List[str],
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], Any]] = None,
    ) -> List[Path]:
        """Выполняет пакетную обработку и сжатие нескольких изображений.

        Обрабатывает поочередно каждое изображение из списка, изменяя его размер
        и сохраняя результат в указанной директории. Операция продолжается даже при
        возникновении ошибок с отдельными файлами - они пропускаются, а обработка
        продолжается для оставшихся изображений.

        Args:
            files: Список путей к файлам изображений для обработки.
            output_dir: Директория для сохранения обработанных изображений.
            progress_callback: Опциональная функция обратного вызова для отслеживания прогресса.
                Принимает параметры (прогресс от 0.0 до 1.0, сообщение о статусе).

        Returns:
            Список путей к успешно обработанным файлам.

        Raises:
            Не выбрасывает исключений - ошибки обработки отдельных файлов
            не прерывают общий процесс.

        Examples:
            >>> # Основное использование
            >>> files = ["image1.jpg", "image2.png", "image3.jpeg"]
            >>> processed = ImageProcessor.compress_multiple_images(files, "output/")
            >>>
            >>> # С отслеживанием прогресса
            >>> def show_progress(progress, message):
            ...     print(f"Выполнено: {progress:.0f}%, {message}")
            >>>
            >>> processed = ImageProcessor.compress_multiple_images(
            ...     files, "output/", progress_callback=show_progress
            ... )
        """
        processed_files = []
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True)

        total_files = len(files)
        for i, file_path in enumerate(files, 1):
            try:
                if progress_callback is not None:
                    progress = (i / total_files) * 100
                    progress_callback(progress, f"Обработка файла {i}/{total_files}")

                output_path = output_dir_path / f"{Path(file_path).stem}.png"
                # Используем resize_image внутри try-except для обработки любых ошибок
                try:
                    ImageProcessor.resize_image(file_path, str(output_dir_path), progress_callback)
                    processed_files.append(output_path)
                except (FileNotFoundError, ImageProcessingError, PermissionError, OSError) as exc:
                    # Логируем ошибку через callback, если он доступен
                    if progress_callback is not None:
                        progress_callback(-1, f"Ошибка обработки {file_path}: {str(exc)}")
                    # Продолжаем обработку других файлов
                    continue

            except Exception as e:
                # Обрабатываем любые непредвиденные ошибки для устойчивости
                if progress_callback is not None:
                    progress_callback(-1, f"Неожиданная ошибка при обработке {file_path}: {str(e)}")
                continue

        return processed_files

    @staticmethod
    @track_timing(name="convert_format")
    @count_calls()
    def convert_format(input_path: str, output_path: str) -> None:
        """Конвертирует изображение в формат PNG без изменения размера.

        Выполняет конвертацию изображения из любого поддерживаемого формата в формат PNG,
        сохраняя оригинальные размеры и максимальное качество. Перед сохранением проверяет
        существование выходной директории и наличие прав на запись.

        Args:
            input_path: Путь к исходному изображению любого поддерживаемого формата.
            output_path: Полный путь (включая имя файла) для сохранения результата в PNG.

        Raises:
            FileNotFoundError: Если входной файл не существует.
            PermissionError: При отсутствии прав доступа к файлу или директории.
            OSError: При ошибках чтения/записи или конвертации изображения.

        Examples:
            >>> # Конвертация JPEG в PNG
            >>> ImageProcessor.convert_format("photo.jpg", "output/photo.png")
            >>>
            >>> # Конвертация BMP в PNG
            >>> from pathlib import Path
            >>> in_file = "images/logo.bmp"
            >>> out_file = str(Path("converted") / Path(in_file).with_suffix(".png").name)
            >>> ImageProcessor.convert_format(in_file, out_file)
        """
        try:
            # Проверка существования директории и прав на запись
            output_dir = Path(output_path).parent
            if not output_dir.exists():
                raise PermissionError(f"Директория не существует: {output_dir}")
            if not os.access(str(output_dir), os.W_OK):
                raise PermissionError(f"Нет прав на запись в директорию: {output_dir}")

            with Image.open(input_path) as img:
                img.save(output_path, format="PNG")
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл не найден: {input_path}")
        except PermissionError as e:
            raise PermissionError(str(e))
        except (UnidentifiedImageError, OSError) as e:
            raise OSError(f"Ошибка при конвертации изображения: {str(e)}")

    @staticmethod
    @track_timing(name="convert_multiple_images")
    @count_calls()
    def convert_multiple_images(files: List[str], output_dir: str) -> None:
        """Выполняет пакетную конвертацию изображений в формат PNG.

        Последовательно конвертирует все изображения из предоставленного списка
        в формат PNG и сохраняет их в указанную директорию. В отличие от
        метода compress_multiple_images, при возникновении ошибки обработка
        прерывается и выбрасывается исключение.

        Args:
            files: Список путей к файлам изображений для конвертации.
            output_dir: Директория для сохранения конвертированных файлов.

        Raises:
            OSError: При любой ошибке в процессе конвертации (включая FileNotFoundError
                и PermissionError). Содержит информацию о проблемном файле.

        Examples:
            >>> # Конвертация набора изображений
            >>> files = ["photo1.jpg", "photo2.jpeg", "logo.gif"]
            >>> ImageProcessor.convert_multiple_images(files, "png_files")
            >>>
            >>> # Работа с шаблонами путей
            >>> import glob
            >>> jpg_files = glob.glob("photos/*.jpg")
            >>> ImageProcessor.convert_multiple_images(jpg_files, "converted")
        """
        for file_path in files:
            try:
                ImageProcessor.convert_format(
                    file_path, str(Path(output_dir) / f"{Path(file_path).stem}.png")
                )
            except (FileNotFoundError, PermissionError, OSError) as e:
                raise OSError(f"Не удалось обработать изображение {file_path}: {str(e)}")
