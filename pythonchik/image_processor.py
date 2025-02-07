"""Модуль обработки изображений.

Предоставляет классы и функции для работы с изображениями,
включая изменение размера, оптимизацию и сохранение.
"""

from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from pythonchik import config


class ImageProcessor:
    """Класс для обработки изображений.

    Предоставляет методы для различных операций с изображениями,
    таких как изменение размера, оптимизация и сохранение.
    """

    @staticmethod
    def resize_image(
        image_path: str, output_dir: str, progress_callback: Optional[Callable] = None
    ) -> None:
        """Уменьшает размер изображения в два раза и сохраняет его в указанную директорию.

        Аргументы:
            image_path (str): Путь к исходному изображению
            output_dir (str): Директория для сохранения обработанного изображения
            progress_callback: Функция обратного вызова для отображения прогресса

        Исключения:
            FileNotFoundError: Если исходный файл не найден
            PermissionError: Если нет прав на запись в output_dir
            PIL.UnidentifiedImageError: Если формат изображения не поддерживается
            OSError: При других ошибках ввода/вывода
        """
        try:
            if progress_callback:
                progress_callback(0, f"Обработка {Path(image_path).name}...")

            with Image.open(image_path) as im:
                width, height = im.size
                new_size = (
                    width // config.IMAGE_RESIZE_RATIO,
                    height // config.IMAGE_RESIZE_RATIO,
                )
                resized_image = im.resize(new_size)
                output_path = Path(output_dir) / f"{Path(image_path).stem}.png"
                resized_image.save(
                    output_path, optimize=True, quality=config.IMAGE_QUALITY
                )

                if progress_callback:
                    progress_callback(100, f"Обработано {Path(image_path).name}")

        except FileNotFoundError:
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        except PermissionError:
            raise PermissionError(f"Нет прав на запись в директорию: {output_dir}")
        except Exception as e:
            raise OSError(f"Ошибка при обработке изображения {image_path}: {str(e)}")

    @staticmethod
    def convert_format(image_path: str, output_path: str) -> None:
        """Конвертирует изображение в формат PNG.

        Аргументы:
            image_path (str): Путь к исходному изображению
            output_path (str): Путь для сохранения конвертированного изображения

        Исключения:
            FileNotFoundError: Если исходный файл не найден
            PermissionError: Если нет прав на запись в output_path
            PIL.UnidentifiedImageError: Если формат изображения не поддерживается
            OSError: При других ошибках ввода/вывода
        """
        try:
            with Image.open(image_path) as im:
                im.save(output_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл не найден: {image_path}")
        except PermissionError:
            raise PermissionError(f"Нет прав на запись: {output_path}")
        except Exception as e:
            raise OSError(f"Ошибка при конвертации изображения {image_path}: {str(e)}")
