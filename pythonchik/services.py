from typing import Any


def extract_addresses(data: dict[str, Any]) -> list[str]:
    """Извлечь адреса из данных каталога.

    Функция обрабатывает словарь с данными каталога и извлекает адреса из полей
    target_regions или target_shops. Если target_regions отсутствует или пуст,
    используется первый адрес из target_shops.

    Аргументы:
        data (Dict[str, Any]): Словарь с данными каталога, содержащий поля
            'catalogs' с вложенными полями 'target_regions' и 'target_shops'

    Возвращает:
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
    for catalog in data.get("catalogs", []):
        try:
            if catalog.get("target_regions"):
                addresses.append(catalog["target_regions"][0])
            else:
                addresses.append(catalog["target_shops"][0])
        except (KeyError, IndexError):
            continue
    return addresses


def check_coordinates_match(data: dict[str, Any]) -> tuple[list[str], int, int, int]:
    """Проверить соответствие между адресами и координатами.

    Аргументы:
        data: Словарь, содержащий каталоги и координаты магазинов

    Возвращает:
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

    if "catalogs" not in data or "target_shops_coords" not in data:
        raise ValueError("Отсутствуют обязательные поля")

    if not data.get("catalogs"):
        return [], 0, 0, 0

    try:
        shop_coords = set(data["target_shops_coords"])
        catalog_shops = []

        for catalog in data["catalogs"]:
            if not isinstance(catalog, dict) or "target_shops" not in catalog or not catalog["target_shops"]:
                raise ValueError("Некорректный формат каталога")
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
            if offer["barcode"] not in barcodes and len(offer["barcode"]) > 5:
                barcodes.append(offer["barcode"])
        except KeyError:
            continue
    return barcodes


def count_unique_offers(data: dict[str, Any]) -> tuple[int, int]:
    """Подсчитать общее количество и уникальные предложения.

    Аргументы:
        data: Словарь, содержащий данные предложений

    Возвращает:
        Кортеж, содержащий общее количество и количество уникальных предложений

    Исключения:
        ValueError: Если в предложении отсутствуют обязательные поля или структура данных некорректна
    """
    if not isinstance(data, dict):
        raise ValueError("Входные данные должны быть словарем")

    if "offers" not in data:
        raise ValueError("Отсутствует поле 'offers'")

    if not data.get("offers"):
        return 0, 0

    offers = []
    count = 0

    for offer in data["offers"]:
        if not isinstance(offer, dict):
            raise ValueError("Некорректный формат предложения")
        if "description" not in offer:
            raise ValueError("Отсутствует поле 'description' в предложении")
        if not offer["description"]:
            raise ValueError("Пустое поле 'description' в предложении")

        count += 1
        if offer["description"] not in offers:
            offers.append(offer["description"])

    return count, len(offers)


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

    Аргументы:
        data: Словарь, содержащий данные предложений

    Возвращает:
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
