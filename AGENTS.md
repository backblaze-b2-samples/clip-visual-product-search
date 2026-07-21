<!-- last_verified: 2026-07-21 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
packages/shared/   Shared TypeScript types
scripts/           Dev helpers + seed-catalog.py (populates a demo catalog in B2)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

## 2. What This App Is

`clip-visual-product-search` is a self-hosted **visual + cross-modal product search** app
for e-commerce catalogs. The primary entity is a **`Product`** (SKU + image + metadata +
CLIP embedding). Backblaze B2 is the single durable store for three parallel artifact sets
— product images, per-SKU CLIP embeddings (`.npy`), and the FAISS index — all over the
S3-compatible API.

- **Search** (`/search`) is the marquee flow: text→image and image→image, ranked by CLIP
  cosine similarity over a FAISS index.
- **Catalog** (`/catalog`) is the sample-scoped product gallery + full CRUD over `Product`,
  plus per-product **"Find similar"** (the run verb).
- **Files** (`/files`) is the **full-bucket explorer** — keep it; it browses every prefix.
- **Dashboard** (`/`) shows catalog metrics (products, embeddings, index vectors, catalog
  size) + a growth chart. Rewire new aggregations through `runtime → service → repo` and
  expose them via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare
  `useEffect + fetch`.

**Keep as-is (shared scaffolding)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design
  tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new
  screens with these primitives; never edit generated `components/ui/` files directly.
- **Full-bucket File Explorer.** `/files`, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`, the by-key API routes, and `lib/file-tree.ts`.

## 3. Architectural Invariants

**Backend layering**: `types` → `config` → `repo` → `service` → `runtime`

- No backward imports across layers
- **No `boto3` outside `repo/`**
- **No `torch` / `open_clip` outside `service/clip_model.py`** — the CLIP runtime is
  contained exactly like boto3 so the app imports (and tests) never pull in torch
- No business logic in route handlers (`runtime/`)
- All external APIs/models wrapped behind `repo/` (storage) or `service/clip_model.py` (CLIP)
- All request/response data validated at the boundary (Pydantic models)
- No shared mutable state across layers

**Device policy**: CLIP device is auto-detected **CUDA → Apple MPS → CPU**, defaulting to
CPU. Never hard-require a GPU (no unconditional `.cuda()` / `device="cuda"`, no assert on a
missing GPU).

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in
`apps/web/src/lib/queries.ts`. New endpoints touch three files: `runtime/<router>.py`,
`lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements.
- No raw SDK/model calls outside their containment layer.
- Files stay under 300 lines.
- Tests added or updated for every behavior change.
- Docs updated in the same PR as code changes.
- Lint clean before merge; prefer boring, composable libraries.

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| No torch/open_clip outside service/clip_model.py | `tests/test_structure.py::test_clip_torch_only_in_clip_model` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web / dev:api # one side only
python scripts/seed-catalog.py   # populate a demo catalog in B2 (real CLIP)

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm test:web          # frontend unit tests (vitest)
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest — stubbed embedder, no model download)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

CI (`.github/workflows/ci.yml`) runs these gates on every PR and push to `main`. Backend
tests inject a **stub embedder** and an **in-memory B2**, so they run with no model
download and no network — real CLIP is exercised by `scripts/seed-catalog.py`.

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm test:web && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |

If documentation and implementation conflict, update docs in the same PR.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security / Reliability | [docs/SECURITY.md](docs/SECURITY.md) · [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans / Tech debt | [docs/exec-plans/](docs/exec-plans/) |

## 11. When Unsure

- Prefer boring, stable libraries; prefer small PRs.
- Add tests with every change; never bypass lint rules without explicit instruction.
- Ask before making destructive or irreversible changes.
