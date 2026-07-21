"""Catalog CRUD tests with a stub embedder + in-memory B2 (no model, no network)."""

import pytest

from app.service import catalog
from app.service.catalog import CatalogError
from app.types import Category, Currency, ProductCreate, ProductUpdate

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"


def _create(sku="sku-1", title="Teal Trail Runner", category=Category.footwear):
    data = ProductCreate(
        sku=sku, title=title, price=89.0, currency=Currency.usd, category=category
    )
    return catalog.create_product(data, PNG_BYTES, f"{sku}.png")


def test_create_writes_image_embedding_and_metadata(fake_b2, stub_embedder):
    product = _create()
    assert product.sku == "sku-1"
    assert product.image_url  # presigned/public URL populated on read
    # Three parallel artifacts landed in B2: image, .npy, and metadata csv.
    assert any(k.endswith("sku-1.png") for k in fake_b2.store)
    assert "catalog/embeddings/sku-1.npy" in fake_b2.store
    assert "catalog/metadata.csv" in fake_b2.store


def test_create_duplicate_sku_conflicts(fake_b2, stub_embedder):
    _create()
    with pytest.raises(CatalogError) as exc:
        _create()
    assert exc.value.status_code == 409


def test_get_and_list(fake_b2, stub_embedder):
    _create(sku="a", category=Category.footwear)
    _create(sku="b", category=Category.apparel)
    assert catalog.get_product("a").sku == "a"
    assert len(catalog.list_products()) == 2
    footwear = catalog.list_products(category=Category.footwear)
    assert [p.sku for p in footwear] == ["a"]


def test_get_missing_raises_404(fake_b2, stub_embedder):
    with pytest.raises(CatalogError) as exc:
        catalog.get_product("nope")
    assert exc.value.status_code == 404


def test_update_metadata_only_does_not_reembed(fake_b2, stub_embedder):
    _create(sku="a")
    before = fake_b2.store["catalog/embeddings/a.npy"]
    updated = catalog.update_product("a", ProductUpdate(title="Renamed", price=42.0))
    assert updated.title == "Renamed"
    assert updated.price == 42.0
    # Embedding untouched when the image isn't replaced.
    assert fake_b2.store["catalog/embeddings/a.npy"] == before


def test_update_with_new_image_reembeds(fake_b2, stub_embedder):
    _create(sku="a")
    before = fake_b2.store["catalog/embeddings/a.npy"]
    new_image = b"\x89PNG\r\n\x1a\n" + b"different-bytes"
    catalog.update_product("a", ProductUpdate(), image_bytes=new_image, filename="a2.png")
    assert fake_b2.store["catalog/embeddings/a.npy"] != before


def test_delete_scopes_to_sku(fake_b2, stub_embedder):
    _create(sku="a")
    _create(sku="b")
    catalog.delete_product("a")
    with pytest.raises(CatalogError):
        catalog.get_product("a")
    # b's artifacts remain.
    assert catalog.get_product("b").sku == "b"
    assert "catalog/embeddings/b.npy" in fake_b2.store
    assert "catalog/embeddings/a.npy" not in fake_b2.store


def test_stats_reflect_catalog(fake_b2, stub_embedder):
    _create(sku="a")
    _create(sku="b")
    stats = catalog.get_stats()
    assert stats.product_count == 2
    assert stats.embedding_count == 2
    assert stats.index_vector_count == 2
    assert stats.catalog_bytes > 0


def test_unsupported_image_type_rejected(fake_b2, stub_embedder):
    data = ProductCreate(
        sku="x", title="x", price=1.0, currency=Currency.usd, category=Category.home
    )
    with pytest.raises(CatalogError) as exc:
        catalog.create_product(data, b"data", "x.txt")
    assert exc.value.status_code == 415
