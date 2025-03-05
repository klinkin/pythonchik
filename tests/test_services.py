from decimal import Decimal
from typing import Any

import pytest

from pythonchik.services import (
    analyze_price_differences,
    check_coordinates_match,
    count_unique_offers,
    create_test_json,
    extract_addresses,
    extract_barcodes,
)
from pythonchik.types import Catalog, CatalogData, Offer


@pytest.fixture
def sample_data() -> dict:
    data: CatalogData = CatalogData(
        catalogs=[
            Catalog(
                target_regions=["Moscow Region"],
                target_shops=["Shop A"],
                offers=["offer1", "offer2"],
            ),
            Catalog(
                target_regions=["Saint Petersburg"],
                target_shops=["Shop B"],
                offers=["offer3", "offer4"],
            ),
            Catalog(
                target_regions=["Shop C Region"],
                target_shops=["Shop C"],
                offers=["offer5"],
            ),
        ],
        offers=[
            Offer(
                id="offer1",
                description="Product A",
                barcode="123456789",
                price_new=Decimal("100"),
                price_old=Decimal("120"),
            ),
            Offer(
                id="offer2",
                description="Product A",
                barcode="987654321",
                price_new=Decimal("150"),
                price_old=Decimal("180"),
            ),
            Offer(
                id="offer3",
                description="Product B",
                barcode="456789123",
                price_new=Decimal("200"),
                price_old=None,
            ),
            Offer(
                id="offer4",
                description="Product C",
                barcode="654321789",
                price_new=Decimal("300"),
                price_old=None,
            ),
            Offer(
                id="offer5",
                description="Product D",
                barcode="789123456",
                price_new=Decimal("400"),
                price_old=Decimal("450"),
            ),
        ],
        target_shops_coords=["Shop A", "Shop B"],
    )
    return data.model_dump()


def test_extract_addresses_with_target_regions(sample_data):
    addresses = extract_addresses(sample_data)
    assert len(addresses) == 3
    assert "Moscow Region" in addresses
    assert "Saint Petersburg" in addresses
    assert "Shop C Region" in addresses


def test_extract_addresses_without_target_regions():
    data = {
        "catalogs": [
            {"target_shops": ["Shop X"], "offers": []},
            {"target_shops": ["Shop Y"], "offers": []},
        ]
    }
    addresses = extract_addresses(data)
    assert len(addresses) == 2
    assert "Shop X" in addresses
    assert "Shop Y" in addresses


def test_extract_addresses_empty_data():
    assert extract_addresses({}) == []
    assert extract_addresses({"catalogs": []}) == []


def test_check_coordinates_match_success(sample_data):
    unmatched, total, coords_count, matched = check_coordinates_match(sample_data)
    assert len(unmatched) == 1
    assert total == 3
    assert coords_count == 2
    assert matched == 2
    assert "Shop C" in unmatched


def test_check_coordinates_match_empty_data():
    result = check_coordinates_match({"catalogs": []})
    assert result == ([], 0, 0, 0)


def test_check_coordinates_match_invalid_data():
    invalid_data: Any = []
    with pytest.raises(ValueError, match="Входные данные должны быть словарем"):
        check_coordinates_match(invalid_data)

    with pytest.raises(ValueError, match="Отсутствует обязательное поле: catalogs"):
        check_coordinates_match({})


def test_extract_barcodes_success(sample_data):
    barcodes = extract_barcodes(sample_data)
    assert len(barcodes) == 5
    assert "123456789" in barcodes
    assert "987654321" in barcodes
    assert "456789123" in barcodes


def test_extract_barcodes_empty_data():
    assert extract_barcodes({}) == []
    assert extract_barcodes({"offers": []}) == []


def test_extract_barcodes_invalid_data():
    data = {"offers": [{"barcode": "123"}, {"barcode": None}, {}]}
    assert extract_barcodes(data) == []


def test_count_unique_offers_success(sample_data):
    total, unique = count_unique_offers(sample_data)
    assert total == 5
    assert unique == 4  # Product A appears twice


def test_count_unique_offers_empty_data():
    assert count_unique_offers({"offers": []}) == (0, 0)


def test_count_unique_offers_invalid_data():
    invalid_data: Any = []
    with pytest.raises(ValueError, match="Входные данные должны быть словарем"):
        count_unique_offers(invalid_data)

    with pytest.raises(ValueError, match="Отсутствует поле 'offers'"):
        count_unique_offers({})

    with pytest.raises(ValueError, match="Некорректный формат предложения"):
        count_unique_offers({"offers": ["not a dict"]})


def test_create_test_json_success(sample_data):
    result = create_test_json(sample_data)
    assert len(result["catalogs"]) == 3
    assert len(result["offers"]) == 3
    for catalog in result["catalogs"]:
        assert len(catalog["offers"]) == 1


def test_create_test_json_empty_data():
    result = create_test_json({})
    assert result == {"catalogs": [], "offers": [], "target_shops_coords": []}


def test_create_test_json_missing_offers():
    data = {"catalogs": [{"target_regions": ["Region"]}]}
    result = create_test_json(data)
    assert result["catalogs"][0].get("offers") is None


def test_analyze_price_differences_success(sample_data):
    diffs, diff_count, total = analyze_price_differences(sample_data)
    assert len(diffs) == 1  # Only Product A has different prices
    assert diff_count == 1
    assert total == 4
    assert diffs[0] == 50  # 150 - 100 = 50


def test_analyze_price_differences_invalid_data():
    with pytest.raises(KeyError, match="Missing 'description' field in offer"):
        analyze_price_differences({"offers": [{"price_new": 100}]})

    with pytest.raises(KeyError, match="Missing 'price_new' field"):
        analyze_price_differences({"offers": [{"description": "Product"}]})

    with pytest.raises(ValueError, match="Invalid price value"):
        analyze_price_differences({"offers": [{"description": "Product", "price_new": "100"}]})

    with pytest.raises(ValueError, match="Negative price value"):
        analyze_price_differences({"offers": [{"description": "Product", "price_new": -100}]})


def test_analyze_price_differences_empty_data():
    assert analyze_price_differences({}) == ([], 0, 0)
    assert analyze_price_differences({"offers": []}) == ([], 0, 0)


def test_extract_addresses_invalid_data():
    data = {"catalogs": [{"target_regions": "не список"}]}
    with pytest.raises(TypeError):
        extract_addresses(data)
