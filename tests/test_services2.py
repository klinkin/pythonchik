import pytest

from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
)
from pythonchik.types import CatalogData


@pytest.fixture
def sample_data() -> CatalogData:
    return {
        "catalogs": [
            {
                "target_regions": ["Moscow Region"],
                "target_shops": ["Shop A"],
                "offers": ["offer1", "offer2"],
            },
            {
                "target_regions": ["Saint Petersburg"],
                "target_shops": ["Shop B"],
                "offers": ["offer3", "offer4"],
            },
            {"target_regions": [], "target_shops": ["Shop C"], "offers": ["offer5"]},
        ],
        "offers": [
            {
                "id": "offer1",
                "description": "Product A",
                "barcode": "123456789",
                "price_new": 100,
                "price_old": 120,
            },
            {
                "id": "offer2",
                "description": "Product A",
                "barcode": "987654321",
                "price_new": 150,
                "price_old": 180,
            },
            {
                "id": "offer3",
                "description": "Product B",
                "barcode": "456789123",
                "price_new": 200,
            },
            {"id": "offer4", "description": "Product C", "price_new": 300},
            {
                "id": "offer5",
                "description": "Product D",
                "barcode": "789123456",
                "price_new": 400,
                "price_old": 450,
            },
        ],
        "target_shops_coords": ["Shop A", "Shop B"],
    }


def test_extract_addresses(sample_data: CatalogData) -> None:
    # Тестирование нормального случая с примером данных
    addresses = extract_addresses(dict(sample_data))
    assert len(addresses) == 3
    assert "Moscow Region" in addresses
    assert "Saint Petersburg" in addresses
    assert "Shop C" in addresses

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    assert extract_addresses(dict(empty_data)) == []

    # Тестирование случая с пустым списком target_regions
    data_empty_regions: CatalogData = {
        "catalogs": [{"target_regions": [], "target_shops": ["Shop A"], "offers": ["offer1"]}],
        "offers": [],
        "target_shops_coords": [],
    }
    assert "Shop A" in extract_addresses(dict(data_empty_regions))

    # Тестирование случая с дублирующимися регионами
    duplicate_data: CatalogData = {
        "catalogs": [
            {
                "target_regions": ["Moscow Region", "Moscow Region"],
                "target_shops": ["Shop A", "Shop B"],
                "offers": ["offer1"],
            }
        ],
        "offers": [],
        "target_shops_coords": [],
    }
    result = extract_addresses(dict(duplicate_data))
    assert len(result) == 1
    assert result[0] == "Moscow Region"


def test_check_coordinates_match(sample_data: CatalogData) -> None:
    # Тестирование нормального случая
    no_coords, total_catalogs, total_coords, matched = check_coordinates_match(dict(sample_data))
    assert total_catalogs == 3
    assert total_coords == 2
    assert matched == 2
    assert len(no_coords) == 1
    assert "Shop C" in no_coords

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    assert check_coordinates_match(dict(empty_data)) == ([], 0, 0, 0)

    # Тестирование некорректных данных
    with pytest.raises(ValueError, match="Входные данные должны быть словарем"):
        check_coordinates_match([])

    # Тестирование отсутствующих полей
    invalid_data = {"catalogs": []}
    with pytest.raises(ValueError, match="Отсутствуют обязательные поля"):
        check_coordinates_match(invalid_data)


def test_extract_barcodes(sample_data: CatalogData) -> None:
    # Тестирование нормального случая
    barcodes = extract_barcodes(dict(sample_data))
    assert len(barcodes) == 4
    assert "123456789" in barcodes
    assert "987654321" in barcodes
    assert "456789123" in barcodes
    assert "789123456" in barcodes

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    assert extract_barcodes(dict(empty_data)) == []

    # Тестирование предложения без штрихкода
    data_no_barcode: CatalogData = {"offers": [{"id": "offer1", "description": "Test", "price_new": 100}]}
    assert extract_barcodes(data_no_barcode) == []

    # Тестирование некорректного штрихкода
    data_invalid_barcode: CatalogData = {
        "offers": [{"id": "offer1", "description": "Test", "barcode": "123"}]
    }
    assert extract_barcodes(data_invalid_barcode) == []


def test_count_unique_offers(sample_data: CatalogData) -> None:
    # Тестирование нормального случая
    total, unique = count_unique_offers(dict(sample_data))
    assert total == 5
    assert unique == 4  # Product A встречается дважды

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    assert count_unique_offers(dict(empty_data)) == (0, 0)

    # Тестирование отсутствующего поля description
    invalid_data = {"offers": [{"id": "offer1"}]}
    with pytest.raises(ValueError, match="Отсутствует поле 'description' в предложении"):
        count_unique_offers(invalid_data)

    # Тестирование пустого description
    data_empty_desc = {"offers": [{"id": "offer1", "description": ""}]}
    with pytest.raises(ValueError, match="Пустое поле 'description' в предложении"):
        count_unique_offers(data_empty_desc)


def test_analyze_price_differences(sample_data: CatalogData) -> None:
    # Тестирование нормального случая
    diffs, count, total = analyze_price_differences(dict(sample_data))
    assert len(diffs) == 1  # Только Product A имеет разные цены
    assert diffs[0] == 50  # 150 - 100
    assert count == 1
    assert total == 4

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    assert analyze_price_differences(dict(empty_data)) == ([], 0, 0)

    # Тестирование отсутствующего поля price_new
    invalid_data = {"offers": [{"description": "Test"}]}
    with pytest.raises(KeyError, match="Missing 'price_new' field"):
        analyze_price_differences(invalid_data)

    # Тестирование отрицательной цены
    negative_price_data = {"offers": [{"description": "Test", "price_new": -100}]}
    with pytest.raises(ValueError, match="Negative price value"):
        analyze_price_differences(negative_price_data)


def test_create_test_json(sample_data: CatalogData) -> None:
    # Тестирование нормального случая
    result = create_test_json(dict(sample_data))

    # Проверка структуры результата
    assert "catalogs" in result
    assert "offers" in result
    assert "target_shops_coords" in result

    # Проверка ограничения предложений в каталогах
    for catalog in result["catalogs"]:
        if "offers" in catalog:
            assert len(catalog["offers"]) <= 1

    # Проверка соответствия предложений
    offer_ids = [offer["id"] for offer in result["offers"]]
    for catalog in result["catalogs"]:
        if catalog.get("offers"):
            assert catalog["offers"][0] in offer_ids

    # Тестирование пустых данных
    empty_data: CatalogData = {"catalogs": [], "offers": [], "target_shops_coords": []}
    empty_result = create_test_json(dict(empty_data))
    assert empty_result == {"catalogs": [], "offers": [], "target_shops_coords": []}
