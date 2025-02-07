"""Настройки конфигурации приложения."""

from pathlib import Path

# Настройки обработки изображений
IMAGE_QUALITY = 50
IMAGE_RESIZE_RATIO = 2

# Названия выходных директорий
COMPRESSED_IMAGES_DIR = "Картинки Сжатые"
FORMAT_CONVERTED_IMAGES_DIR = "Картинки формат"

# Расширения файлов
JSON_FILE_TYPES = [("JSON файлы", "*.json")]
IMAGE_FILE_TYPES = [("Файлы изображений", "*.png;*.jpg;*.webp;*.tif")]

# Суффиксы выходных файлов
ADDRESSES_SUFFIX = "_addresses"
BARCODE_SUFFIX = "_barcode"
NO_COORDINATES_SUFFIX = "_no_coordinates"
TEST_JSON_SUFFIX = "_test"

# Настройки архива
COMPRESSED_IMAGES_ARCHIVE = "Картинки Сжатые.zip"

# Настройки графика
PRICE_DIFF_PLOT_FILENAME = "Разница цен"
PRICE_PLOT_SIZE = (10, 8)
PRICE_PLOT_BINS = 30

# Настройки расположения кнопок
BUTTON_PADX = 60
BUTTON_PADY = 25
