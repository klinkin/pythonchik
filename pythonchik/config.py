"""Настройки конфигурации приложения.

Этот модуль содержит константы, пути и функции, используемые для настройки работы приложения.
Он централизует настройки для обработки изображений, путей к файлам, форматов данных и
других параметров, используемых различными компонентами.

Категории настроек:
- Настройки обработки изображений: качество, коэффициент изменения размера
- Пути к директориям вывода: output, compressed_images, converted_images
- Типы файлов: расширения для JSON и изображений
- Суффиксы для создаваемых файлов: addresses, barcodes и т.д.
- Параметры графиков: размер, количество столбцов
- Пути к файлам конфигурации: settings.json, metrics.json

Функции:
- get_unique_filename: Генерирует уникальное имя файла с временной меткой
- get_archive_path: Возвращает путь для архива сжатых изображений
- get_plot_filename: Возвращает имя файла для графиков

Примеры:
    >>> from pythonchik.config import OUTPUT_DIR, get_unique_filename
    >>> output_path = get_unique_filename("report", extension=".txt")
    >>> print(f"Файл будет сохранен в: {output_path}")
"""

from datetime import datetime
from pathlib import Path

# Настройки обработки изображений
# ------------------------------
# Качество сжатия изображений (0-100)
IMAGE_QUALITY = 50
# Коэффициент уменьшения изображения при изменении размера
IMAGE_RESIZE_RATIO = 2

# Настройки директорий
# -------------------
# Основная директория для вывода результатов
OUTPUT_DIR = Path("оutput")
OUTPUT_DIR.mkdir(exist_ok=True)

# Поддиректории для различных типов вывода
COMPRESSED_IMAGES_DIR = OUTPUT_DIR / "compressed_images"
FORMAT_CONVERTED_IMAGES_DIR = OUTPUT_DIR / "converted_images"

# Пути к файлам конфигурации
# ------------------------
# Директория для хранения конфигурационных файлов
CONFIG_DIR = Path.home() / ".pythonchik"
CONFIG_DIR.mkdir(exist_ok=True)

# Пути к файлам настроек и метрик
SETTINGS_FILE = CONFIG_DIR / "settings.json"
METRICS_FILE = CONFIG_DIR / "metrics.json"

# Типы файлов для диалогов выбора
# ------------------------------
JSON_FILE_TYPES = (("JSON файлы", "*.json"),)
IMAGE_FILE_TYPES = (("Файлы изображений", ("*.png", "*.jpg", "*.webp", "*.tif")),)

# Суффиксы для созданных файлов
# ----------------------------
ADDRESSES_SUFFIX = "_addresses"
BARCODES_SUFFIX = "_barcodes"
NO_COORDINATES_SUFFIX = "_no_coordinates"
TEST_JSON_SUFFIX = "_test"


def get_unique_filename(base_name: str, suffix: str = "", extension: str = "") -> Path:
    """Генерирует уникальное имя файла с временной меткой.

    Создает уникальное имя файла, используя базовое имя, дополнительный суффикс,
    текущую временную метку и указанное расширение. Файл будет создан в директории,
    указанной в OUTPUT_DIR.

    Args:
        base_name: Базовое имя файла
        suffix: Суффикс перед расширением
        extension: Расширение файла (с точкой)

    Returns:
        Path: Уникальный путь к файлу в директории output

    Examples:
        >>> path = get_unique_filename("report", suffix="_final", extension=".txt")
        >>> # Создаст путь типа "output/report_final_20250307_120145.txt"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{base_name}{suffix}_{timestamp}{extension}"


# Настройки архива
def get_archive_path() -> Path:
    """Возвращает уникальный путь для архива сжатых изображений.

    Returns:
        Path: Путь к ZIP-архиву с временной меткой в имени
    """
    return get_unique_filename("compressed_images", extension=".zip")


# Настройки графика
def get_plot_filename() -> str:
    """Возвращает уникальное имя файла для графика разницы цен.

    Returns:
        str: Строковое представление пути к файлу PNG для графика
    """
    return str(get_unique_filename("price_difference", extension=".png"))


# Параметры для графиков
PRICE_PLOT_SIZE = (10, 8)  # Размер графика (ширина, высота) в дюймах
PRICE_PLOT_BINS = 30  # Количество столбцов в гистограмме
