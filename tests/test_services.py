import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
    load_json_file,
    save_to_csv,
)


@pytest.fixture
def sample_data():
    return {
        "catalogs": [
            {
                "target_regions": ["Region 1"],
                "target_shops": ["Shop 1"],
                "offers": ["offer1"],
            },
            {
                "target_regions": ["Region 2"],
                "target_shops": ["Shop 2"],
                "offers": ["offer2"],
            },
        ],
        "offers": [
            {
                "id": "offer1",
                "description": "Product 1",
                "barcode": "123456789",
                "price_new": 100,
            },
            {
                "id": "offer2",
                "description": "Product 1",
                "barcode": "987654321",
                "price_new": 150,
            },
        ],
        "target_shops_coords": ["Shop 1"],
    }


def test_load_json_file(tmp_path):
    test_data = {"test": "data"}
    test_file = tmp_path / "test.json"

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    result = load_json_file(str(test_file))
    assert result == test_data

    with pytest.raises(FileNotFoundError):
        load_json_file("nonexistent.json")

    # Тест некорректного формата JSON
    invalid_json = tmp_path / "invalid.json"
    with open(invalid_json, "w") as f:
        f.write("{invalid json}")
    with pytest.raises(json.JSONDecodeError):
        load_json_file(str(invalid_json))

    # Тест некорректной кодировки
    with patch("builtins.open", mock_open(read_data=b"\xff\xff\xff\xff")):
        with pytest.raises(UnicodeDecodeError):
            load_json_file("test.json")


def test_extract_addresses(sample_data):
    addresses = extract_addresses(sample_data)
    assert len(addresses) == 2
    assert "Region 1" in addresses
    assert "Region 2" in addresses

    # Тест с пустыми данными
    assert extract_addresses({}) == []

    # Тест с отсутствующими target_regions и target_shops
    invalid_data = {"catalogs": [{"other_field": "value"}]}
    assert extract_addresses(invalid_data) == []

    # Тест с пустым target_shops
    data_empty_shops = {"catalogs": [{"target_shops": []}]}
    assert extract_addresses(data_empty_shops) == []


def test_save_to_csv(tmp_path):
    data = ["item1", "item2"]
    header = ["Items"]
    output_path = tmp_path / "test.csv"

    save_to_csv(data, header, str(output_path))

    with open(output_path) as f:
        content = f.read().splitlines()
        assert content[0] == "Items"
        assert content[1] == "item1"
        assert content[2] == "item2"

    # Тест ошибки доступа
    with patch("builtins.open", side_effect=PermissionError):
        with pytest.raises(PermissionError):
            save_to_csv(data, header, str(output_path))

    # Тест ошибки операционной системы
    with patch("builtins.open", side_effect=OSError):
        with pytest.raises(OSError):
            save_to_csv(data, header, str(output_path))


def test_check_coordinates_match(sample_data):
    no_coords, total_catalogs, total_coords, matched = check_coordinates_match(
        sample_data
    )

    assert total_catalogs == 2
    assert total_coords == 1
    assert matched == 1
    assert len(no_coords) == 1
    assert "Shop 2" in no_coords

    # Тест с пустыми данными
    empty_result = check_coordinates_match({})
    assert empty_result == ([], 0, 0, 0)

    # Тест с отсутствующим target_shops
    invalid_data = {"catalogs": [{"other_field": "value"}]}
    with pytest.raises(ValueError):
        check_coordinates_match(invalid_data)

    # Тест с пустым target_shops
    data_empty_shops = {"catalogs": [{"target_shops": []}]}
    with pytest.raises(ValueError):
        check_coordinates_match(data_empty_shops)


def test_extract_barcodes(sample_data):
    barcodes = extract_barcodes(sample_data)
    assert len(barcodes) == 2
    assert "123456789" in barcodes
    assert "987654321" in barcodes

    # Test with invalid barcode
    invalid_data = {"offers": [{"barcode": "123"}]}
    assert extract_barcodes(invalid_data) == []

    # Test with missing barcode field
    missing_barcode = {"offers": [{"other_field": "value"}]}
    assert extract_barcodes(missing_barcode) == []

    # Test with duplicate barcodes
    duplicate_data = {"offers": [{"barcode": "123456789"}, {"barcode": "123456789"}]}
    assert len(extract_barcodes(duplicate_data)) == 1


def test_count_unique_offers(sample_data):
    total, unique = count_unique_offers(sample_data)
    assert total == 2
    assert unique == 1  # Both products have same description

    # Test with missing description field
    with pytest.raises(ValueError):
        count_unique_offers({"offers": [{"invalid": "data"}]})

    # Test with empty offers
    assert count_unique_offers({}) == (0, 0)

    # Test with unique descriptions
    unique_data = {
        "offers": [{"description": "Product 1"}, {"description": "Product 2"}]
    }
    total, unique = count_unique_offers(unique_data)
    assert total == 2
    assert unique == 2


def test_create_test_json(sample_data):
    result = create_test_json(sample_data)

    assert len(result["catalogs"]) == len(sample_data["catalogs"])
    for catalog in result["catalogs"]:
        assert len(catalog["offers"]) == 1

    assert "target_shops_coords" in result
    assert len(result["offers"]) == len(result["catalogs"])

    # Тест с пустыми данными
    empty_result = create_test_json({})
    assert empty_result == {"catalogs": [], "offers": [], "target_shops_coords": []}

    # Тест с отсутствующими предложениями
    no_offers = {"catalogs": [{"offers": []}]}
    result = create_test_json(no_offers)
    assert result["catalogs"] == [{"offers": []}]
    assert result["offers"] == []


def test_analyze_price_differences(sample_data):
    diffs, count, total = analyze_price_differences(sample_data)

    assert len(diffs) == 1
    assert diffs[0] == 50  # 150 - 100
    assert count == 1
    assert total == 1

    # Тест с некорректными данными о ценах
    invalid_data = {"offers": [{"description": "Test", "price_new": "invalid"}]}
    with pytest.raises(ValueError):
        analyze_price_differences(invalid_data)

    # Тест с отсутствующим полем цены
    missing_price = {"offers": [{"description": "Test"}]}
    with pytest.raises(ValueError):
        analyze_price_differences(missing_price)

    # Тест с пустыми предложениями
    assert analyze_price_differences({}) == ([], 0, 0)

    # Тест с одинаковыми ценами
    same_price_data = {
        "offers": [
            {"description": "Test", "price_new": 100},
            {"description": "Test", "price_new": 100},
        ]
    }
    diffs, count, total = analyze_price_differences(same_price_data)
    assert len(diffs) == 0
    assert count == 0
    assert total == 1
