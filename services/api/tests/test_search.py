"""Cross-modal search tests with a stub embedder + in-memory B2."""

import io

import pytest

from app.service import catalog, search
from app.types import Category, Currency, ProductCreate, SearchMode

PNG = b"\x89PNG\r\n\x1a\n"


def _img(tag: str) -> bytes:
    return PNG + tag.encode("utf-8")


def _seed(sku, category=Category.footwear, image=None):
    data = ProductCreate(
        sku=sku, title=sku, price=10.0, currency=Currency.usd, category=category
    )
    return catalog.create_product(data, image or _img(sku), f"{sku}.png")


def test_search_text_returns_ranked_results(fake_b2, stub_embedder):
    for sku in ("a", "b", "c"):
        _seed(sku)
    resp = search.search_text("teal running shoe", k=2)
    assert resp.mode == SearchMode.text
    assert resp.query == "teal running shoe"
    assert 0 < resp.count <= 2
    # Scores are sorted descending.
    scores = [r.score for r in resp.results]
    assert scores == sorted(scores, reverse=True)


def test_search_image_finds_exact_match_first(fake_b2, stub_embedder):
    _seed("a", image=_img("a"))
    _seed("b", image=_img("b"))
    # Searching with a's exact image bytes ranks a first (cosine ~1.0).
    resp = search.search_image(_img("a"), k=2)
    assert resp.mode == SearchMode.image
    assert resp.results[0].product.sku == "a"
    assert resp.results[0].score > 0.999


def test_search_category_filter(fake_b2, stub_embedder):
    _seed("a", category=Category.footwear)
    _seed("b", category=Category.apparel)
    _seed("c", category=Category.apparel)
    resp = search.search_text("anything", k=10, category=Category.apparel)
    assert {r.product.sku for r in resp.results} <= {"b", "c"}
    assert all(r.product.category == Category.apparel for r in resp.results)


def test_category_filter_does_not_shrink_top_n(fake_b2, stub_embedder):
    """A category filter must not silently return fewer than the requested `k`.

    Regression for the post-filter shrink bug: with a fixed top-K retrieval
    budget, out-of-category nearest neighbours could consume the budget and
    leave < k in-category hits (e.g. "Top 4" + Footwear returned 2 of 4).
    Retrieval now widens to the whole index when a category is set, so a
    "Top N" + category returns exactly min(N, in-category count).
    """
    # 6 categories x 4 = 24 products, mirroring the seeded demo catalog.
    for cat in Category:
        for i in range(4):
            _seed(f"{cat.value.lower()}-{i}", category=cat)
    in_category = 4  # Footwear products present

    # k below the in-category count → exactly k, all in-category.
    resp = search.search_text("shoe", k=2, category=Category.footwear)
    assert resp.count == 2
    assert all(r.product.category == Category.footwear for r in resp.results)

    # k equal to the in-category count → all in-category items (not fewer).
    resp = search.search_text("shoe", k=in_category, category=Category.footwear)
    assert resp.count == in_category
    assert {r.product.sku for r in resp.results} == {f"footwear-{i}" for i in range(4)}
    assert all(r.product.category == Category.footwear for r in resp.results)

    # k above the in-category count → capped at the in-category count.
    resp = search.search_text("shoe", k=8, category=Category.footwear)
    assert resp.count == in_category
    assert all(r.product.category == Category.footwear for r in resp.results)

    # No category → a normal top-N over the whole index, unchanged.
    resp = search.search_text("shoe", k=4)
    assert resp.count == 4


def test_search_similar_excludes_self(fake_b2, stub_embedder):
    _seed("a", image=_img("a"))
    _seed("b", image=_img("b"))
    resp = search.search_similar("a", k=5)
    assert all(r.product.sku != "a" for r in resp.results)


def test_empty_text_query_raises(fake_b2, stub_embedder):
    from app.service.catalog import CatalogError

    with pytest.raises(CatalogError):
        search.search_text("   ", k=4)


@pytest.mark.asyncio
async def test_http_create_then_search_and_similar(client, fake_b2, stub_embedder):
    # Create a product via the multipart endpoint.
    resp = await client.post(
        "/products",
        data={
            "sku": "sku-teal-runner-01",
            "title": "Teal Trail Runner",
            "price": "89.00",
            "currency": "USD",
            "category": "Footwear",
        },
        files={"image": ("shoe.png", io.BytesIO(_img("shoe")), "image/png")},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["sku"] == "sku-teal-runner-01"

    # Text search returns a well-formed response.
    resp = await client.post("/search", data={"mode": "text", "query": "trail shoe", "k": "8"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "text"
    assert body["count"] >= 1

    # Image search with the exact bytes ranks the product first.
    resp = await client.post(
        "/search",
        data={"mode": "image", "k": "8"},
        files={"image": ("q.png", io.BytesIO(_img("shoe")), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["product"]["sku"] == "sku-teal-runner-01"

    # Find-similar (the run verb) responds without the product itself.
    resp = await client.post("/products/sku-teal-runner-01/similar")
    assert resp.status_code == 200
    assert all(r["product"]["sku"] != "sku-teal-runner-01" for r in resp.json()["results"])


@pytest.mark.asyncio
async def test_http_catalog_stats(client, fake_b2, stub_embedder):
    await client.post(
        "/products",
        data={
            "sku": "a",
            "title": "A",
            "price": "1.0",
            "currency": "USD",
            "category": "Home",
        },
        files={"image": ("a.png", io.BytesIO(_img("a")), "image/png")},
    )
    resp = await client.get("/catalog/stats")
    assert resp.status_code == 200
    assert resp.json()["product_count"] == 1
