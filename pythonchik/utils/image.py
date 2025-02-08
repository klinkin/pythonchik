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


class ImageProcessor:
    """Класс для обработки изображений.

    Предоставляет методы для различных операций с изображениями,
    таких как изменение размера, оптимизация и сохранение.
    """

    @staticmethod
    def resize_image(
        image_path: str,
        output_dir: str,
        progress_callback: Callable[[float, str], Any] | None = None,
    ) -> None:
        """Изменение размера изображения.

        Функция изменяет размер изображения в соответствии с заданным коэффициентом
        и сохраняет результат в указанную директорию в формате PNG.

        Аргументы:
            image_path: Путь к исходному изображению
            output_dir: Директория для сохранения обработанного изображения
            progress_callback: Функция обратного вызова для отображения прогресса

        Возвращает:
            None

        Исключения:
            FileNotFoundError: Если входной файл не существует
            PermissionError: При отсутствии прав доступа
            OSError: При ошибке обработки изображения

        Пример использования:
            >>> ImageProcessor.resize_image('input.jpg', 'output_dir')
        """
        try:
            # Проверка существования директории и прав на запись
            output_dir_path = Path(output_dir)
            if not output_dir_path.exists():
                raise PermissionError(f"Директория не существует: {output_dir}")
            if not os.access(str(output_dir_path), os.W_OK):
                raise PermissionError(f"Нет прав на запись в директорию: {output_dir}")

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
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        except PermissionError as e:
            raise PermissionError(str(e))
        except (UnidentifiedImageError, OSError) as e:
            raise OSError(f"Ошибка при обработке изображения {image_path}: {str(e)}")

    @staticmethod
    def compress_multiple_images(
        files: list[str],
        output_dir: str,
        progress_callback: Callable[[float, str], Any] | None = None,
    ) -> list[Path]:
        """Пакетная обработка нескольких изображений.

        Функция последовательно обрабатывает список изображений, изменяя их размер
        и сохраняя результаты в указанную директорию.

        Аргументы:
            files: Список путей к файлам изображений
            output_dir: Директория для сохранения обработанных изображений
            progress_callback: Функция обратного вызова для отображения прогресса

        Возвращает:
            List[Path]: Список путей к обработанным файлам

        Пример использования:
            >>> files = ['image1.jpg', 'image2.jpg']
            >>> processed = ImageProcessor.compress_multiple_images(files, 'output_dir')
            >>> print(processed)
            [PosixPath('output_dir/image1.png'), PosixPath('output_dir/image2.png')]
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
        """Конвертация изображения в формат PNG.

        Функция конвертирует изображение в формат PNG без изменения его размера
        и сохраняет результат по указанному пути.

        Аргументы:
            input_path: Путь к исходному изображению
            output_path: Путь для сохранения конвертированного изображения

        Возвращает:
            None

        Исключения:
            FileNotFoundError: Если входной файл не существует
            PermissionError: При отсутствии прав доступа
            OSError: При ошибке конвертации изображения

        Пример использования:
            >>> ImageProcessor.convert_format('input.jpg', 'output.png')
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
        """Конвертация нескольких изображений в формат PNG.

        Функция последовательно конвертирует список изображений в формат PNG
        и сохраняет результаты в указанную директорию.

        Аргументы:
            files: Список путей к файлам для конвертации
            output_dir: Директория для сохранения конвертированных файлов

        Возвращает:
            None

        Исключения:
            OSError: При ошибке конвертации любого из изображений

        Пример использования:
            >>> files = ['image1.jpg', 'image2.jpg']
            >>> ImageProcessor.convert_multiple_images(files, 'output_dir')
        """
        for file_path in files:
            try:
                ImageProcessor.convert_format(
                    file_path, str(Path(output_dir) / f"{Path(file_path).stem}.png")
                )
            except (FileNotFoundError, PermissionError, OSError) as e:
                raise OSError(f"Не удалось обработать изображение {file_path}: {str(e)}")
