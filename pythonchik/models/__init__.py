"""Модели данных приложения Pythonchik.

Этот модуль содержит Pydantic-модели для валидации, сериализации и десериализации данных,
используемых в приложении. Модели обеспечивают согласованность структур данных
и автоматическую валидацию при работе с внешними источниками.

Основные компоненты:
- Offer: Модель предложения с валидацией полей (идентификатор, описание, штрих-код, цены)
- Catalog: Модель каталога с целевыми регионами и магазинами
- CatalogData: Полная структура данных каталога со списками предложений и магазинов

Преимущества использования:
- Автоматическая валидация данных при создании и обновлении
- Четкое определение типов полей и их ограничений
- Автоматическая сериализация в JSON и десериализация
- Встроенные механизмы валидации значений (например, штрих-кодов)

Примеры использования:
    >>> from pythonchik.models import Catalog, Offer, CatalogData
    >>>
    >>> # Создание предложения с валидацией
    >>> offer = Offer(
    ...     id="12345",
    ...     description="Смартфон XYZ",
    ...     barcode="1234567890123",
    ...     price_new=Decimal("999.99"),
    ...     price_old=Decimal("1299.99")
    ... )
    >>>
    >>> # Создание каталога
    >>> catalog = Catalog(
    ...     target_regions=["Москва", "Санкт-Петербург"],
    ...     target_shops=["ТЦ Метрополис", "ТЦ Галерея"],
    ...     offers=["12345", "67890"]
    ... )
    >>>
    >>> # Полная структура каталога
    >>> data = CatalogData(
    ...     catalogs=[catalog],
    ...     offers=[offer],
    ...     target_shops_coords=["55.790307,37.530374", "59.927437,30.360550"]
    ... )
    >>>
    >>> # Сериализация в JSON
    >>> json_data = data.model_dump_json()
"""

from pythonchik.types import Catalog, CatalogData, Offer

__all__ = ["Catalog", "CatalogData", "Offer"]
