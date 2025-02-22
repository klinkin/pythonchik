from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Offer(BaseModel):
    """Модель предложения в каталоге с валидацией.

    Описание:
        Расширенная модель для представления предложения в каталоге с встроенной валидацией полей.

    Аргументы:
        id (str): Уникальный идентификатор предложения
        description (str): Описание продукта
        barcode (str): Штрих-код продукта
        price_new (Decimal): Текущая цена предложения
        price_old (Optional[Decimal]): Предыдущая цена, если доступна

    Особенности:
        - Все поля проходят автоматическую валидацию
        - Штрих-код должен содержать только цифры
        - Цены не могут быть отрицательными
    """

    id: str = Field(..., description="Уникальный идентификатор предложения")
    description: str = Field(..., min_length=1, description="Описание продукта")
    barcode: str = Field(..., min_length=5, description="Штрих-код продукта")
    price_new: Decimal = Field(..., ge=0, description="Текущая цена предложения")
    price_old: Optional[Decimal] = Field(None, ge=0, description="Предыдущая цена, если доступна")

    @field_validator("barcode")
    def validate_barcode(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Штрих-код должен содержать только цифры")
        return v


class Catalog(BaseModel):
    """Модель каталога с валидацией.

    Описание:
        Расширенная модель для представления записи каталога с встроенной валидацией полей.

    Аргументы:
        target_regions (List[str]): Список целевых регионов
        target_shops (List[str]): Список целевых магазинов
        offers (List[str]): Список идентификаторов предложений

    Особенности:
        - Списки регионов и магазинов не могут быть пустыми
        - Строки в списках не могут быть пустыми
    """

    target_regions: List[str] = Field(..., min_length=1, description="Список целевых регионов")
    target_shops: List[str] = Field(..., min_length=1, description="Список целевых магазинов")
    offers: List[str] = Field(default_factory=list, description="Список идентификаторов предложений")

    @field_validator("target_regions", "target_shops")
    def validate_non_empty_strings(cls, v: List[str]) -> List[str]:
        if any(not s.strip() for s in v):
            raise ValueError("Пустые строки не допускаются")
        return v


class CatalogData(BaseModel):
    """Модель полной структуры данных каталога с валидацией.

    Описание:
        Расширенная модель для представления полной структуры данных каталога
        с встроенной валидацией всех компонентов.

    Аргументы:
        catalogs (List[Catalog]): Список каталогов
        offers (List[Offer]): Список предложений
        target_shops_coords (List[str]): Список координат магазинов

    Особенности:
        - Валидация при присваивании значений
        - Автоматическое кодирование десятичных чисел в строки
    """

    catalogs: List[Catalog] = Field(default_factory=list, description="Список каталогов")
    offers: List[Offer] = Field(default_factory=list, description="Список предложений")
    target_shops_coords: List[str] = Field(..., description="Список координат магазинов")

    model_config = ConfigDict(validate_assignment=True, json_encoders={Decimal: lambda v: str(v)})

    def get_total_offers(self) -> int:
        """Получает общее количество предложений во всех каталогах.

        Описание:
            Подсчитывает общее количество предложений во всех каталогах.

        Возвращает:
            int: Общее количество предложений
        """
        return len(self.offers)

    def get_unique_regions(self) -> set[str]:
        """Получает множество уникальных регионов из всех каталогов.

        Описание:
            Собирает все уникальные регионы из всех каталогов в множество.

        Возвращает:
            set[str]: Множество уникальных регионов
        """
        return {region for catalog in self.catalogs for region in catalog.target_regions}
