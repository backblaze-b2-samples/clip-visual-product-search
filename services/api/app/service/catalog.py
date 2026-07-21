"""Product catalog orchestration: CRUD over the primary entity (`Product`).

Create is the full write path that makes the sample real end-to-end:
validate → embed the image with CLIP → write three parallel B2 artifacts
(image, `.npy` embedding, updated FAISS index) → upsert the metadata row.
Delete tears the same set down, scoped to the SKU's prefix. Nothing here talks
to boto3 directly — all B2 access goes through `repo/`, all embedding through
`service.clip_model`, all indexing through `service.index`.
"""

import io
import logging
import mimetypes
from datetime import UTC, datetime

import numpy as np

from app.config import settings
from app.repo import delete_key, delete_prefix, get_bytes, get_inline_url, put_bytes
from app.service import clip_model, index, metadata_store
from app.types import (
    CatalogGrowthPoint,
    CatalogStats,
    Category,
    Currency,
    Product,
    ProductCreate,
    ProductUpdate,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class CatalogError(Exception):
    """Raised on catalog validation / conflict failures."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _image_key(sku: str, filename: str) -> str:
    safe = filename.replace("/", "_").replace("\\", "_") or "image"
    return f"{settings.catalog_images_prefix}{sku}/{safe}"


def _embedding_key(sku: str) -> str:
    return f"{settings.catalog_embeddings_prefix}{sku}.npy"


def _content_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    if mime not in ALLOWED_IMAGE_TYPES:
        raise CatalogError(
            "Unsupported image type — use JPEG, PNG, WebP, or GIF", status_code=415
        )
    return mime


def _embed_and_store(sku: str, image_bytes: bytes, image_key: str) -> np.ndarray:
    """Embed the image, write the image + `.npy`, and index the vector."""
    vec = clip_model.embed_image(image_bytes)
    buf = io.BytesIO()
    np.save(buf, vec)
    put_bytes(_embedding_key(sku), buf.getvalue(), "application/octet-stream")
    index.add(sku, vec)
    return vec


def _row_to_product(row: dict, *, with_url: bool = True) -> Product:
    image_key = row["image_key"]
    return Product(
        sku=row["sku"],
        title=row["title"],
        price=float(row["price"]),
        currency=Currency(row["currency"]),
        category=Category(row["category"]),
        image_key=image_key,
        created_at=datetime.fromisoformat(row["created_at"]),
        image_url=get_inline_url(image_key) if with_url and image_key else None,
    )


def create_product(
    data: ProductCreate, image_bytes: bytes, filename: str
) -> Product:
    if metadata_store.get_row(data.sku) is not None:
        raise CatalogError(f"SKU '{data.sku}' already exists", status_code=409)
    if not image_bytes:
        raise CatalogError("A product image is required")
    content_type = _content_type(filename)

    image_key = _image_key(data.sku, filename)
    put_bytes(image_key, image_bytes, content_type)
    _embed_and_store(data.sku, image_bytes, image_key)

    created_at = datetime.now(UTC).isoformat()
    row = {
        "sku": data.sku,
        "title": data.title,
        "price": f"{data.price}",
        "currency": data.currency.value,
        "category": data.category.value,
        "image_key": image_key,
        "created_at": created_at,
    }
    metadata_store.upsert_row(row)
    logger.info("Product created: sku=%s image_key=%s", data.sku, image_key)
    return _row_to_product(row)


def get_product(sku: str) -> Product:
    row = metadata_store.get_row(sku)
    if row is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)
    return _row_to_product(row)


def list_products(category: Category | None = None) -> list[Product]:
    rows = metadata_store.all_rows()
    products = [_row_to_product(r) for r in rows]
    if category is not None:
        products = [p for p in products if p.category == category]
    products.sort(key=lambda p: p.created_at, reverse=True)
    return products


def update_product(
    sku: str,
    data: ProductUpdate,
    image_bytes: bytes | None = None,
    filename: str | None = None,
) -> Product:
    row = metadata_store.get_row(sku)
    if row is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)

    if data.title is not None:
        row["title"] = data.title
    if data.price is not None:
        row["price"] = f"{data.price}"
    if data.currency is not None:
        row["currency"] = data.currency.value
    if data.category is not None:
        row["category"] = data.category.value

    # Only re-embed when the image is actually replaced.
    if image_bytes:
        content_type = _content_type(filename or "image")
        # Remove the old image object(s) for this SKU, then write the new one.
        delete_prefix(f"{settings.catalog_images_prefix}{sku}/")
        image_key = _image_key(sku, filename or "image")
        put_bytes(image_key, image_bytes, content_type)
        row["image_key"] = image_key
        _embed_and_store(sku, image_bytes, image_key)

    metadata_store.upsert_row(row)
    logger.info("Product updated: sku=%s", sku)
    return _row_to_product(row)


def delete_product(sku: str) -> None:
    row = metadata_store.get_row(sku)
    if row is None:
        raise CatalogError(f"Product '{sku}' not found", status_code=404)
    # Scoped deletes: only this SKU's image folder + embedding.
    delete_prefix(f"{settings.catalog_images_prefix}{sku}/")
    delete_key(_embedding_key(sku))
    index.remove(sku)
    metadata_store.delete_row(sku)
    logger.info("Product deleted: sku=%s", sku)


def load_embedding(sku: str) -> np.ndarray | None:
    """Load a SKU's stored CLIP vector from B2 (for image-to-image 'find similar')."""
    data = get_bytes(_embedding_key(sku))
    if data is None:
        return None
    return np.load(io.BytesIO(data))


def get_stats() -> CatalogStats:
    rows = metadata_store.all_rows()
    embeddings = [
        o for o in _list_embeddings() if o["key"].endswith(".npy")
    ]
    catalog_bytes = _catalog_bytes()
    return CatalogStats(
        product_count=len(rows),
        embedding_count=len(embeddings),
        index_vector_count=index.vector_count(),
        catalog_bytes=catalog_bytes,
        catalog_bytes_human=humanize_bytes(catalog_bytes),
    )


def get_growth(days: int = 14) -> list[CatalogGrowthPoint]:
    from collections import defaultdict
    from datetime import timedelta

    rows = metadata_store.all_rows()
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        try:
            d = datetime.fromisoformat(r["created_at"]).date()
        except (ValueError, KeyError):
            continue
        if d >= cutoff:
            counts[d.isoformat()] += 1
    return [
        CatalogGrowthPoint(
            date=(cutoff + timedelta(days=i)).isoformat(),
            products=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]


def _list_embeddings() -> list[dict]:
    from app.repo import list_prefix

    return list_prefix(settings.catalog_embeddings_prefix)


def _catalog_bytes() -> int:
    from app.repo import list_prefix

    total = 0
    for prefix in (
        settings.catalog_images_prefix,
        settings.catalog_embeddings_prefix,
    ):
        total += sum(o["size"] for o in list_prefix(prefix))
    return total
