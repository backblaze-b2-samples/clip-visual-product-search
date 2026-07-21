"""Cross-modal search: text→image and image→image over the FAISS index.

Embed the query into CLIP's shared 512-d space (text or image, same space),
run an exact cosine-similarity search on the FAISS index, then hydrate each hit
into a `SearchResult` (product metadata + a presigned image URL + score).

The optional category filter is applied after ranking so it never distorts
scores. So that a category can't silently shrink the requested count, the
retrieval budget widens to the whole (exact, tiny) index when a category is set
— see `_fetch_k` — guaranteeing "Top N" + a category returns
min(N, in-category count) rather than fewer.
"""

import logging

import numpy as np

from app.service import catalog, clip_model, index
from app.service.catalog import CatalogError
from app.types import Category, Product, SearchMode, SearchResponse, SearchResult

logger = logging.getLogger(__name__)


def _hydrate(hits: list[tuple[str, float]], category: Category | None, k: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for sku, score in hits:
        try:
            product: Product = catalog.get_product(sku)
        except CatalogError:
            # Index/metadata drift — skip stale ids rather than 500.
            logger.warning("Search hit sku=%s missing from metadata; skipping", sku)
            continue
        if category is not None and product.category != category:
            continue
        results.append(SearchResult(product=product, score=score))
        if len(results) >= k:
            break
    return results


def _fetch_k(k: int, category: Category | None) -> int:
    """Retrieval budget for the FAISS search.

    No category → retrieve exactly `k` (a normal top-N over the whole index).

    With a category the filter is a POST-filter applied after ranking, so a
    fixed top-K budget can be exhausted by out-of-category neighbours and leave
    fewer than `k` in-category hits even when more exist in that category.
    Retrieve the whole (exact, tiny `IndexFlatIP`) index instead so every
    in-category vector is a candidate; `_hydrate` then filters to the category
    and truncates to `k`, guaranteeing "Top N" + category returns
    min(N, in-category count).

    Scanning the full index is trivial at demo scale (~dozens of vectors). For a
    millions-row catalog the scale-appropriate approach is a pre-filtered /
    per-category index (e.g. an IDSelector on the flat index, or IVF/HNSW — see
    index.py), not a full scan.
    """
    if category is None:
        return k
    return index.vector_count()


def search_text(query: str, k: int = 12, category: Category | None = None) -> SearchResponse:
    if not query or not query.strip():
        raise CatalogError("Enter a text query to search")
    vec = clip_model.embed_text(query.strip())
    hits = index.search(vec, _fetch_k(k, category))
    results = _hydrate(hits, category, k)
    return SearchResponse(mode=SearchMode.text, query=query.strip(), count=len(results), results=results)


def search_image(image_bytes: bytes, k: int = 12, category: Category | None = None) -> SearchResponse:
    if not image_bytes:
        raise CatalogError("Upload an image to search")
    vec = clip_model.embed_image(image_bytes)
    hits = index.search(vec, _fetch_k(k, category))
    results = _hydrate(hits, category, k)
    return SearchResponse(mode=SearchMode.image, query=None, count=len(results), results=results)


def search_similar(sku: str, k: int = 12, category: Category | None = None) -> SearchResponse:
    """Image→image search seeded by a stored product's own CLIP embedding."""
    # Ensure the product exists (404s cleanly if not).
    catalog.get_product(sku)
    vec = _load_or_reembed(sku)
    hits = index.search(vec, _fetch_k(k, category), exclude_sku=sku)
    results = _hydrate(hits, category, k)
    return SearchResponse(mode=SearchMode.image, query=sku, count=len(results), results=results)


def _load_or_reembed(sku: str) -> np.ndarray:
    vec = catalog.load_embedding(sku)
    if vec is not None:
        return vec
    # Embedding artifact missing — fall back to re-embedding from the stored image.
    from app.repo import get_bytes

    product = catalog.get_product(sku)
    image_bytes = get_bytes(product.image_key)
    if not image_bytes:
        raise CatalogError(f"No embedding or image found for '{sku}'", status_code=404)
    return clip_model.embed_image(image_bytes)
