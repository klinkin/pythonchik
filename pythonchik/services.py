import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Загрузка и парсинг JSON файла.

    Функция загружает JSON файл по указанному пути и преобразует его в словарь Python.
    Поддерживает обработку файлов в кодировке UTF-8.

    Аргументы:
        file_path (str): Полный путь к JSON файлу для загрузки

    Возвращает:
        Dict[str, Any]: Словарь, содержащий распарсенные JSON данные

    Исключения:
        FileNotFoundError: Если файл не существует по указанному пути
        json.JSONDecodeError: Если содержимое файла не является корректным JSON
        UnicodeDecodeError: Если файл содержит символы в неподдерживаемой кодировке

    Пример использования:
        >>> data = load_json_file('data.json')
        >>> print(data['catalogs'][0]['target_shops'])
        ['Магазин 1', 'Магазин 2']
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"JSON файл не найден: {file_path}") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Некорректный формат JSON в файле {file_path}: {str(e)}", e.doc, e.pos
        )
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            f"Некорректная кодировка файла {file_path}: {str(e)}", *e.args[1:]
        )


def extract_addresses(data: Dict[str, Any]) -> List[str]:
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
            addresses.append(
                catalog.get("target_regions", [catalog["target_shops"][0]])[0]
            )
        except (KeyError, IndexError):
            continue
    return addresses


def save_to_csv(data: List[Any], header: List[str], output_path: str) -> None:
    """Сохранить данные в CSV файл.

    Аргументы:
        data: Список данных для сохранения
        header: Список заголовков столбцов
        output_path: Путь для сохранения CSV файла

    Исключения:
        PermissionError: Если нет прав на запись в файл
        OSError: Если произошла ошибка при записи в файл
    """
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows([[item] for item in data])
    except PermissionError as e:
        raise PermissionError(
            f"Отказано в доступе при записи в файл {output_path}"
        ) from e
    except OSError as e:
        raise OSError(f"Ошибка при записи в CSV файл {output_path}: {str(e)}") from e


def check_coordinates_match(data: Dict[str, Any]) -> Tuple[List[str], int, int, int]:
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
        KeyError: Если структура данных некорректна
        IndexError: Если массив target_shops пуст
    """
    segment = []
    koor = []
    nkoor = []
    count = 0

    try:
        for catalog in data.get("catalogs", []):
            if not catalog.get("target_shops"):
                raise KeyError("Отсутствует target_shops в каталоге")
            segment.append(catalog["target_shops"][0])

        for shop in data.get("target_shops_coords", []):
            koor.append(shop)

        for shop in segment:
            if shop not in koor:
                nkoor.append(str(shop))
            else:
                count += 1

        return nkoor, len(segment), len(koor), count
    except (KeyError, IndexError) as e:
        raise ValueError(f"Некорректная структура данных: {str(e)}") from e


def extract_barcodes(data: Dict[str, Any]) -> List[str]:
    """Извлечь уникальные штрих-коды из предложений."""
    barcodes = []
    for offer in data.get("offers", []):
        try:
            if offer["barcode"] not in barcodes and len(offer["barcode"]) > 5:
                barcodes.append(offer["barcode"])
        except KeyError:
            continue
    return barcodes


def count_unique_offers(data: Dict[str, Any]) -> Tuple[int, int]:
    """Подсчитать общее количество и уникальные предложения.

    Аргументы:
        data: Словарь, содержащий данные предложений

    Возвращает:
        Кортеж, содержащий общее количество и количество уникальных предложений

    Исключения:
        KeyError: Если в предложении отсутствуют обязательные поля
    """
    offers = []
    count = 0
    try:
        for offer in data.get("offers", []):
            count += 1
            if "description" not in offer:
                raise KeyError("Отсутствует поле 'description' в предложении")
            if offer["description"] not in offers:
                offers.append(offer["description"])
        return count, len(offers)
    except KeyError as e:
        raise ValueError(f"Некорректные данные предложения: {str(e)}") from e


def create_test_json(data: Dict[str, Any]) -> Dict[str, Any]:
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


def analyze_price_differences(data: Dict[str, Any]) -> Tuple[List[float], int, int]:
    """Анализ разницы цен в предложениях.

    Аргументы:
        data: Словарь, содержащий данные предложений

    Возвращает:
        Кортеж, содержащий:
        - Список разниц в ценах
        - Количество товаров с разными ценами
        - Общее количество уникальных товаров

    Исключения:
        ValueError: Если данные о ценах некорректны
        KeyError: Если отсутствуют обязательные поля
    """
    segment = []
    price_diffs = []
    count = 0

    try:
        for offer in data.get("offers", []):
            if "description" not in offer:
                raise KeyError("Missing 'description' field in offer")
            if offer["description"] not in segment:
                segment.append(offer["description"])

        for desc in segment:
            prices = []
            for offer in data["offers"]:
                if desc == offer["description"]:
                    if "price_new" not in offer:
                        raise KeyError(f"Missing 'price_new' field for offer: {desc}")
                    price = offer["price_new"]
                    if not isinstance(price, (int, float)):
                        raise ValueError(
                            f"Некорректное значение цены для {desc}: {price}"
                        )
                    if price not in prices:
                        prices.append(price)

            if len(prices) > 1:
                price_diffs.append(max(prices) - min(prices))
                count += 1

        return price_diffs, count, len(segment)
    except (KeyError, ValueError) as e:
        raise ValueError(f"Ошибка обработки данных о ценах: {str(e)}") from e
