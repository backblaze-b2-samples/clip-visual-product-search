<!-- last_verified: 2026-07-21 -->
# CLIP Visual Product Search

Self-hosted **visual + cross-modal product search** for e-commerce catalogs, with
**[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-clip-visual-product-search)**
as the single durable store for the whole catalog: product images, per-SKU CLIP
embeddings, and the FAISS index.

Shoppers (or catalog owners) find similar items two ways:

- **Type a description** → text-to-image search ("teal running shoe with a white sole")
- **Upload a photo** → image-to-image search ("find items that look like this")

The whole catalog is embedded locally with **CLIP** — no managed vector service, no
second API key — and searched with a local **FAISS** index. Every artifact is read and
written over B2's **S3-compatible API** with a custom user agent and the standard `B2_*`
env vars. The model runs on your own hardware (CPU by default; CUDA / Apple MPS auto-detected).

## Why this shape matters

As a catalog grows toward millions of images, B2 holds a **1:1 image↔embedding artifact
store plus the index** — a large, continuously refreshed dataset that never leaves your
bucket. The demo runs on a small seeded catalog (~24 products), but the code path and this
README make the scale story explicit: swap the seed script for your real catalog and the
same pipeline handles it. For production millions, the notes below point at IVF/HNSW
indexes and batched persistence.

## Features

- **Cross-modal search (text→image & image→image)** — the marquee flow at `/search`.
- **CLIP catalog embedding** — every product is embedded to a 512-d `.npy` in B2, 1:1 with its image.
- **Local FAISS index on B2** — the index is built from B2 embeddings and persisted back to B2; no managed vector DB.
- **Product catalog management** — full CRUD plus per-product **"Find similar"** over the primary entity.
- **B2 as the catalog-scale artifact store** — images + embeddings + index in one bucket, S3 API, standard `B2_*` vars, custom UA.
- **Two asset views** — a sample-scoped **catalog gallery** (`/catalog`, `catalog/images/`) alongside the **full-bucket explorer** (`/files`).

### The model (local, no API key)

| Feature | Model | Runtime | Deployment | Cost / run | Key |
|---|---|---|---|---|---|
| cross-modal search & embedding | OpenAI **CLIP `ViT-B-32`** (`pretrained="openai"`, 512-d) | `open_clip_torch` | **local** | **$0** | none |

> **First run downloads the CLIP weights (~350 MB), cached afterward — no API key required.**
> This is vendor-faithful CLIP: the *exact OpenAI weights* served through the maintained
> `open_clip_torch` runtime (which pins cleanly on fresh clones, unlike `git+openai/CLIP`).
> The only credentials the app needs are your B2 keys.

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts, TanStack Query
- Python 3.11+, FastAPI, boto3, Pydantic v2, **PyTorch + open_clip_torch + faiss-cpu**, Pillow
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free
**[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-clip-visual-product-search)**.

**1. Install dependencies**

```bash
pnpm install
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # includes torch + faiss-cpu; first CLIP use downloads ~350 MB
cd ../..
```

**2. Add your B2 credentials**

```bash
cp .env.example .env
```

Then head to the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-clip-visual-product-search) and fill in `.env`:

| Variable | Where it comes from |
|---|---|
| `B2_APPLICATION_KEY_ID` | Application key **keyID** (Read & Write) |
| `B2_APPLICATION_KEY` | Application key **applicationKey** *(shown once)* |
| `B2_BUCKET_NAME` | Your bucket's unique name |
| `B2_REGION` | Your bucket region, e.g. `us-west-004` — the S3 endpoint is derived from it |
| `B2_ENDPOINT` | *(optional)* explicit S3 endpoint override |
| `B2_PUBLIC_URL_BASE` | *(optional)* public base URL for a public bucket; images stream via presigned URLs when unset |

> Docs: [creating a bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-clip-visual-product-search) · [creating app keys](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-clip-visual-product-search).

**3. Seed a demo catalog**

```bash
python scripts/seed-catalog.py
```

This generates ~24 deterministic synthetic product tiles (nothing binary is committed;
a fresh clone reproduces the same catalog with no API key), embeds each with real CLIP,
and writes the images, `.npy` embeddings, FAISS index, and metadata CSV to your bucket.
**Replace `PRODUCTS` and the tile generator in `scripts/seed-catalog.py` with your real
catalog** when you're ready.

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000` (Swagger UI at `/docs`). Open
`/search`, type a description or drop a photo, and rank the catalog by CLIP similarity.

`pnpm dev` runs `pnpm doctor` first — a preflight that catches the common setup gotchas
(wrong Node/Python version, missing venv, missing or placeholder `.env`, busy ports).

## What lives in B2

All access is via boto3 over the S3-compatible API (signature v4, custom user agent
`b2ai-clip-visual-product-search`). **No b2-native API.**

```
catalog/images/<sku>/<filename>   product images        (put/get/list/delete)
catalog/embeddings/<sku>.npy      512-d CLIP vectors     (put/get/list/delete)
catalog/index/faiss.index         the FAISS index        (get/put)
catalog/index/id_map.json         int-id ↔ SKU map       (get/put)
catalog/metadata.csv              product metadata store (get/put) — no app DB
```

For a real millions-row catalog, front the metadata CSV with a database, swap
`IndexFlatIP` for `IVF`/`HNSW`, and batch the write-through persistence — see
[ARCHITECTURE.md](ARCHITECTURE.md).

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `python scripts/seed-catalog.py` | Populate a demo catalog in B2 |
| `pnpm build` | Build frontend |
| `pnpm lint` / `pnpm lint:api` | Lint frontend / backend |
| `pnpm test:web` / `pnpm test:api` | Unit tests (vitest / pytest) |
| `pnpm check:structure` | Verify layering + SDK-containment rules |
| `pnpm test:e2e` | Playwright e2e (`pnpm --filter @clip-visual-product-search/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (search, embedding, index, catalog, gallery) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |

## License

MIT License - see [LICENSE](LICENSE) for details.
