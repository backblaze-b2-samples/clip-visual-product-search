<!-- last_verified: 2026-07-21 -->
# Feature: CLIP Embedding

## Purpose
Embed product images and text queries into the same 512-d vector space so cosine
similarity ranks image↔image and text↔image alike. Runs locally, no API key.

## Used By
- Service: `catalog.create_product` / `update_product` (embed each product image)
- Service: `search.search_text` / `search_image` / `search_similar` (embed queries)
- Script: `scripts/seed-catalog.py`

## Core Functions
- `services/api/app/service/clip_model.py` — `embed_image(bytes) -> np.ndarray`, `embed_text(str) -> np.ndarray`, `_select_device()`, `_ensure_loaded()`
- `services/api/app/service/catalog.py` — `_embed_and_store()`

## Canonical Files
- The **only** place `torch` / `open_clip` are imported: `services/api/app/service/clip_model.py`

## Model
- **OpenAI CLIP `ViT-B-32`**, `pretrained="openai"` — the exact OpenAI weights served via
  the maintained `open_clip_torch` runtime (pins cleanly on fresh clones, unlike
  `git+openai/CLIP`). Output: **L2-normalized 512-d float32** vectors.

## Inputs
- `embed_image`: raw image bytes (JPEG/PNG/WebP/GIF)
- `embed_text`: a query string

## Outputs
- A `numpy.ndarray` of shape `(512,)`, L2-normalized (so inner product == cosine similarity)
- Side effect (first call): downloads the CLIP weights (~350 MB), cached thereafter

## Flow
- Model is lazily loaded once, thread-safely (double-checked lock)
- **Device auto-detect: CUDA → Apple MPS → CPU**, defaulting to CPU — never GPU-required
- `embed_image`: preprocess → `encode_image` → normalize; `embed_text`: tokenize → `encode_text` → normalize
- Inference only (`torch.set_grad_enabled(False)`)

## Edge Cases
- No GPU present → CPU path (default), no error
- A library without MPS support would fall back CUDA → CPU (documented policy)
- Corrupt/non-image bytes → Pillow raises; the caller surfaces a 4xx via `CatalogError`

## Verification
- Test files: `services/api/tests/test_structure.py` (`test_clip_torch_only_in_clip_model`),
  `services/api/tests/test_catalog.py`, `services/api/tests/test_search.py` (stub embedder)
- Real-model exercise: `python scripts/seed-catalog.py` (downloads weights, embeds ~24 products)
- Quick verify command: `pnpm check:structure && pnpm test:api`
- Pass criteria: containment test green (torch only in `clip_model.py`), suite green with no model download

## Related Docs
- [Cross-Modal Search](cross-modal-search.md) · [FAISS Index](faiss-index.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
