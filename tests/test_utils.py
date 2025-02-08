import json
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import mock_open, patch

import pytest

from pythonchik.utils import (
    create_archive,
    load_json_file,
    process_multiple_files,
    save_to_csv,
)


def test_load_json_file(tmp_path: Path) -> None:
    """Test the load_json_file function with various scenarios."""
    # Test successful JSON loading
    test_data = {"test": "data", "number": 42}
    test_file = tmp_path / "test.json"

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_data, f)

    result = load_json_file(str(test_file))
    assert result == test_data
    assert isinstance(result, dict)
    assert result["test"] == "data"
    assert result["number"] == 42

    # Test file not found error
    with pytest.raises(FileNotFoundError) as exc_info:
        load_json_file("nonexistent.json")
    assert "JSON файл не найден" in str(exc_info.value)

    # Test invalid JSON format
    invalid_json = tmp_path / "invalid.json"
    with open(invalid_json, "w", encoding="utf-8") as f:
        f.write("{invalid json}")

    with pytest.raises(json.JSONDecodeError) as exc_info:
        load_json_file(str(invalid_json))
    assert "Некорректный формат JSON" in str(exc_info.value)

    # Test incorrect encoding
    with patch("builtins.open", mock_open(read_data=b"\xff\xff\xff\xff")):
        with pytest.raises(UnicodeDecodeError) as exc_info:
            load_json_file("test.json")
        assert "Некорректная кодировка файла" in str(exc_info.value)

    # Test empty file
    empty_file = tmp_path / "empty.json"
    with open(empty_file, "w", encoding="utf-8") as f:
        f.write("")

    with pytest.raises(json.JSONDecodeError) as exc_info:
        load_json_file(str(empty_file))
    assert "Некорректный формат JSON" in str(exc_info.value)

    # Test large JSON file
    large_data = {"items": [i for i in range(1000)]}
    large_file = tmp_path / "large.json"
    with open(large_file, "w", encoding="utf-8") as f:
        json.dump(large_data, f)

    result = load_json_file(str(large_file))
    assert result == large_data
    assert len(result["items"]) == 1000

    # Test JSON with special characters
    special_data = {
        "special": "спец символы",
        "quotes": '"quoted"',
        "path": "C:\\Program Files\\Test",
    }
    special_file = tmp_path / "special.json"
    with open(special_file, "w", encoding="utf-8") as f:
        json.dump(special_data, f)

    result = load_json_file(str(special_file))
    assert result == special_data
    assert result["special"] == "спец символы"
    assert result["quotes"] == '"quoted"'
    assert result["path"] == "C:\\Program Files\\Test"


def test_process_multiple_files(tmp_path: Path) -> None:
    """Test the process_multiple_files function with various scenarios."""
    # Test successful processing of multiple files
    test_data1 = {"items": [1, 2, 3]}
    test_data2 = {"items": [4, 5, 6]}

    file1 = tmp_path / "test1.json"
    file2 = tmp_path / "test2.json"

    with open(file1, "w", encoding="utf-8") as f:
        json.dump(test_data1, f)
    with open(file2, "w", encoding="utf-8") as f:
        json.dump(test_data2, f)

    def processor_func(data: dict[str, Any]) -> list[int]:
        return data["items"]

    result = process_multiple_files([str(file1), str(file2)], processor_func)
    assert result == [1, 2, 3, 4, 5, 6]

    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        process_multiple_files(["nonexistent.json"], processor_func)


def test_save_to_csv(tmp_path: Path) -> None:
    """Test the save_to_csv function with various scenarios."""
    # Test successful CSV creation
    data = ["item1", "item2", "item3"]
    header = ["Items"]
    output_path = tmp_path / "test.csv"

    save_to_csv(data, header, str(output_path))

    with open(output_path, encoding="utf-8") as f:
        content = f.read().splitlines()
        assert content[0] == "Items"
        assert content[1] == "item1"
        assert content[2] == "item2"
        assert content[3] == "item3"

    # Test permission error
    with patch("builtins.open", side_effect=PermissionError):
        with pytest.raises(PermissionError) as exc_info:
            save_to_csv(data, header, str(output_path))
        assert "Отказано в доступе" in str(exc_info.value)

    # Test OS error
    with patch("builtins.open", side_effect=OSError):
        with pytest.raises(OSError) as exc_info:
            save_to_csv(data, header, str(output_path))
        assert "Ошибка при записи в CSV файл" in str(exc_info.value)


def test_create_archive(tmp_path: Path) -> None:
    """Test the create_archive function with various scenarios."""
    # Test successful archive creation
    test_files = []
    file_contents = ["content1", "content2", "content3"]

    for i, content in enumerate(file_contents, 1):
        file_path = tmp_path / f"test{i}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        test_files.append(str(file_path))

    archive_path = tmp_path / "test_archive.zip"
    create_archive(test_files, str(archive_path))

    assert archive_path.exists()
    with zipfile.ZipFile(archive_path) as zf:
        assert len(zf.namelist()) == len(test_files)
        for i, content in enumerate(file_contents, 1):
            with zf.open(f"test{i}.txt") as f:
                assert f.read().decode() == content

    # Test with non-existent file
    with pytest.raises(FileNotFoundError) as exc_info:
        create_archive(["nonexistent.txt"], str(archive_path))
    assert "Файл не найден" in str(exc_info.value)

    # Test permission error
    with patch("zipfile.ZipFile", side_effect=PermissionError):
        with pytest.raises(PermissionError) as exc_info:
            create_archive(test_files, str(archive_path))
        assert "Отказано в доступе" in str(exc_info.value)

    # Test OS error
    with patch("zipfile.ZipFile", side_effect=OSError):
        with pytest.raises(OSError) as exc_info:
            create_archive(test_files, str(archive_path))
        assert "Не удалось создать архив" in str(exc_info.value)
