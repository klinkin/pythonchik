"""Script to generate a basic set of test images."""

from pathlib import Path

from PIL import Image


def create_test_images(output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Basic RGB image
    rgb_image = Image.new("RGB", (100, 100), color="red")
    rgb_image.save(output_path / "test_rgb.png")

    # Grayscale image
    gray_image = Image.new("L", (100, 100), color=128)
    gray_image.save(output_path / "test_gray.png")

    # RGBA image with transparency
    rgba_image = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    rgba_image.save(output_path / "test_rgba.png")

    # Different formats
    test_image = Image.new("RGB", (100, 100), "blue")
    test_image.save(output_path / "test.jpg", "JPEG")
    test_image.save(output_path / "test.png", "PNG")


if __name__ == "__main__":
    create_test_images("test_images")
    print("Test images generated successfully!")
