from typing import TypedDict


class Offer(TypedDict):
    """Type definition for an offer in the catalog."""

    id: str
    description: str
    barcode: str
    price_new: float


class Catalog(TypedDict):
    """Type definition for a catalog entry."""

    target_regions: list[str]
    target_shops: list[str]
    offers: list[str]


class CatalogData(TypedDict):
    """Type definition for the complete catalog data structure."""

    catalogs: list[Catalog]
    offers: list[Offer]
    target_shops_coords: list[str]
