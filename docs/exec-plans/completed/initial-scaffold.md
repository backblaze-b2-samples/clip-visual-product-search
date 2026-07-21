# Build plan — `clip-visual-product-search`

Source of truth for the starter tree:
`.claude/scratch/vcsk-4b8e8077-9b4e-4190-96a1-4dadfe375e73/` (fresh clone of vibe-coding-starter-kit).

## 1. Purpose

`clip-visual-product-search` is a self-hosted **visual + cross-modal product search**
app for e-commerce catalogs. A shopper (or catalog owner) can find similar items by
**typing a description** (text→image) or **uploading a photo** (image→image). It embeds
the whole product catalog locally with **CLIP** (no managed vector service, no second
API key) and searches with a local **FAISS** index. Backblaze **B2** is the single
durable store for three parallel, catalog-scale artifact sets — product **images**,
per-SKU CLIP **embeddings** (`.npy`), and the FAISS **index** — all accessed over the
S3-compatible API with a custom user-agent and standard `B2_*` env vars. It's for
retail/marketplace engineers who want an OSS blueprint for catalog-scale visual search
where B2 is the storage layer and the model runs on their own hardware.

The story the sample tells: as a catalog grows to millions of images, B2 holds a 1:1
image↔embedding artifact store plus the index — a large, continuously refreshed dataset
that never leaves your bucket. The demo runs on a small seeded catalog but the code path
and README make the scale story explicit.

## 2. Architecture delta from vibe-coding-starter-kit

The starter is a Next.js 16 + FastAPI + shared-TS B2 file dashboard with a strict layered
API (`types → config → repo → service → runtime`, boto3 confined to `repo/`). We keep the
chassis and layering, swap the file-CRUD domain for a product-catalog + CLIP-search domain.

### KEEP (as-is or lightly rebranded)
- Monorepo shell: `pnpm-workspace.yaml`, root `package.json` scripts, `scripts/dev.sh`,
  `scripts/doctor.mjs`, `scripts/pick-port.mjs`, `.github/workflows/ci.yml`, `infra/railway/`.
- Whole `apps/web/src/components/ui/*` shadcn library (Select, RadioGroup, Form, Dialog,
  AlertDialog, DataTable, Chart, Progress, Dropzone deps, etc.) — reused by new views.
- Layout chrome: `components/layout/*` (app-sidebar, header, health-banner, command-palette,
  theme-provider), `app/layout.tsx`, `error.tsx`, `global-error.tsx`, `loading.tsx`,
  `not-found.tsx`, `globals.css`, `next-themes` dark mode.
- **Full-bucket explorer (NON-NEGOTIABLE KEEP):** `app/files/page.tsx` +
  `components/files/*` (file-browser, file-preview, file-metadata-panel, file-tree-row) +
  the by-key API routes (`GET /files`, presigned `download`/`preview`, `DELETE`) and
  `lib/file-tree.ts`. This browses the **entire** bucket (all prefixes) and stays.
- API chassis: layered structure, `main.py` middleware stack (CORS-last, rate-limit,
  request-timing/JSON-500, structured logging), `/health` (B2 connectivity),
  `/metrics` (Prometheus), `repo/counter.py` download counter, `repo/b2_client.py`
  connectivity + list cache + presigned URLs, `types/errors.py`, `types/formatting.py`,
  `config/settings.py` chassis, rate-limit + key-prefix confinement, `tests/test_structure.py`
  and the reliability/security test suite (adapted to new routes).
- `/design` design-system page + `components/design/*` (cheap, shows tokens; keep).
- `apps/web/src/lib`: `api-client.ts` (extend), `queries.ts` + `query-client.tsx`
  (TanStack Query), `refresh-context.tsx`, `utils.ts`, `app-config.ts` (rebrand).
- Settings shell: `app/settings/page.tsx`, `components/settings/settings-form.tsx`
  (the **form-UX exemplar** — Select for finite fields + FormDescription hints),
  `components/settings/danger-zone.tsx` (repurpose for admin "Rebuild index").

### TRIM (remove from starter)
- Generic file **upload** flow: `app/upload/page.tsx`, `components/upload/*`
  (dropzone/upload-form/upload-progress as a *generic* uploader), `POST /upload`
  generic route, `service/upload.py`, `runtime/upload.py`, `types/upload.py`,
  `tests/test_upload_*`. The catalog's write path is **Add Product** (image + metadata),
  not arbitrary file upload. (The reusable **dropzone** UI is copied into the product
  create/search image pickers; only the generic *page/flow* is trimmed.)
- **PDF** metadata path: drop `PyPDF2` and PDF branches in `service/metadata.py`; the
  catalog is images only. Keep image-dimension extraction (useful for product cards).
- `docs/features/file-upload.md`, `docs/features/metadata-extraction.md` (rewritten, see §5).
- `apps/web/e2e/upload.spec.ts` (replace with a product-search e2e stub).

### ADD (new for clip-visual-product-search)
- **CLIP embedder (service, local):** `services/api/app/service/clip_model.py` — lazy-loads
  CLIP once (thread-safe), **device auto-detect CUDA → MPS → CPU** (CPU default, never
  GPU-required), exposes `embed_image(bytes) -> np.ndarray` and `embed_text(str) -> np.ndarray`,
  both **L2-normalized 512-d** vectors. Model: **`open_clip_torch` ViT-B-32 with
  `pretrained="openai"`** (the exact OpenAI CLIP weights — vendor-faithful CLIP, but
  pip-installable and pin-friendly, unlike `git+openai/CLIP`; see §3 note). CLIP/torch
  imports are contained to this one module.
- **FAISS index manager (service):** `services/api/app/service/index.py` — wraps
  `faiss.IndexIDMap(faiss.IndexFlatIP(512))` (cosine via normalized IP), in-memory + a lock,
  int-id→SKU JSON map. Lazy load from B2 on first use; if `catalog/index/faiss.index` absent,
  rebuild from all `catalog/embeddings/*.npy`. `add(sku, vec)`, `remove(sku)` (via
  `remove_ids` on the IDMap), `search(vec, k)`, `rebuild_from_b2()`, `persist_to_b2()`
  (write-through after each mutation — demo scale; README notes IVF/HNSW + batched persist
  for production millions).
- **Catalog service:** `services/api/app/service/catalog.py` — product CRUD orchestration:
  create (validate → `embed_image` → write image to `catalog/images/<sku>/<filename>` +
  `.npy` to `catalog/embeddings/<sku>.npy` → `index.add` → persist → upsert metadata row),
  read, update (metadata-only; re-embed only if the image is replaced), delete (scoped B2
  deletes of the SKU's image+embedding → `index.remove` → persist → drop metadata row).
- **Search service:** `services/api/app/service/search.py` — `search_text(q, k, category?)`
  and `search_image(bytes, k, category?)`: embed query → `index.search` → map ids→SKUs →
  hydrate metadata + a presigned (or public) image URL per hit → ranked `SearchResult[]`.
- **Metadata store:** product metadata (sku, title, price, currency, category, image_key,
  created_at) persisted as a CSV at `catalog/metadata.csv` in B2 (stdlib `csv`, read-modify-write
  under a lock; no app DB — B2 stays the sole store, matching the starter's ethos). Small
  in-process cache invalidated on mutation.
- **New repo helpers** (`repo/b2_client.py` or a new `repo/catalog_store.py`, boto3 stays here):
  `put_bytes(key, data, content_type)`, `get_bytes(key)`, `list_prefix(prefix)`,
  `delete_key(key)` used by the catalog/index/metadata services. Presigned-URL helper reused.
- **New types:** `types/catalog.py` (`Product`, `ProductCreate`, `ProductUpdate`,
  `Category` enum, `CatalogStats`), `types/search.py` (`SearchResult`, `SearchResponse`,
  `SearchMode` enum). All boundary data stays Pydantic.
- **New runtime routes:** `runtime/products.py` (`POST /products`, `GET /products`,
  `GET /products/{sku}`, `PATCH /products/{sku}`, `DELETE /products/{sku}`,
  `POST /products/{sku}/similar` = the **run** verb), `runtime/search.py` (`POST /search`),
  and an admin `POST /index/rebuild` (wired to the Settings "Rebuild index" action).
- **Frontend routes/components:**
  - `/` dashboard — repurposed stats-cards (product count, embeddings, index vectors,
    catalog bytes), catalog-growth chart, recent-products table.
  - `/search` (**marquee**) — `components/search/search-form.tsx` (text input + image
    dropzone + **mode** segmented control + **top-K** Select + optional **category** Select)
    and `components/search/results-grid.tsx` streaming product images from B2 with score badges.
  - `/catalog` (**sample-specific asset explorer, scoped to `catalog/images/`**) —
    `components/catalog/catalog-gallery.tsx` product-card grid + "Add product" CTA.
    This is the sample-scoped explorer that lives ALONGSIDE the full-bucket `/files` explorer.
  - `/catalog/[sku]` — `components/catalog/product-detail.tsx` (read): image, metadata,
    embedding info, **Find similar** (run), Edit, Delete (AlertDialog confirm).
  - `/catalog/new` + `/catalog/[sku]/edit` — `components/catalog/product-form.tsx`
    (create/edit; see §Form UX).
  - Extend `lib/api-client.ts` + `lib/queries.ts` with product/search calls; add types to
    `packages/shared/src/types.ts`.
- **Seed script:** `scripts/seed-catalog.py` — populates a small demo catalog (~24 products
  across categories) using **Pillow-generated synthetic product tiles** (deterministic,
  keyless, nothing binary committed), embeds each with CLIP, writes images+`.npy`+index+CSV
  to B2. Documented as "replace with your real catalog". (Synthetic keeps a fresh-clone run
  reproducible + keyless; real imagery is a later screenshot-step concern.)
- `docs/exec-plans/completed/initial-scaffold.md` (this plan, moved on PASS).

## 3. B2 surface (S3-compatible only)

All via boto3 in `repo/` with `Config(user_agent_extra=...)`, signature v4. **No b2-native API.**
- `put_object` — product images (`catalog/images/<sku>/<filename>`), embeddings
  (`catalog/embeddings/<sku>.npy`), FAISS index (`catalog/index/faiss.index`),
  id-map (`catalog/index/id_map.json`), metadata (`catalog/metadata.csv`).
- `get_object` — stream images to results/detail, download `.npy` for reindex, load index+map.
- `list_objects_v2` — catalog gallery, reindex scan, dashboard stats, full-bucket explorer.
- `head_object` — image size/content-type for product cards.
- `delete_object` — scoped per-SKU image+embedding deletes on product delete.
- `generate_presigned_url` — stream/preview product & catalog images to the browser
  (default; public URL only when `B2_PUBLIC_URL_BASE` is set).
No b2-native calls anywhere. **Justification note:** `open_clip`/PyArrow-style clients are not
used for B2 — every B2 op is boto3-S3.

## 4. Key features (seed README + `docs/features/*.md`)

1. **Cross-modal search (text→image & image→image)** — the marquee. `deployment: local`.
2. **CLIP catalog embedding** — every product embedded to a 512-d `.npy` in B2, 1:1 with images.
3. **Local FAISS index on B2** — index built from B2 embeddings, persisted back to B2; no
   managed vector DB.
4. **Product catalog management** — full CRUD + "Find similar" over the primary entity.
5. **B2 as the catalog-scale artifact store** — images + embeddings + index in one bucket,
   S3 API, standard `B2_*` vars, custom UA.
6. **Sample-scoped catalog gallery + full-bucket explorer** — both asset views.

### External API provider
**None.** The only heavy workload (CLIP embedding + FAISS) runs **on-device**. Per
`api-provider-selection.md` this is the "point is on-device/local capability" case →
`deployment: local`, and the hard rule applies: **CPU default, auto-detect CUDA → MPS → CPU,
never GPU-required**. No second key; B2 credentials only.

| feature | provider | model | deployment | est. cost / demo run | key env var |
|---|---|---|---|---|---|
| cross-modal search & embedding | OpenAI CLIP (via `open_clip_torch`) | `ViT-B-32` `pretrained=openai` (512-d) | **local** | **$0** (first run downloads ~350 MB weights, cached; no API key) | — (none) |

**Vendor-fidelity note (justified):** the trending OSS is CLIP (openai/CLIP). We run the
*same model and the exact OpenAI weights* via `open_clip_torch` (`pretrained="openai"`)
rather than `pip install git+https://github.com/openai/CLIP.git`, because the git package is
unpinnable/fragile on fresh clones while `open_clip_torch` pins cleanly and is the maintained
CLIP runtime. This is CLIP, not a substitute — fidelity preserved. Record as a deviation.

**Genblaze:** the description's suggested stack does **not** mention Genblaze/`genblaze-*`/
`genblaze-s3` — so **no Genblaze routing**; there is no external AI provider to orchestrate.

### Primary-entity lifecycle (mandatory)
**Primary entity: `Product`** (a catalog item: SKU + image + metadata + CLIP embedding).
All lifecycle verbs are **built in the UI** (nothing omitted):
- **create** — `/catalog/new` form → embeds + indexes + writes artifacts to B2.
- **read** — `/catalog/[sku]` detail page.
- **edit** — `/catalog/[sku]/edit` (metadata; optional image replace → re-embed).
- **delete** — AlertDialog on detail/gallery → scoped B2 delete + index removal.
- **run** — **"Find similar"** on a product = image-to-image search from the product's
  stored embedding (`POST /products/{sku}/similar`), surfaced as a button on the detail page.
  (The global `/search` page is the marquee cross-modal entry; "Find similar" is the
  per-entity run verb.)
`omitted_ui_verbs`: **none** — build all five.

### Form UX conventions
- **Create/edit product form** (`product-form.tsx`), modeled on `settings-form.tsx`:
  - Finite fields → selectors, never free text: **Category** (`Select`: Apparel, Footwear,
    Accessories, Home, Electronics, Beauty), **Currency** (`Select`: USD, EUR, GBP).
  - Free-text/number fields: SKU (create-only, immutable on edit), Title, Price, Image (dropzone).
  - **Create-only safe-default hints** as `placeholder` / `FormDescription` (guidance, never
    an autofill button): SKU e.g. `sku-teal-runner-01`, Title e.g. `Teal Trail Runner`,
    Price e.g. `89.00`, Category default hint "Footwear". Edit form opens pre-filled from the
    real product (no default hints).
- **Search form:** **mode** (segmented control: Text / Image), **top-K** (`Select`: 4/8/12/24),
  optional **category filter** (`Select` incl. "All"); the query text / image are free inputs.

## 5. Doc transforms
- `README.md` — rewrite: title/description, the CLIP+FAISS+B2 architecture, the catalog-scale
  story, feature list (§4), quickstart (install deps incl. torch/faiss, fill `.env`,
  `python scripts/seed-catalog.py`, `pnpm dev`), env-var table with the standard `B2_*` names,
  "first run downloads CLIP weights (~350 MB, no key)" note, and the synthetic-seed / real-catalog note.
- `ARCHITECTURE.md` — replace file-CRUD component/flow descriptions with catalog/embed/index/
  search flows; keep layering + invariants sections; add the CLIP-model + FAISS-index components
  and note CLIP/torch confined to `service/clip_model.py`, boto3 to `repo/`.
- `PRODUCT.md`, `AGENTS.md` — rebrand + retarget to the product-search domain; keep invariants.
- `docs/features/`: **rewrite** `dashboard.md` (catalog metrics), `file-browser.md`
  (full-bucket explorer, note the sample-scoped catalog gallery too); **delete**
  `file-upload.md`, `metadata-extraction.md`; **add** `cross-modal-search.md`,
  `clip-embedding.md`, `faiss-index.md`, `product-catalog.md`, `catalog-gallery.md`
  (from `_template.md`).
- `docs/SECURITY.md`, `docs/RELIABILITY.md`, `docs/design-system.md`, `docs/app-workflows.md`,
  `docs/dev-workflows.md` — light edits for new routes/domain; keep structure.

## 6. Rename table

| kind | from | to |
|---|---|---|
| kebab / repo dir | `vibe-coding-starter-kit` | `clip-visual-product-search` |
| snake | `vibe_coding_starter_kit` | `clip_visual_product_search` |
| Title Case | `OSS Starter Kit` / `Vibe Coding Starter Kit` | `CLIP Visual Product Search` |
| npm workspace (web) | `@vibe-coding-starter-kit/web` | `@clip-visual-product-search/web` |
| npm workspace (shared) | `@vibe-coding-starter-kit/shared` | `@clip-visual-product-search/shared` |
| root pkg name | `vibe-coding-starter-kit` | `clip-visual-product-search` |
| `app-config.ts` APP_NAME | `OSS Starter Kit` | `CLIP Visual Product Search` |
| `app-config.ts` APP_DESCRIPTION | `File management dashboard powered by Backblaze B2` | `Visual & text product search over a Backblaze B2 catalog with CLIP + FAISS` |
| user_agent_extra | `b2ai-oss-start` | `b2ai-clip-visual-search` |
| UTM content tag | (starter) | `clip-visual-product-search` |
| CI/workflow + image tags | `vibe-coding-starter-kit` | `clip-visual-product-search` |

### Env-var standardization (parent CLAUDE.md standard #3; starter deviates)
Rename to the standard names and treat `B2_PUBLIC_URL_BASE` as **optional** (the app must NOT
hard-fail when it's unset — images stream via presigned URLs; public URL only when set):
- `B2_KEY_ID` → **`B2_APPLICATION_KEY_ID`**
- `B2_APPLICATION_KEY` (unchanged)
- `B2_BUCKET_NAME` (unchanged)
- add **`B2_REGION`** (e.g. `us-west-004`); derive endpoint `https://s3.${B2_REGION}.backblazeb2.com`
  when `B2_ENDPOINT` is unset (keep `B2_ENDPOINT` as an optional override).
- `b2_public_url` → **`B2_PUBLIC_URL_BASE`** (optional).
Update `.env.example`, `config/settings.py`, `scripts/doctor.mjs`, README env table accordingly.

## 7. Tests
Keep `tests/test_structure.py` (layering invariants — CLIP/torch only in `service/clip_model.py`,
boto3 only in `repo/`). Adapt health/rate-limit/key-prefix/error tests to new routes. Add
catalog + search + index tests that **inject a stub embedder** (deterministic fake vectors) so
the suite runs with **no model download and no network** — real CLIP is exercised by the seed
script + the later verify step. Replace the e2e upload spec with a product-search e2e stub.

## 8. Guardrails
- Parent CLAUDE.md standards: S3 API only, custom UA on every S3 client, standard `B2_*` names.
- Keep each file < 300 lines; preserve layering (no backward imports; boto3 only in `repo/`,
  CLIP/torch only in `service/clip_model.py`).
- Pin ML deps to a known-good window (avoid the unpinned false-green trap):
  `torch>=2.2,<3`, `open_clip_torch>=2.24,<3`, `faiss-cpu>=1.8,<2`, `numpy<2`, `Pillow>=11`.
- `.env` only for real secrets (gitignored); `.env.example` uses placeholders.
- Strip starter git history; init a fresh repo in the sample.
