<!-- last_verified: 2026-07-21 -->
# App Workflows

User journeys inside the application.

## Search the Catalog (marquee)

- User navigates to `/search`
- Chooses a **mode** (segmented control): **Text** or **Image**
- **Text mode**: types a description (e.g. "teal running shoe with a white sole")
- **Image mode**: drops or selects a reference photo
- Optionally sets **Top-K** (4/8/12/24) and a **Category** filter
- Submits → the query is embedded with CLIP, searched against the FAISS index, and results
  render as a product grid with a **% match** badge per hit, ranked by cosine similarity
- Clicking a result opens its product detail page
- See: [Cross-Modal Search](features/cross-modal-search.md)

## Browse and Manage the Catalog

- User navigates to `/catalog`
- Products load as a card grid (image + title + category + price), optionally filtered by category
- **Add product** (`/catalog/new`): SKU + title + price + currency (select) + category
  (select) + image (dropzone). On save the image is embedded, indexed, and written to B2
- **Product detail** (`/catalog/[sku]`): image, metadata, embedding location, and actions
- **Find similar** (run verb): image-to-image search seeded by the product's stored embedding
- **Edit** (`/catalog/[sku]/edit`): update metadata; replacing the image re-embeds and re-indexes
- **Delete**: AlertDialog confirm → scoped B2 delete (image + `.npy`) + index removal + metadata drop
- See: [Product Catalog](features/product-catalog.md), [Catalog Gallery](features/catalog-gallery.md)

## View Dashboard

- User navigates to `/` (home)
- Stat cards show: products, CLIP embeddings, index vectors, catalog size
- Catalog growth chart shows products added per day (last 14 days)
- Recent products table lists the newest items with category, price, and date
- Empty state guides the user to add a product or run the seed script
- See: [Dashboard](features/dashboard.md)

## Browse the Whole Bucket

- User navigates to `/files`
- The full-bucket explorer lists **every** object across all prefixes (images, embeddings,
  index, metadata) in a tree with preview / download / delete
- This is the raw B2 view that lives alongside the sample-scoped `/catalog` gallery
- See: [File Browser](features/file-browser.md)

## Rebuild the Search Index (admin)

- User navigates to `/settings`
- Under **Index Maintenance**, clicks **Rebuild index** and confirms
- The backend re-reads every `catalog/embeddings/*.npy` object and rewrites the FAISS index
  + id map to B2 (non-destructive)
- See: [FAISS Index](features/faiss-index.md)
