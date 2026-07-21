from enum import StrEnum

from pydantic import BaseModel

from app.types.catalog import Product


class SearchMode(StrEnum):
    text = "text"
    image = "image"


class SearchResult(BaseModel):
    """A single ranked hit: the matched product plus its similarity score."""

    product: Product
    # Cosine similarity in [-1, 1] (vectors are L2-normalized, inner product).
    score: float


class SearchResponse(BaseModel):
    mode: SearchMode
    query: str | None = None
    count: int
    results: list[SearchResult]
