"""In-memory FAISS index over the catalog's CLIP embeddings, persisted to B2.

The index is `IndexIDMap(IndexFlatIP(512))`: exact inner-product search over
L2-normalized vectors == exact cosine similarity. FAISS keys on int64 ids, so a
JSON id↔SKU map rides alongside it. The whole thing is the durable source of
truth on B2 (`catalog/index/faiss.index` + `catalog/index/id_map.json`) — on
first use we load it from the bucket, or rebuild it from every
`catalog/embeddings/*.npy` if the index object is absent.

Persistence is write-through after each mutation. That's the right trade at demo
scale; for catalog-scale millions the README notes swapping IndexFlatIP for
IVF/HNSW and batching the persist. Everything here is guarded by a single lock —
the FastAPI handlers run in Starlette's threadpool, so concurrent search/mutate
calls must not race the shared index.
"""

import json
import logging
import threading

import faiss
import numpy as np

from app.config import settings
from app.repo import get_bytes, list_prefix, put_bytes

logger = logging.getLogger(__name__)

# faiss-cpu bundles its own libomp.dylib; pin its OpenMP pool to one thread so it
# doesn't contend with torch's OpenMP runtime in the same process (see main.py's
# OMP guard). Belt-and-suspenders alongside the OMP_NUM_THREADS env cap.
faiss.omp_set_num_threads(1)

EMBED_DIM = 512

_lock = threading.RLock()
_index: "faiss.Index | None" = None
_id_to_sku: dict[int, str] = {}
_sku_to_id: dict[str, int] = {}
_next_id: int = 0
_loaded: bool = False


def _new_index() -> "faiss.Index":
    return faiss.IndexIDMap(faiss.IndexFlatIP(EMBED_DIM))


def _as_matrix(vec: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(vec, dtype="float32").reshape(1, EMBED_DIM)


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        index_bytes = get_bytes(settings.catalog_index_key)
        id_map_bytes = get_bytes(settings.catalog_id_map_key)
        if index_bytes and id_map_bytes:
            _load_from_bytes(index_bytes, id_map_bytes)
            logger.info("Loaded FAISS index from B2 (%d vectors)", len(_id_to_sku))
        else:
            logger.info("No persisted index found — rebuilding from B2 embeddings")
            _rebuild_locked()
        _loaded = True


def _load_from_bytes(index_bytes: bytes, id_map_bytes: bytes) -> None:
    global _index, _id_to_sku, _sku_to_id, _next_id
    _index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype="uint8"))
    payload = json.loads(id_map_bytes.decode("utf-8"))
    _id_to_sku = {int(k): v for k, v in payload.get("id_to_sku", {}).items()}
    _sku_to_id = {v: k for k, v in _id_to_sku.items()}
    _next_id = int(payload.get("next_id", (max(_id_to_sku) + 1) if _id_to_sku else 0))


def _rebuild_locked() -> int:
    """Rebuild the index from every embedding `.npy` in B2. Lock must be held."""
    global _index, _id_to_sku, _sku_to_id, _next_id
    _index = _new_index()
    _id_to_sku = {}
    _sku_to_id = {}
    _next_id = 0
    for obj in list_prefix(settings.catalog_embeddings_prefix):
        key = obj["key"]
        if not key.endswith(".npy"):
            continue
        sku = key[len(settings.catalog_embeddings_prefix):-len(".npy")]
        data = get_bytes(key)
        if data is None:
            continue
        vec = np.load(_bytes_io(data))
        _add_locked(sku, vec)
    _persist_locked()
    return len(_id_to_sku)


def _bytes_io(data: bytes):
    import io

    return io.BytesIO(data)


def _add_locked(sku: str, vec: np.ndarray) -> None:
    global _next_id
    if sku in _sku_to_id:
        _remove_locked(sku)
    new_id = _next_id
    _next_id += 1
    _index.add_with_ids(_as_matrix(vec), np.array([new_id], dtype="int64"))
    _id_to_sku[new_id] = sku
    _sku_to_id[sku] = new_id


def _remove_locked(sku: str) -> None:
    old_id = _sku_to_id.pop(sku, None)
    if old_id is None:
        return
    _id_to_sku.pop(old_id, None)
    _index.remove_ids(np.array([old_id], dtype="int64"))


def _persist_locked() -> None:
    index_bytes = faiss.serialize_index(_index).tobytes()
    put_bytes(settings.catalog_index_key, index_bytes, "application/octet-stream")
    payload = {
        "id_to_sku": {str(k): v for k, v in _id_to_sku.items()},
        "next_id": _next_id,
    }
    put_bytes(
        settings.catalog_id_map_key,
        json.dumps(payload).encode("utf-8"),
        "application/json",
    )


def add(sku: str, vec: np.ndarray) -> None:
    """Add (or replace) a SKU's vector and write the index through to B2."""
    _ensure_loaded()
    with _lock:
        _add_locked(sku, vec)
        _persist_locked()


def remove(sku: str) -> None:
    """Remove a SKU's vector (if present) and persist the index to B2."""
    _ensure_loaded()
    with _lock:
        _remove_locked(sku)
        _persist_locked()


def search(vec: np.ndarray, k: int, exclude_sku: str | None = None) -> list[tuple[str, float]]:
    """Return up to `k` (sku, cosine-score) hits ranked by similarity."""
    _ensure_loaded()
    with _lock:
        total = _index.ntotal
        if total == 0:
            return []
        # Over-fetch by one when excluding the query's own SKU.
        fetch = min(k + (1 if exclude_sku else 0), total)
        scores, ids = _index.search(_as_matrix(vec), fetch)
        hits: list[tuple[str, float]] = []
        for idx, score in zip(ids[0], scores[0], strict=False):
            if idx == -1:
                continue
            sku = _id_to_sku.get(int(idx))
            if sku is None or sku == exclude_sku:
                continue
            hits.append((sku, float(score)))
            if len(hits) >= k:
                break
        return hits


def rebuild_from_b2() -> int:
    """Force a full rebuild from B2 embeddings. Returns the vector count."""
    global _loaded
    with _lock:
        count = _rebuild_locked()
        _loaded = True
    return count


def vector_count() -> int:
    _ensure_loaded()
    with _lock:
        return _index.ntotal if _index is not None else 0


def reset_for_tests() -> None:
    """Drop in-memory state so tests start from a clean index."""
    global _index, _id_to_sku, _sku_to_id, _next_id, _loaded
    with _lock:
        _index = None
        _id_to_sku = {}
        _sku_to_id = {}
        _next_id = 0
        _loaded = False
