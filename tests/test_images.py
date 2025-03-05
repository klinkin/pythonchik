"""Тесты для модуля обработки изображений.

Тестирование функциональности класса ImageProcessor, включая
изменение размера, конвертацию форматов и пакетную обработку изображений.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

from pythonchik import config
from pythonchik.errors.error_handlers import ImageProcessingError
from pythonchik.utils.image import ImageProcessor


@pytest.fixture
def test_image() -> Image.Image:
    """Создание тестового изображения."""
    img = Image.new("RGB", (100, 100), color="red")
    return img


@pytest.fixture
def temp_image_file(tmp_path: Path, test_image: Image.Image) -> Path:
    """Создание временного файла изображения для тестирования."""
    image_path = tmp_path / "test_image.png"
    test_image.save(image_path)
    return image_path


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Создание временной директории для выходных файлов."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def test_resize_image(temp_image_file: Path, temp_output_dir: Path) -> None:
    """Тестирование метода resize_image."""
    # Тест успешного изменения размера
    ImageProcessor.resize_image(str(temp_image_file), str(temp_output_dir))
    output_path = temp_output_dir / f"{temp_image_file.stem}.png"
    assert output_path.exists()

    # Проверка размеров
    with Image.open(output_path) as img:
        width, height = img.size
        original_size = Image.open(temp_image_file).size
        assert width == original_size[0] // config.IMAGE_RESIZE_RATIO
        assert height == original_size[1] // config.IMAGE_RESIZE_RATIO

    # Тест с несуществующим файлом
    # Ожидаем ImageProcessingError вместо FileNotFoundError, так как метод
    # оборачивает FileNotFoundError в ImageProcessingError
    with pytest.raises(ImageProcessingError):
        ImageProcessor.resize_image("nonexistent.jpg", str(temp_output_dir))

    # Тест с некорректной директорией
    # Ожидаем ImageProcessingError вместо PermissionError, так как метод
    # проверяет существование директории и выбрасывает ImageProcessingError
    with pytest.raises(ImageProcessingError):
        ImageProcessor.resize_image(str(temp_image_file), "/nonexistent/dir")


def test_compress_multiple_images(temp_image_file: Path, temp_output_dir: Path) -> None:
    """Тестирование метода compress_multiple_images."""
    # Создание дополнительного тестового файла
    second_image = temp_image_file.parent / "test_image2.png"
    Image.new("RGB", (200, 200), color="blue").save(second_image)

    # Тест обработки нескольких файлов
    files = [str(temp_image_file), str(second_image)]
    processed_files = ImageProcessor.compress_multiple_images(files, str(temp_output_dir))

    assert len(processed_files) == 2
    for file in processed_files:
        assert file.exists()
        assert file.suffix == ".png"

    # Тест с несуществующим файлом в списке
    files.append("nonexistent.jpg")
    processed_files = ImageProcessor.compress_multiple_images(files, str(temp_output_dir))
    assert len(processed_files) == 2  # Должно быть обработано только 2 существующих файла


def test_convert_format(temp_image_file: Path, temp_output_dir: Path) -> None:
    """Тестирование метода convert_format."""
    output_path = temp_output_dir / "converted.png"

    # Тест успешной конвертации
    ImageProcessor.convert_format(str(temp_image_file), str(output_path))
    assert output_path.exists()

    # Проверка формата
    with Image.open(output_path) as img:
        assert img.format == "PNG"

    # Тест с несуществующим файлом
    with pytest.raises(FileNotFoundError):
        ImageProcessor.convert_format("nonexistent.jpg", str(output_path))

    # Тест с некорректным выходным путем
    with pytest.raises(PermissionError):
        ImageProcessor.convert_format(str(temp_image_file), "/nonexistent/dir/image.png")


def test_convert_multiple_images(temp_image_file: Path, temp_output_dir: Path) -> None:
    """Тестирование метода convert_multiple_images."""
    # Создание дополнительных тестовых файлов разных форматов
    jpeg_file = temp_image_file.parent / "test.jpg"
    Image.new("RGB", (100, 100), color="green").save(jpeg_file, format="JPEG")

    files = [str(temp_image_file), str(jpeg_file)]

    # Тест успешной конвертации нескольких файлов
    ImageProcessor.convert_multiple_images(files, str(temp_output_dir))

    # Проверка результатов
    for file in files:
        output_path = temp_output_dir / f"{Path(file).stem}.png"
        assert output_path.exists()
        with Image.open(output_path) as img:
            assert img.format == "PNG"

    # Тест с ошибкой
    with pytest.raises(OSError):
        ImageProcessor.convert_multiple_images(["nonexistent.jpg"], str(temp_output_dir))


def test_progress_callback() -> None:
    """Тестирование работы callback-функции прогресса."""
    progress_values = []
    messages = []

    def callback(progress: float, message: str) -> None:
        progress_values.append(progress)
        messages.append(message)

    # Создание временных файлов и директорий
    with Image.new("RGB", (100, 100), color="red") as img:
        temp_dir = Path(os.path.dirname(__file__)) / "temp_test_dir"
        temp_dir.mkdir(exist_ok=True)
        try:
            image_path = temp_dir / "test_callback.png"
            img.save(image_path)

            output_dir = temp_dir / "output"
            output_dir.mkdir(exist_ok=True)

            # Тестирование callback в resize_image
            ImageProcessor.resize_image(str(image_path), str(output_dir), callback)
            assert 0 in progress_values  # Начальный прогресс
            assert 100 in progress_values  # Конечный прогресс
            assert any("Обработка" in msg for msg in messages)
            assert any("Обработано" in msg for msg in messages)

        finally:
            # Очистка
            if temp_dir.exists():
                for file in temp_dir.glob("**/*"):
                    if file.is_file():
                        file.unlink()
                for dir_path in reversed(list(temp_dir.glob("**/*"))):
                    if dir_path.is_dir():
                        dir_path.rmdir()
                temp_dir.rmdir()
