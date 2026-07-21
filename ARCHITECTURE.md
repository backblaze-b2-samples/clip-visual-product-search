<!-- last_verified: 2026-07-21 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with catalog metrics (products, embeddings, index vectors, catalog size) + growth chart
  - **Search** (`/search`) — cross-modal text→image and image→image product search
  - **Catalog** (`/catalog`) — sample-scoped product gallery + full CRUD over the `Product` entity
  - **Files** (`/files`) — full-bucket explorer (all prefixes) with preview/download/delete
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Product CRUD, cross-modal search, and index-rebuild REST API
  - Local **CLIP** embedder (`ViT-B-32`, OpenAI weights via `open_clip_torch`)
  - In-memory **FAISS** index (`IndexIDMap(IndexFlatIP(512))`), persisted to B2
  - B2 S3 integration via boto3; health, metrics, structured logging, rate limiting
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic (catalog, search, index, clip_model) — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` → `config` → `repo` → `service` → `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. **`torch` / `open_clip` only allowed in `service/clip_model.py`** — the ML runtime is
   contained exactly like boto3, so importing the app never drags in torch and tests stub
   the embedder
5. All boundary data uses Pydantic models (no raw dicts across layers)
6. Each file stays under 300 lines

Both containment rules are enforced by `tests/test_structure.py`.

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (Product, SearchResult, CatalogStats, ...)
    config/                Settings loaded from environment
    repo/                  B2 S3 access (b2_client.py, catalog_store.py, counter.py)
    service/               clip_model.py, index.py, catalog.py, search.py, metadata_store.py, files.py
    runtime/               FastAPI route handlers (products, search, index, files, health, metrics)
  tests/                   pytest tests (structural + integration, stubbed embedder)
```

## Key Components

- **CLIP embedder** (`service/clip_model.py`) — lazily loads `ViT-B-32` (OpenAI weights)
  once, thread-safe, device auto-detected **CUDA → Apple MPS → CPU** (CPU default, never
  GPU-required). Exposes `embed_image(bytes)` and `embed_text(str)`, both L2-normalized
  512-d vectors in CLIP's shared space. `torch`/`open_clip` imports are confined here.
- **FAISS index** (`service/index.py`) — `IndexIDMap(IndexFlatIP(512))` (exact cosine via
  normalized inner product), in-memory with a lock and an int-id↔SKU map. Lazy-loaded from
  B2; rebuilt from `catalog/embeddings/*.npy` if the index object is absent. Write-through
  persistence after each mutation.
- **Catalog service** (`service/catalog.py`) — product CRUD orchestration: create =
  validate → embed → write image + `.npy` + index + metadata; delete = scoped teardown.
- **Search service** (`service/search.py`) — `search_text` / `search_image` / `search_similar`;
  embeds the query, runs FAISS search, hydrates ranked `SearchResult`s.
- **Metadata store** (`service/metadata_store.py`) — product rows persisted as
  `catalog/metadata.csv` in B2 (no application database), read-modify-write under a lock.

## Boundary Invariants

- **No external SDK leakage**: `boto3` only in `app/repo/`; `torch`/`open_clip` only in
  `app/service/clip_model.py`. Every other layer goes through those interfaces.
- **No raw dicts at boundaries**: all data crossing layers uses typed Pydantic models.
- **No cross-layer mutable state**: intra-layer caches/counters (the listing cache, the
  download counter, the FAISS index, the metadata cache, rate-limit/metrics state) are
  module-local and guarded by a `threading.Lock`.
- **Validated inputs**: all HTTP inputs validated by FastAPI/Pydantic. File keys reject
  path-traversal patterns; product images are type-checked before embedding.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `:3000`, API `:8000`)
- **Railway** — two services from the same repo; see `infra/railway/README.md`. Give the
  API service enough memory/disk for the ~350 MB CLIP weights and warm it after deploy.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the **sole** data store:
  - `catalog/images/<sku>/<filename>` — product images
  - `catalog/embeddings/<sku>.npy` — 512-d CLIP vectors, 1:1 with images
  - `catalog/index/faiss.index` + `catalog/index/id_map.json` — the persisted index
  - `catalog/metadata.csv` — product metadata (no app DB)
- **Scale note**: at demo scale, an in-memory `IndexFlatIP` + write-through persistence +
  a CSV metadata store are the right trade. For a real millions-row catalog: swap in
  `IVF`/`HNSW`, batch the persist, and front the metadata with a database.

## External Services

- **Backblaze B2 S3 API** — image/embedding/index storage, retrieval, deletion, presigned URLs.
- **No external AI provider** — CLIP + FAISS run entirely on-device. The only credentials are B2 keys.

## Data Flows

- **Add product**: Browser → `POST /products` (multipart) → validate → `embed_image` →
  write image + `.npy` → `index.add` + persist → upsert metadata row → response.
- **Search (text)**: Browser → `POST /search` (mode=text) → `embed_text` → `index.search`
  → hydrate SKUs → ranked `SearchResult[]`.
- **Search (image)**: Browser → `POST /search` (mode=image, file) → `embed_image` → same.
- **Find similar (run verb)**: Browser → `POST /products/{sku}/similar` → load stored
  embedding → `index.search` (exclude self) → ranked results.
- **Delete**: Browser → `DELETE /products/{sku}` → scoped B2 deletes (image folder + `.npy`)
  → `index.remove` + persist → drop metadata row.
- **Rebuild index**: Settings → `POST /index/rebuild` → scan `catalog/embeddings/*.npy` →
  fresh index → persist.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend → API** — CORS-restricted; `CORSMiddleware` is registered LAST (outermost) so
  it wraps every response, including uncaught-exception 500s. A per-IP rate-limit middleware
  sits inner to CORS.
- **API → B2** — authenticated via application keys, signature v4, custom user agent.
- **Client → B2** — presigned URLs for inline image rendering (or public URLs when `B2_PUBLIC_URL_BASE` is set).

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format), `/health` endpoint (B2 connectivity check)

## Canonical Files

- Layered route handler: `services/api/app/runtime/products.py`
- Search orchestration: `services/api/app/service/search.py`
- CLIP embedder (ML containment): `services/api/app/service/clip_model.py`
- FAISS index manager: `services/api/app/service/index.py`
- B2 data access (repo layer): `services/api/app/repo/catalog_store.py`, `b2_client.py`
- Pydantic models: `services/api/app/types/` (`catalog.py`, `search.py`)
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Cross-Modal Search](docs/features/cross-modal-search.md)
- [CLIP Embedding](docs/features/clip-embedding.md)
- [FAISS Index](docs/features/faiss-index.md)
- [Product Catalog](docs/features/product-catalog.md)
- [Catalog Gallery](docs/features/catalog-gallery.md)
- [Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
