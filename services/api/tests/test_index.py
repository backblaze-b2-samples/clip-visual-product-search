"""FAISS index manager tests — deterministic vectors, in-memory B2, no network."""

import numpy as np

from app.service import index


def _unit(seed: int) -> np.ndarray:
    v = np.random.default_rng(seed).standard_normal(512).astype("float32")
    return v / np.linalg.norm(v)


def test_add_search_returns_nearest(fake_b2):
    a, b, c = _unit(1), _unit(2), _unit(3)
    index.add("sku-a", a)
    index.add("sku-b", b)
    index.add("sku-c", c)

    hits = index.search(a, k=1)
    assert hits[0][0] == "sku-a"
    # Cosine similarity of a vector with itself is ~1.0.
    assert hits[0][1] > 0.999


def test_search_excludes_self(fake_b2):
    a, b = _unit(1), _unit(2)
    index.add("sku-a", a)
    index.add("sku-b", b)
    hits = index.search(a, k=5, exclude_sku="sku-a")
    assert all(sku != "sku-a" for sku, _ in hits)
    assert hits[0][0] == "sku-b"


def test_remove_drops_vector(fake_b2):
    index.add("sku-a", _unit(1))
    index.add("sku-b", _unit(2))
    assert index.vector_count() == 2
    index.remove("sku-a")
    assert index.vector_count() == 1
    hits = index.search(_unit(1), k=5)
    assert all(sku != "sku-a" for sku, _ in hits)


def test_add_same_sku_replaces_not_duplicates(fake_b2):
    index.add("sku-a", _unit(1))
    index.add("sku-a", _unit(9))
    assert index.vector_count() == 1


def test_rebuild_from_b2(fake_b2):
    from app.config import settings

    # Seed embeddings directly into the fake bucket.
    for i, sku in enumerate(["x", "y", "z"]):
        buf = _npy_bytes(_unit(i + 10))
        fake_b2.put_bytes(f"{settings.catalog_embeddings_prefix}{sku}.npy", buf, "application/octet-stream")
    index.reset_for_tests()
    count = index.rebuild_from_b2()
    assert count == 3
    assert index.vector_count() == 3


def test_persisted_index_reloads(fake_b2):
    index.add("sku-a", _unit(1))
    # Drop in-memory state; a subsequent search must reload from the fake bucket.
    index.reset_for_tests()
    hits = index.search(_unit(1), k=1)
    assert hits and hits[0][0] == "sku-a"


def _npy_bytes(vec: np.ndarray) -> bytes:
    import io

    buf = io.BytesIO()
    np.save(buf, vec)
    return buf.getvalue()
