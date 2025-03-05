from typing import Any

from pythonchik.utils.event_system import Event, EventBus, EventType


def extract_addresses(data: dict[str, Any], event_bus=None) -> list[str]:
    """Извлечь адреса из данных каталога.

    Функция обрабатывает словарь с данными каталога и извлекает адреса из полей
    target_regions или target_shops. Если target_regions отсутствует или пуст,
    используется первый адрес из target_shops.

    Args:
        data (Dict[str, Any]): Словарь с данными каталога, содержащий поля
            'catalogs' с вложенными полями 'target_regions' и 'target_shops'
        event_bus (Optional[EventBus]): Шина событий для отправки обновлений прогресса

    Returns:
        List[str]: Список извлеченных адресов

    Пример использования:
        >>> data = {
        ...     'catalogs': [{
        ...         'target_regions': ['Москва'],
        ...         'target_shops': ['ТЦ Метрополис']
        ...     }]
        ... }
        >>> addresses = extract_addresses(data)
        >>> print(addresses)
        ['Москва']
    """
    addresses = []
    catalogs = data.get("catalogs", [])
    total_catalogs = len(catalogs)

    for i, catalog in enumerate(catalogs):
        try:
            if catalog.get("target_regions"):
                addresses.append(catalog["target_regions"][0])
            else:
                addresses.append(catalog["target_shops"][0])

            if event_bus:
                progress = int((i + 1) / total_catalogs * 100)
                event_bus.publish(
                    Event(
                        EventType.PROGRESS_UPDATED,
                        {
                            "progress": progress,
                            "message": f"Обработано {i + 1} из {total_catalogs} каталогов",
                        },
                    )
                )

        except (KeyError, IndexError):
            continue

    return addresses


def check_coordinates_match(data: dict[str, Any]) -> tuple[list[str], int, int, int]:
    """Проверить соответствие между адресами и координатами.

    Args:
        data: Словарь, содержащий каталоги и координаты магазинов

    Returns:
        Кортеж, содержащий:
        - Список адресов без координат
        - Общее количество каталогов
        - Общее количество координат
        - Количество совпавших координат

    Исключения:
        ValueError: Если структура данных некорректна или отсутствуют обязательные поля
    """
    if not isinstance(data, dict):
        raise ValueError("Входные данные должны быть словарем")

    # Validate catalogs field first as it's the primary requirement
    if "catalogs" not in data:
        raise ValueError("Отсутствует обязательное поле: catalogs")

    if not data.get("catalogs"):
        return [], 0, 0, 0

    # If we have catalogs, validate target_shops_coords
    if "target_shops_coords" not in data:
        # Return all shops as unmatched if target_shops_coords is missing
        catalog_shops = []
        for catalog in data["catalogs"]:
            if not isinstance(catalog, dict):
                raise ValueError("Каталог должен быть словарем")
            if "target_shops" not in catalog or not catalog["target_shops"]:
                continue
            catalog_shops.append(catalog["target_shops"][0])
        return catalog_shops, len(catalog_shops), 0, 0

    try:
        # Validate target_shops_coords
        if not isinstance(data["target_shops_coords"], (list, tuple)):
            raise ValueError("Поле target_shops_coords должно быть списком")
        shop_coords = set(data["target_shops_coords"])
        catalog_shops = []

        # Process catalogs
        for i, catalog in enumerate(data["catalogs"]):
            if not isinstance(catalog, dict):
                raise ValueError(f"Каталог #{i + 1} должен быть словарем")
            if "target_shops" not in catalog:
                raise ValueError(f"Отсутствует поле target_shops в каталоге #{i + 1}")
            if not catalog["target_shops"]:
                raise ValueError(f"Пустой список target_shops в каталоге #{i + 1}")
            catalog_shops.append(catalog["target_shops"][0])

        unmatched_shops = [shop for shop in catalog_shops if shop not in shop_coords]
        matched_count = len(catalog_shops) - len(unmatched_shops)

        return unmatched_shops, len(catalog_shops), len(shop_coords), matched_count
    except (KeyError, IndexError) as e:
        raise ValueError(f"Некорректная структура данных: {str(e)}") from e


def extract_barcodes(data: dict[str, Any]) -> list[str]:
    """Извлечь уникальные штрих-коды из предложений."""
    barcodes = []
    for offer in data.get("offers", []):
        try:
            barcode = offer.get("barcode")
            if barcode and isinstance(barcode, str) and len(barcode) > 5 and barcode not in barcodes:
                barcodes.append(barcode)
        except (KeyError, TypeError):
            continue
    return barcodes


def count_unique_offers(data: dict[str, Any]) -> tuple[int, int]:
    """Подсчитать общее количество и уникальные предложения.

    Args:
        data: Словарь, содержащий данные предложений

    Returns:
        Кортеж, содержащий общее количество и количество уникальных предложений

    Исключения:
        ValueError: Если в предложении отсутствуют обязательные поля или структура данных некорректна
    """
    if not isinstance(data, dict):
        raise ValueError("Входные данные должны быть словарем")

    if "offers" not in data:
        raise ValueError("Отсутствует поле 'offers'")

    offers = data.get("offers", [])
    if not offers:
        return 0, 0

    unique_descriptions = set()
    for offer in offers:
        if not isinstance(offer, dict):
            raise ValueError("Некорректный формат предложения")
        if "description" not in offer:
            raise ValueError("Отсутствует поле 'description' в предложении")
        if not offer["description"]:
            raise ValueError("Пустое поле 'description' в предложении")

        unique_descriptions.add(offer["description"])

    return len(offers), len(unique_descriptions)


def create_test_json(data: dict[str, Any]) -> dict[str, Any]:
    """Создать тестовый JSON с ограниченными данными."""
    json_file = {"catalogs": data.get("catalogs", [])}

    for catalog in json_file["catalogs"]:
        if catalog.get("offers"):
            catalog["offers"] = [catalog["offers"][0]]

    koor = []
    for offer in data.get("offers", []):
        for catalog in json_file["catalogs"]:
            if catalog.get("offers") and offer["id"] == catalog["offers"][0]:
                koor.append(offer)

    json_file["offers"] = koor
    json_file["target_shops_coords"] = data.get("target_shops_coords", [])
    return json_file


def analyze_price_differences(data: dict[str, Any]) -> tuple[list[float], int, int]:
    """Анализ разницы цен в предложениях.

    Args:
        data: Словарь, содержащий данные предложений

    Returns:
        Кортеж, содержащий:
        - Список разниц в ценах
        - Количество товаров с разными ценами
        - Общее количество уникальных товаров

    Исключения:
        ValueError: Если данные о ценах некорректны или отрицательны
        KeyError: Если отсутствуют обязательные поля
    """
    if not data.get("offers"):
        return [], 0, 0

    unique_products = {}
    for offer in data["offers"]:
        if "description" not in offer:
            raise KeyError("Missing 'description' field in offer")
        if "price_new" not in offer:
            raise KeyError(f"Missing 'price_new' field for offer: {offer['description']}")

        price = offer["price_new"]
        if not isinstance(price, (int | float)):
            raise ValueError(f"Invalid price value for {offer['description']}: {price}")
        if price < 0:
            raise ValueError("Negative price value")

        desc = offer["description"]
        if desc not in unique_products:
            unique_products[desc] = set()
        unique_products[desc].add(price)

    price_diffs = []
    diff_count = 0
    for prices in unique_products.values():
        if len(prices) > 1:
            price_diffs.append(max(prices) - min(prices))
            diff_count += 1

    return price_diffs, diff_count, len(unique_products)
