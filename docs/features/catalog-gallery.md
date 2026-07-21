<!-- last_verified: 2026-07-21 -->
# Feature: Catalog Gallery

## Purpose
A sample-scoped, browsable view of the product catalog (the `catalog/images/` prefix in
B2) as product cards, with a category filter and an "Add product" entry point. It lives
alongside the [File Browser](file-browser.md), which browses the **whole** bucket.

## Used By
- UI: `/catalog` page (`components/catalog/catalog-gallery.tsx`)
- API: `GET /products`, `GET /products?category=...`

## Core Functions
- `apps/web/src/components/catalog/catalog-gallery.tsx` — product-card grid + category filter + Add CTA
- `apps/web/src/lib/queries.ts` — `useProducts(category?)`
- `services/api/app/runtime/products.py` — `GET /products`
- `services/api/app/service/catalog.py` — `list_products(category?)`

## Canonical Files
- Gallery component: `apps/web/src/components/catalog/catalog-gallery.tsx`

## Inputs
- `category`: optional Category filter (selector: All + the six categories)

## Outputs
- `GET /products` → `Product[]` (newest-first), each with a presigned/public `image_url`

## Flow
- Page loads → `useProducts()` fetches products (optionally filtered by category)
- Products render as image cards (image + title + category badge + price)
- Clicking a card opens the product detail page; "Add product" links to `/catalog/new`

## Edge Cases
- Empty catalog → empty state with "Add product" and a hint to run `scripts/seed-catalog.py`
- API error → inline error state with retry
- A product with no `image_url` → "No image" placeholder tile

## UX States
- Loading: skeleton tiles
- Empty: guidance to add a product / seed
- Loaded: filtered product grid

## Verification
- Test files: `services/api/tests/test_catalog.py` (`test_get_and_list`), `apps/web/e2e/product-search.spec.ts`
- Quick verify command: `pnpm test:api`
- Pass criteria: list + category filter tests green

## Related Docs
- [Product Catalog](product-catalog.md) · [File Browser](file-browser.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md) · [App Workflows](../app-workflows.md)
