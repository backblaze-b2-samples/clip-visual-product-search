<!-- last_verified: 2026-07-21 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the catalog and its CLIP/FAISS artifacts stored in B2.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /catalog/stats`, `GET /catalog/stats/growth`, `GET /products`

## Core Functions
- `apps/web/src/components/dashboard/catalog-stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/catalog-growth-chart.tsx` — products-added-per-day bar chart
- `apps/web/src/components/dashboard/recent-products-table.tsx` — newest products
- `apps/web/src/lib/api-client.ts` — `getCatalogStats()`, `getCatalogGrowth()`, `getProducts()`
- `services/api/app/runtime/index.py` — `GET /catalog/stats` + `/growth` handlers
- `services/api/app/service/catalog.py` — `get_stats()`, `get_growth()` business logic

## Canonical Files
- Stat cards: `apps/web/src/components/dashboard/catalog-stats-cards.tsx`
- Stats service logic: `services/api/app/service/catalog.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /catalog/stats` → `CatalogStats` (product_count, embedding_count, index_vector_count, catalog_bytes, catalog_bytes_human)
- `GET /catalog/stats/growth?days=14` → `CatalogGrowthPoint[]` (server-side aggregation from metadata `created_at`)
- `GET /products` → `Product[]` for the recent-products table (sorted newest-first)

## Flow
- Page loads → parallel API calls (catalog stats, growth, products)
- Stat cards display products, embeddings, index vectors, and catalog size
- Growth chart displays daily product-add counts for the last 14 days
- Recent products table lists the newest items with category, price, and date

## Edge Cases
- API unavailable → inline error states with retry
- Empty catalog → empty chart + table messages guiding the user to add a product / run the seed
- Large catalog → stats/list paginate through all objects using `ContinuationToken`

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No products yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_catalog.py` (`test_stats_reflect_catalog`), `services/api/tests/test_search.py` (`test_http_catalog_stats`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
