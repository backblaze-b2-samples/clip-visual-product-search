"""Product metadata persisted as a single CSV in B2 — no application database.

B2 stays the sole store (matching the starter's ethos): product rows live in
`catalog/metadata.csv`, read-modify-written under a process lock with a small
in-process cache invalidated on every mutation. Fine for the demo's catalog
scale; a real millions-row catalog would front this with a proper DB, which the
README calls out.
"""

import csv
import io
import logging
import threading

from app.config import settings
from app.repo import get_bytes, put_bytes

logger = logging.getLogger(__name__)

FIELDS = ["sku", "title", "price", "currency", "category", "image_key", "created_at"]

_lock = threading.Lock()
_cache: list[dict] | None = None


def _load_rows() -> list[dict]:
    """Return all rows (cached). Caller holds the lock."""
    global _cache
    if _cache is not None:
        return _cache
    data = get_bytes(settings.catalog_metadata_key)
    if not data:
        _cache = []
        return _cache
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    _cache = [dict(row) for row in reader]
    return _cache


def _write_rows(rows: list[dict]) -> None:
    """Persist all rows to B2 and refresh the cache. Caller holds the lock."""
    global _cache
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in FIELDS})
    put_bytes(
        settings.catalog_metadata_key,
        buf.getvalue().encode("utf-8"),
        "text/csv",
    )
    _cache = rows


def all_rows() -> list[dict]:
    with _lock:
        return list(_load_rows())


def get_row(sku: str) -> dict | None:
    with _lock:
        for row in _load_rows():
            if row.get("sku") == sku:
                return dict(row)
    return None


def upsert_row(row: dict) -> None:
    with _lock:
        rows = list(_load_rows())
        for i, existing in enumerate(rows):
            if existing.get("sku") == row["sku"]:
                rows[i] = row
                break
        else:
            rows.append(row)
        _write_rows(rows)


def delete_row(sku: str) -> bool:
    with _lock:
        rows = list(_load_rows())
        kept = [r for r in rows if r.get("sku") != sku]
        if len(kept) == len(rows):
            return False
        _write_rows(kept)
        return True


def count() -> int:
    with _lock:
        return len(_load_rows())


def invalidate_cache() -> None:
    global _cache
    with _lock:
        _cache = None
