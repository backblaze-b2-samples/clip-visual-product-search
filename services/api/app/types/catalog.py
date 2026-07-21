from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    """Finite product categories — a selector (not free text) in the UI."""

    apparel = "Apparel"
    footwear = "Footwear"
    accessories = "Accessories"
    home = "Home"
    electronics = "Electronics"
    beauty = "Beauty"


class Currency(StrEnum):
    usd = "USD"
    eur = "EUR"
    gbp = "GBP"


class Product(BaseModel):
    """A catalog item: SKU + image + metadata + (implicit) CLIP embedding."""

    sku: str
    title: str
    price: float
    currency: Currency
    category: Category
    image_key: str
    created_at: datetime
    # Presigned (or public) URL for browser rendering. Populated on read;
    # never persisted (presigned URLs are short-lived).
    image_url: str | None = None


class ProductCreate(BaseModel):
    """Boundary model for the create form (image arrives as multipart bytes)."""

    sku: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=200)
    price: float = Field(ge=0)
    currency: Currency
    category: Category


class ProductUpdate(BaseModel):
    """Metadata-only edit. The image is replaced via a separate multipart part."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    category: Category | None = None


class CatalogStats(BaseModel):
    product_count: int
    embedding_count: int
    index_vector_count: int
    catalog_bytes: int
    catalog_bytes_human: str


class CatalogGrowthPoint(BaseModel):
    date: str
    products: int
