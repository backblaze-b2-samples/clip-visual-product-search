<!-- last_verified: 2026-07-21 -->
# Feature: Cross-Modal Search

## Purpose
Find catalog products by a **typed description** (text→image) or an **uploaded photo**
(image→image), ranked by CLIP cosine similarity. This is the marquee feature.

## Used By
- UI: `/search` page (`components/search/search-form.tsx`, `components/search/results-grid.tsx`)
- API: `POST /search`
- Also: per-product "Find similar" via `POST /products/{sku}/similar` (see [Product Catalog](product-catalog.md))

## Core Functions
- `services/api/app/service/search.py` — `search_text()`, `search_image()`, `search_similar()`
- `services/api/app/service/clip_model.py` — `embed_text()`, `embed_image()` (shared 512-d space)
- `services/api/app/service/index.py` — `search(vec, k, exclude_sku)`
- `apps/web/src/lib/api-client.ts` — `search()`, `findSimilar()`

## Canonical Files
- Search orchestration: `services/api/app/service/search.py`
- Search route: `services/api/app/runtime/search.py`

## Inputs
- `mode`: `"text" | "image"` (form)
- `query`: string (text mode)
- `image`: file (image mode)
- `k`: int (top-K, clamped 1–48; UI offers 4/8/12/24)
- `category`: optional Category filter

## Outputs
- `POST /search` → `SearchResponse` (`mode`, `query`, `count`, `results: SearchResult[]`)
- `SearchResult` = `{ product, score }` where `score` is cosine similarity in [-1, 1]
- Each result product carries a presigned (or public) `image_url` for browser rendering

## Flow
- Client submits mode + query/image (+ k, category) as multipart to `POST /search`
- Backend embeds the query into CLIP's shared 512-d space (`embed_text` or `embed_image`)
- FAISS returns the nearest vectors; ids are mapped to SKUs and hydrated with metadata + image URL
- Optional category filter is applied **after** ranking (over-fetch so ~k remain)
- Results render as a product grid with a `% match` badge per hit

## Edge Cases
- Empty text query → 400 ("Enter a text query to search")
- Image mode with no file → 400
- Empty index (no products) → 200 with `count: 0` and an empty-state grid
- Index/metadata drift (a hit's SKU has no metadata row) → that hit is skipped, not a 500

## UX States
- Loading: skeleton result cards
- Empty (after a search): "No matches found" with guidance
- Error: inline error state with retry (toast on failure)

## Verification
- Test files: `services/api/tests/test_search.py`
- Required cases: text ranking, image exact-match first, category filter, empty-query 400, HTTP create→search→similar flow
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green. Tests use a stub embedder (no model download); real CLIP is exercised by the seed script.

## Related Docs
- [CLIP Embedding](clip-embedding.md) · [FAISS Index](faiss-index.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md) · [App Workflows](../app-workflows.md)
