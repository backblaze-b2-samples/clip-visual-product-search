<!-- last_verified: 2026-07-21 -->
# Feature: FAISS Index

## Purpose
Maintain an in-memory FAISS index over the catalog's CLIP embeddings, persisted to B2, so
similarity search needs no managed vector database.

## Used By
- Service: `catalog` (add/remove on product create/update/delete)
- Service: `search` (query the index)
- API: `POST /index/rebuild` (admin, wired to Settings → Index Maintenance)

## Core Functions
- `services/api/app/service/index.py` — `add()`, `remove()`, `search()`, `rebuild_from_b2()`, `vector_count()`, internal `_persist_locked()` / `_load_from_bytes()`
- `services/api/app/runtime/index.py` — `POST /index/rebuild`, `GET /catalog/stats`

## Canonical Files
- Index manager: `services/api/app/service/index.py`

## Design
- `IndexIDMap(IndexFlatIP(512))` — exact inner-product search over L2-normalized vectors
  == exact cosine similarity. Guarded by a single lock (handlers run in Starlette's threadpool).
- Int64 ids ↔ SKU map persisted alongside the index.
- Persisted to B2: `catalog/index/faiss.index` + `catalog/index/id_map.json`.

## Inputs / Outputs
- `add(sku, vec)` → write-through persist (replaces the SKU's vector if present)
- `remove(sku)` → `remove_ids` + persist
- `search(vec, k, exclude_sku?)` → `list[(sku, score)]`
- `rebuild_from_b2()` → int (vector count); rebuilds from every `catalog/embeddings/*.npy`

## Flow
- First use lazily loads the index + id map from B2; if the index object is absent, it
  rebuilds from all embedding `.npy` objects, then persists.
- Each mutation writes the whole index back to B2 (write-through).

## Edge Cases
- Missing persisted index → rebuild from embeddings
- Empty index → `search` returns `[]`
- Re-adding an existing SKU → replaces (never duplicates) its vector
- Persisted state reload after an in-memory reset → search transparently reloads from B2

## Scale Note
Demo-scale trade: `IndexFlatIP` + write-through persist. For millions of vectors, swap in
`IVF`/`HNSW` and batch the persistence — see [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Verification
- Test files: `services/api/tests/test_index.py`
- Required cases: add/search nearest, exclude-self, remove, replace-not-duplicate, rebuild-from-B2, persisted reload
- Quick verify command: `pnpm test:api`
- Pass criteria: all pytest tests green (real FAISS, in-memory B2, no network)

## Related Docs
- [CLIP Embedding](clip-embedding.md) · [Cross-Modal Search](cross-modal-search.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
