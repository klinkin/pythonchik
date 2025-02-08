"""Настройки конфигурации приложения."""

from datetime import datetime
from pathlib import Path

# Настройки обработки изображений
IMAGE_QUALITY = 50
IMAGE_RESIZE_RATIO = 2

# Настройки выходной директории
OUTPUT_DIR = Path("оutput")
OUTPUT_DIR.mkdir(exist_ok=True)

# Названия выходных директорий
COMPRESSED_IMAGES_DIR = OUTPUT_DIR / "compressed_images"
FORMAT_CONVERTED_IMAGES_DIR = OUTPUT_DIR / "converted_images"

# Расширения файлов
JSON_FILE_TYPES = (("JSON файлы", "*.json"),)
IMAGE_FILE_TYPES = (("Файлы изображений", ("*.png", "*.jpg", "*.webp", "*.tif")),)

# Суффиксы выходных файлов
ADDRESSES_SUFFIX = "_addresses"
BARCODE_SUFFIX = "_barcode"
NO_COORDINATES_SUFFIX = "_no_coordinates"
TEST_JSON_SUFFIX = "_test"


def get_unique_filename(base_name: str, suffix: str = "", extension: str = "") -> Path:
    """Генерирует уникальное имя файла с временной меткой.

    Args:
        base_name: Базовое имя файла
        suffix: Суффикс перед расширением
        extension: Расширение файла (с точкой)

    Returns:
        Path: Уникальный путь к файлу в директории output
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{base_name}{suffix}_{timestamp}{extension}"


# Настройки архива
def get_archive_path() -> Path:
    return get_unique_filename("compressed_images", extension=".zip")


# Настройки графика
def get_plot_filename() -> str:
    return str(get_unique_filename("price_difference", extension=".png"))


PRICE_PLOT_SIZE = (10, 8)
PRICE_PLOT_BINS = 30
