# Completed: Initial scaffold — clip-visual-product-search

Scaffolded from the vibe-coding-starter-kit chassis into a self-hosted visual +
cross-modal product search app. Summary of what landed:

## Kept (starter chassis)
- Monorepo shell, `pnpm dev`/doctor/pick-port, CI, Railway config
- Full shadcn UI kit + design tokens + `/design`
- Layout chrome (sidebar, header, health banner, command palette, theming)
- **Full-bucket File Explorer** (`/files` + by-key routes) — non-negotiable keep
- API chassis: layered `types → config → repo → service → runtime`, middleware stack,
  `/health`, `/metrics`, rate limiting, structured logging, structural tests

## Trimmed
- Generic upload flow (`/upload`, `service/upload.py`, `runtime/upload.py`, `types/upload.py`, upload components, `upload-file-types`)
- PDF metadata path + `service/metadata.py` (image catalog only)
- Starter feature docs `file-upload.md`, `metadata-extraction.md`; stale screenshots

## Added (the app)
- **CLIP embedder** `service/clip_model.py` — `ViT-B-32` OpenAI weights via `open_clip_torch`,
  device auto-detect CUDA → MPS → CPU, torch/open_clip contained here
- **FAISS index** `service/index.py` — `IndexIDMap(IndexFlatIP(512))`, persisted to B2
- **Catalog** `service/catalog.py` + `metadata_store.py` (CSV in B2, no app DB)
- **Search** `service/search.py` — text/image/similar
- **Repo** `repo/catalog_store.py` — boto3 byte helpers + inline presigned URLs
- **Routes** `runtime/products.py`, `runtime/search.py`, `runtime/index.py`
- **Types** `types/catalog.py`, `types/search.py`
- **Frontend**: `/search`, `/catalog`, `/catalog/[sku]`, `/catalog/new`, `/catalog/[sku]/edit`,
  catalog dashboard, product form (form-UX exemplar), Settings "Rebuild index"
- **Seed** `scripts/seed-catalog.py` — ~24 deterministic Pillow tiles, real CLIP embeds
- **Tests** — stubbed-embedder + in-memory-B2 catalog/search/index suites; torch containment test

## Standards
- Standard `B2_*` env vars (endpoint derived from `B2_REGION`); `B2_PUBLIC_URL_BASE` optional
- Custom UA `b2ai-clip-visual-product-search` on the S3 client; S3 API only (no b2-native)
- No hardcoded region in source
