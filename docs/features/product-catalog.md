<!-- last_verified: 2026-07-21 -->
# Feature: Product Catalog

## Purpose
Full lifecycle management of the primary entity, `Product` (SKU + image + metadata + CLIP
embedding): create, read, edit, delete, and the "Find similar" run verb.

## Used By
- UI: `/catalog/new`, `/catalog/[sku]`, `/catalog/[sku]/edit` (`components/catalog/product-form.tsx`, `product-detail.tsx`)
- API: `POST /products`, `GET /products/{sku}`, `PATCH /products/{sku}`, `DELETE /products/{sku}`, `POST /products/{sku}/similar`

## Core Functions
- `services/api/app/service/catalog.py` — `create_product`, `get_product`, `list_products`, `update_product`, `delete_product`, `load_embedding`
- `services/api/app/service/metadata_store.py` — CSV metadata store (`catalog/metadata.csv`)
- `services/api/app/runtime/products.py` — HTTP handlers
- `apps/web/src/lib/api-client.ts` / `queries.ts` — product calls + hooks

## Canonical Files
- Catalog orchestration: `services/api/app/service/catalog.py`
- Create/edit form (form-UX exemplar): `apps/web/src/components/catalog/product-form.tsx`

## Inputs
- Create (multipart): `sku`, `title`, `price`, `currency` (select), `category` (select), `image` (dropzone, required)
- Edit (multipart): metadata fields (optional) + optional replacement `image`
- SKU is immutable on edit

## Outputs
- `Product` (`sku`, `title`, `price`, `currency`, `category`, `image_key`, `created_at`, `image_url`)
- Create side effects: writes `catalog/images/<sku>/<file>`, `catalog/embeddings/<sku>.npy`,
  updates the FAISS index, appends a `catalog/metadata.csv` row
- Delete side effects: scoped deletes of the SKU's image folder + embedding, index removal, metadata row drop
- `POST /products/{sku}/similar` → `SearchResponse` (image-to-image from the stored embedding)

## Form UX
- Finite fields are **selectors**, never free text: **Category** (Apparel/Footwear/Accessories/Home/Electronics/Beauty), **Currency** (USD/EUR/GBP)
- Create-only **safe-default hints** as placeholders/descriptions (never an autofill button):
  SKU `sku-teal-runner-01`, Title `Teal Trail Runner`, Price `89.00`, Category hint "Footwear"
- Edit form opens pre-filled from the real product (no hints); replacing the image re-embeds + re-indexes

## Flow
- Create: validate → `embed_image` → write image + `.npy` → `index.add` + persist → upsert metadata row
- Read: metadata row → `Product` + presigned image URL
- Update: patch metadata; if the image is replaced, delete old image, write new, re-embed, re-index
- Delete: scoped B2 deletes + `index.remove` + metadata drop (AlertDialog confirm in the UI)

## Edge Cases
- Duplicate SKU on create → 409
- Missing product on read/update/delete → 404
- Unsupported image type → 415
- Metadata-only edit → embedding untouched (no re-embed)

## Verification
- Test files: `services/api/tests/test_catalog.py`, `services/api/tests/test_search.py`
- Required cases: create writes 3 artifacts, duplicate 409, get/list + category filter, metadata-only vs image-replace update, scoped delete, 415
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm test:web && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all tests green, no lint violations

## Related Docs
- [Catalog Gallery](catalog-gallery.md) · [Cross-Modal Search](cross-modal-search.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md) · [App Workflows](../app-workflows.md)
