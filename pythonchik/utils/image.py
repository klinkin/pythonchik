"""Модуль обработки изображений.

Предоставляет классы и функции для работы с изображениями,
включая изменение размера, оптимизацию и сохранение.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from pythonchik import config
from pythonchik.utils.error_handler import ErrorHandler, ErrorSeverity, ImageProcessingError


class ImageProcessor:
    """Класс для обработки изображений.

    Предоставляет методы для различных операций с изображениями,
    таких как изменение размера, оптимизация и сохранение.

    Методы:
        resize_image: Изменение размера изображения с сохранением в формате PNG
        compress_multiple_images: Пакетная обработка и сжатие нескольких изображений
        convert_format: Конвертация изображения в формат PNG
        convert_multiple_images: Пакетная конвертация изображений в формат PNG

    Особенности:
        - Поддерживает различные форматы изображений
        - Оптимизирует размер файлов при сохранении
        - Предоставляет возможность отслеживания прогресса обработки
        - Обеспечивает обработку ошибок и логирование
    """

    @staticmethod
    def resize_image(
        image_path: str,
        output_dir: str,
        progress_callback: Callable[[float, str], Any] | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        """Изменение размера изображения с сохранением в формате PNG.

        Функция уменьшает размер изображения в соответствии с коэффициентом
        IMAGE_RESIZE_RATIO, оптимизирует его и сохраняет в указанную директорию
        в формате PNG с заданным качеством IMAGE_QUALITY.

        Аргументы:
            image_path: Путь к исходному изображению для обработки
            output_dir: Директория для сохранения обработанного изображения
            progress_callback: Функция для отображения прогресса обработки.
                             Принимает процент выполнения (float) и сообщение (str)
            error_handler: Обработчик ошибок для логирования и обработки исключений

        Возвращает:
            None

        Исключения:
            ImageProcessingError: При проблемах с доступом к директории или файлу
            FileNotFoundError: Если входной файл не существует
            PermissionError: При отсутствии необходимых прав доступа
            OSError: При ошибках в процессе обработки изображения

        Пример использования:
            >>> from pythonchik.utils.image import ImageProcessor
            >>> ImageProcessor.resize_image('photo.jpg', 'output_dir')
        """
        try:
            output_dir_path = Path(output_dir)
            if not output_dir_path.exists():
                raise ImageProcessingError(
                    f"Директория не существует: {output_dir}",
                    recovery_action="Создайте директорию или выберите существующую",
                )
            if not os.access(str(output_dir_path), os.W_OK):
                raise ImageProcessingError(
                    f"Нет прав на запись в директорию: {output_dir}",
                    recovery_action="Проверьте права доступа к директории",
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
                f"Файл не найден: {image_path}", recovery_action="Проверьте правильность пути к файлу"
            )
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error
        except PermissionError as e:
            error = ImageProcessingError(
                str(e), recovery_action="Проверьте права доступа к файлу и директории"
            )
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error
        except (UnidentifiedImageError, OSError) as e:
            error = ImageProcessingError(
                f"Ошибка при обработке изображения {image_path}: {str(e)}",
                recovery_action="Убедитесь, что файл является корректным изображением",
            )
            if error_handler:
                error_handler.handle_error(error, "Изменение размера изображения", ErrorSeverity.ERROR)
            raise error

    @staticmethod
    def compress_multiple_images(
        files: list[str],
        output_dir: str,
        progress_callback: Callable[[float, str], Any] | None = None,
    ) -> list[Path]:
        """Пакетная обработка и сжатие нескольких изображений.

        Функция последовательно обрабатывает список изображений, уменьшая их размер
        и оптимизируя каждое изображение. Все результаты сохраняются в формате PNG
        в указанную директорию. При возникновении ошибки с одним файлом, обработка
        продолжается для остальных файлов.

        Аргументы:
            files: Список путей к исходным файлам изображений
            output_dir: Директория для сохранения обработанных изображений
            progress_callback: Функция для отображения прогресса обработки.
                             Принимает процент выполнения (float) и сообщение (str)

        Возвращает:
            List[Path]: Список путей к успешно обработанным файлам

        Особенности:
            - Автоматически создает директорию вывода, если она не существует
            - Пропускает файлы, которые не удалось обработать
            - Отображает прогресс обработки через callback-функцию

        Пример использования:
            >>> from pathlib import Path
            >>> files = ['photo1.jpg', 'photo2.png']
            >>> processed = ImageProcessor.compress_multiple_images(files, 'output')
            >>> print(processed)
            [PosixPath('output/photo1.png'), PosixPath('output/photo2.png')]
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
                ImageProcessor.resize_image(file_path, str(output_dir_path), progress_callback)
                processed_files.append(output_path)

            except (FileNotFoundError, PermissionError, OSError) as e:
                if progress_callback is not None:
                    progress_callback(-1, f"Ошибка обработки {file_path}: {str(e)}")
                continue

        return processed_files

    @staticmethod
    def convert_format(input_path: str, output_path: str) -> None:
        """Конвертация изображения в формат PNG без изменения размера.

        Функция выполняет конвертацию изображения в формат PNG, сохраняя исходные
        размеры и качество. Перед сохранением проверяется существование директории
        и наличие прав на запись.

        Аргументы:
            input_path: Путь к исходному изображению любого поддерживаемого формата
            output_path: Полный путь для сохранения конвертированного PNG-файла

        Возвращает:
            None

        Исключения:
            FileNotFoundError: Если входной файл не существует
            PermissionError: При отсутствии прав доступа к файлу или директории
            OSError: При ошибках чтения/записи или конвертации изображения
            UnidentifiedImageError: Если формат входного файла не распознан

        Пример использования:
            >>> from pythonchik.utils.image import ImageProcessor
            >>> # Конвертация JPEG в PNG
            >>> ImageProcessor.convert_format('photo.jpg', 'photo.png')
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
    def convert_multiple_images(files: list[str], output_dir: str) -> None:
        """Пакетная конвертация изображений в формат PNG.

        Функция последовательно конвертирует все изображения из предоставленного
        списка в формат PNG, сохраняя их в указанную директорию. При возникновении
        ошибки с любым файлом, обработка прерывается.

        Аргументы:
            files: Список путей к файлам изображений для конвертации
            output_dir: Директория для сохранения конвертированных файлов

        Возвращает:
            None

        Исключения:
            OSError: При любой ошибке в процессе конвертации (включая FileNotFoundError
                    и PermissionError). Содержит информацию о проблемном файле

        Особенности:
            - Сохраняет оригинальные размеры изображений
            - Использует имя исходного файла с расширением .png
            - Прерывает обработку при первой ошибке

        Пример использования:
            >>> from pythonchik.utils.image import ImageProcessor
            >>> files = ['photo1.jpg', 'photo2.jpeg']
            >>> ImageProcessor.convert_multiple_images(files, 'png_files')
        """
        for file_path in files:
            try:
                ImageProcessor.convert_format(
                    file_path, str(Path(output_dir) / f"{Path(file_path).stem}.png")
                )
            except (FileNotFoundError, PermissionError, OSError) as e:
                raise OSError(f"Не удалось обработать изображение {file_path}: {str(e)}")
