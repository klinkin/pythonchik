from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def test_image() -> Image.Image:
    # Создание тестового изображения
    img = Image.new("RGB", (100, 100), color="red")
    return img


@pytest.fixture
def temp_image_file(tmp_path: Path, test_image: Image.Image) -> Path:
    # Создание временного файла изображения для тестирования
    image_path = tmp_path / "test_image.png"
    test_image.save(image_path)
    return image_path


def test_image_processing(test_image: Image.Image, temp_image_file: Path) -> None:
    # Тестирование загрузки изображения
    loaded_image = Image.open(temp_image_file)
    assert loaded_image.size == test_image.size
    assert loaded_image.mode == test_image.mode

    # Тестирование изменения размера
    resized_image = loaded_image.resize((50, 50))
    assert resized_image.size == (50, 50)

    # Тестирование конвертации формата
    jpeg_path = temp_image_file.parent / "test_image.jpg"
    loaded_image.convert("RGB").save(jpeg_path, "JPEG")
    assert jpeg_path.exists()

    # Очистка
    loaded_image.close()
    resized_image.close()
