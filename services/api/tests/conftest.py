import hashlib
from datetime import UTC, datetime

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Catalog/search test doubles ------------------------------------------------
# The catalog, index, search and metadata services all talk to B2 through the
# repo layer and to CLIP through service.clip_model. These fixtures swap both out
# for deterministic in-memory doubles so the suite runs with NO network and NO
# model download — real CLIP is exercised by the seed script and the verify step.


class _FakeB2:
    """A tiny in-memory object store standing in for the B2 bucket."""

    def __init__(self):
        self.store: dict[str, bytes] = {}

    def put_bytes(self, key, data, content_type):
        self.store[key] = bytes(data)

    def get_bytes(self, key):
        return self.store.get(key)

    def object_exists(self, key):
        return key in self.store

    def list_prefix(self, prefix):
        return [
            {"key": k, "size": len(v), "last_modified": datetime.now(UTC)}
            for k, v in self.store.items()
            if k.startswith(prefix)
        ]

    def delete_key(self, key):
        self.store.pop(key, None)

    def delete_prefix(self, prefix):
        for k in [k for k in self.store if k.startswith(prefix)]:
            del self.store[k]

    def get_inline_url(self, key, expires_in=3600):
        return f"https://example.test/{key}"


def _fake_vector(seed_bytes: bytes) -> np.ndarray:
    """Deterministic L2-normalized 512-d vector derived from the input bytes."""
    seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:8], "big")
    vec = np.random.default_rng(seed).standard_normal(512).astype("float32")
    return vec / np.linalg.norm(vec)


@pytest.fixture
def fake_b2(monkeypatch):
    """Patch every repo B2 call across the service modules to an in-memory store."""
    import app.repo as repo
    from app.repo import catalog_store
    from app.service import catalog, index, metadata_store, search  # noqa: F401

    b2 = _FakeB2()

    # metadata_store uses get_bytes / put_bytes
    monkeypatch.setattr(metadata_store, "get_bytes", b2.get_bytes)
    monkeypatch.setattr(metadata_store, "put_bytes", b2.put_bytes)
    # index uses get_bytes / put_bytes / list_prefix
    monkeypatch.setattr(index, "get_bytes", b2.get_bytes)
    monkeypatch.setattr(index, "put_bytes", b2.put_bytes)
    monkeypatch.setattr(index, "list_prefix", b2.list_prefix)
    # catalog uses put_bytes / get_bytes / get_inline_url / delete_key / delete_prefix
    monkeypatch.setattr(catalog, "put_bytes", b2.put_bytes)
    monkeypatch.setattr(catalog, "get_bytes", b2.get_bytes)
    monkeypatch.setattr(catalog, "get_inline_url", b2.get_inline_url)
    monkeypatch.setattr(catalog, "delete_key", b2.delete_key)
    monkeypatch.setattr(catalog, "delete_prefix", b2.delete_prefix)
    # catalog + search import list_prefix / get_bytes lazily from app.repo
    monkeypatch.setattr(repo, "list_prefix", b2.list_prefix)
    monkeypatch.setattr(repo, "get_bytes", b2.get_bytes)
    monkeypatch.setattr(catalog_store, "get_bytes", b2.get_bytes)

    # Fresh in-memory FAISS state + metadata cache per test.
    index.reset_for_tests()
    metadata_store.invalidate_cache()
    yield b2
    index.reset_for_tests()
    metadata_store.invalidate_cache()


@pytest.fixture
def stub_embedder(monkeypatch):
    """Replace CLIP with deterministic fake vectors (no torch, no download)."""
    from app.service import clip_model

    monkeypatch.setattr(clip_model, "embed_image", lambda data: _fake_vector(bytes(data)))
    monkeypatch.setattr(
        clip_model, "embed_text", lambda text: _fake_vector(text.encode("utf-8"))
    )
    return _fake_vector


@pytest.fixture(autouse=True)
def clear_list_cache():
    """Clear the repo's bucket-listing cache before each test so cached
    listings never leak across tests (keeps the pagination tests hermetic)."""
    from app.repo import b2_client

    b2_client._invalidate_list_cache()
    yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the per-IP rate-limit counters before each test — otherwise the
    whole suite shares one client IP and accumulates hits across tests."""
    from app.runtime import ratelimit

    ratelimit._reset_state()
    yield


@pytest.fixture(autouse=True)
def reset_shared_module_state():
    """Reset the remaining shared module state (B2 connectivity cache and the
    in-process metrics counters) so absolute-value assertions can't become
    order-dependent across the suite."""
    from app.repo import b2_client
    from app.runtime import metrics

    b2_client._health_cache = None
    with metrics._lock:
        metrics._request_count.clear()
        metrics._request_duration_sum.clear()
        metrics._upload_count = 0
        metrics._upload_errors = 0
    yield


@pytest.fixture(autouse=True)
def isolate_download_counter(tmp_path, monkeypatch):
    """Redirect the persisted download counter to a temp file per test and
    reset the in-memory counter to 0. Keeps tests hermetic and prevents
    stray writes to services/api/data/."""
    from app.config import settings
    from app.repo import counter

    counter_path = tmp_path / "download_count.json"
    monkeypatch.setattr(settings, "download_count_file", str(counter_path))
    monkeypatch.setattr(counter, "_count", 0)
    yield
