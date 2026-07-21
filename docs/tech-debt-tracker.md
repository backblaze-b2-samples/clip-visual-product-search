# Tech debt

## 2026-07-21 — verify

Nitpicks surfaced by the 3-lens UX verification of the marquee cross-modal search
flow (`/search`). None block the goal; logged here for backlog, never looped on.

- **Header (all pages)** — the top-bar ⌘K widget reads "Search files or jump to…" and is visually the most prominent search affordance → a first-time user may click it before finding the marquee product search; it's honestly labeled "files" and the real search is reachable via the sidebar "Search" item and the dashboard "Search catalog" CTA (`.local/verify/A/01-landing.png`).
- **/catalog and /files (initial data load)** — content area renders blank for ~1–3s before the grid/tree paints, with no loading skeleton (unlike `/search`, which shows skeletons) → briefly reads as empty rather than loading (`.local/verify/A2/07-catalog.png` vs `.local/verify/A2/07b-catalog-waited.png`).
- **/search results grid** — result tiles show a blank grey area briefly while `loading="lazy"` images stream in from B2 (no per-image placeholder/blur); all images do paint after load (`.local/verify/B/03-search-results-text.png`).
- **/search error recovery** — the ErrorState "Retry" button resets the form to idle rather than re-running the failed query, so the user must re-enter/re-submit (`.local/verify/B/10-search-error.png`).
- **/search error toast** — the error toast lingers ~4s after the inline error has already been cleared/recovered (`.local/verify/B/10-search-error.png`).
- **/search empty states** — (a) there is no explicit pre-search empty state (before searching, just the form + empty space; the input placeholder guides); (b) the coded "No matches found" post-search empty state is effectively unreachable with the seeded 24-item catalog (FAISS always returns nearest neighbors) (`.local/verify/B2/01-idle-search.png`).
- **/search input (dev only)** — Next.js dev overlay flags 1 hydration mismatch: a `caret-color` style server/client mismatch on the `#search-query` input; dev-only, no functional impact, but a real console warning (`.local/verify/B2/03-results-text.png`).
- **/search in-progress feedback** — while searching, the app shows a distinct animating in-progress state ("Searching…" button + pulsing skeleton cards) but no stage text or determinate progress bar; adequate for the observed ~3s wait, could feel sparse on a slow first-ever cold model load (gate demoted this from friction → nitpick) (`.local/verify/B2/02-midwait-textsearch-COLD.png`).
