import pytest

from pythonchik.services import (
    extract_addresses,
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
