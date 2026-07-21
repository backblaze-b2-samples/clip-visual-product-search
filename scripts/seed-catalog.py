#!/usr/bin/env python3
"""Seed a small demo catalog into Backblaze B2 with real CLIP embeddings.

Generates ~24 deterministic synthetic product tiles with Pillow (nothing binary
is committed to the repo, and a fresh clone reproduces the same catalog with no
API key), embeds each one with the real CLIP model, and writes the image, the
`.npy` embedding, the FAISS index, and the metadata CSV to your B2 bucket via the
app's own service layer.

This is a stand-in for your real catalog: replace `PRODUCTS` (and the tile
generator) with a loop over your actual product images + metadata. The first run
downloads the CLIP weights (~350 MB, cached afterwards, no key required).

Usage (from the repo root, with your B2 credentials in .env):

    python scripts/seed-catalog.py
"""

# --- OpenMP single-runtime guard: MUST run before torch/faiss load ---
# See services/api/main.py for the full rationale. This script reaches the CLIP
# (torch) and FAISS (faiss) runtimes through the service layer, and both bundle
# their own libomp.dylib; without this guard the first FAISS op aborts with
# "OMP: Error #15 ... already initialized" (SIGABRT / segfault). `setdefault` so
# an explicit operator override still wins. Import-free (os only).
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import colorsys
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# The seed script reuses the API's service layer (embedding + indexing + B2
# writes) so there's a single code path for "add a product".
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from PIL import Image, ImageDraw  # noqa: E402

from app.service import catalog  # noqa: E402
from app.service.catalog import CatalogError  # noqa: E402
from app.types import Category, Currency, ProductCreate  # noqa: E402

# (title, Category, Currency, price)
PRODUCTS: list[tuple[str, Category, Currency, float]] = [
    ("Teal Trail Runner", Category.footwear, Currency.usd, 89.0),
    ("Crimson Court Sneaker", Category.footwear, Currency.usd, 74.5),
    ("Sand Desert Boot", Category.footwear, Currency.gbp, 120.0),
    ("Slate Running Shoe", Category.footwear, Currency.eur, 95.0),
    ("Navy Puffer Jacket", Category.apparel, Currency.usd, 160.0),
    ("Olive Field Shirt", Category.apparel, Currency.usd, 48.0),
    ("Grey Zip Hoodie", Category.apparel, Currency.gbp, 55.0),
    ("Maroon Knit Sweater", Category.apparel, Currency.eur, 72.0),
    ("Tan Leather Belt", Category.accessories, Currency.usd, 35.0),
    ("Black Aviator Sunglasses", Category.accessories, Currency.usd, 65.0),
    ("Brown Canvas Cap", Category.accessories, Currency.gbp, 22.0),
    ("Silver Field Watch", Category.accessories, Currency.eur, 210.0),
    ("Terracotta Plant Pot", Category.home, Currency.usd, 28.0),
    ("Cream Ceramic Mug", Category.home, Currency.usd, 16.0),
    ("Walnut Cutting Board", Category.home, Currency.gbp, 42.0),
    ("Indigo Throw Pillow", Category.home, Currency.eur, 33.0),
    ("Graphite Wireless Earbuds", Category.electronics, Currency.usd, 129.0),
    ("Silver Laptop Stand", Category.electronics, Currency.usd, 49.0),
    ("Black Mechanical Keyboard", Category.electronics, Currency.gbp, 99.0),
    ("White Smart Speaker", Category.electronics, Currency.eur, 89.0),
    ("Rose Lip Balm", Category.beauty, Currency.usd, 9.0),
    ("Amber Facial Serum", Category.beauty, Currency.usd, 38.0),
    ("Mint Hand Cream", Category.beauty, Currency.gbp, 12.0),
    ("Coral Nail Polish", Category.beauty, Currency.eur, 11.0),
]

SHAPES = ("circle", "square", "triangle", "rounded")
SIZE = 512


def _slug(title: str) -> str:
    return "sku-" + title.lower().replace(" ", "-")


def _color(seed: int, sat: float, val: float) -> tuple[int, int, int]:
    hue = (seed * 0.61803398875) % 1.0  # golden-ratio spread for distinct hues
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return int(r * 255), int(g * 255), int(b * 255)


def _tile(idx: int, title: str) -> bytes:
    """Deterministic synthetic product tile: tinted bg + a colored shape + label."""
    bg = _color(idx, 0.18, 0.97)
    fg = _color(idx, 0.62, 0.72)
    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)
    m = 120
    box = (m, m, SIZE - m, SIZE - m)
    shape = SHAPES[idx % len(SHAPES)]
    if shape == "circle":
        draw.ellipse(box, fill=fg)
    elif shape == "square":
        draw.rectangle(box, fill=fg)
    elif shape == "rounded":
        draw.rounded_rectangle(box, radius=48, fill=fg)
    else:  # triangle
        draw.polygon([(SIZE // 2, m), (m, SIZE - m), (SIZE - m, SIZE - m)], fill=fg)
    draw.text((24, SIZE - 40), title, fill=(30, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    created, skipped = 0, 0
    for idx, (title, category, currency, price) in enumerate(PRODUCTS):
        sku = _slug(title)
        image_bytes = _tile(idx, title)
        data = ProductCreate(
            sku=sku, title=title, price=price, currency=currency, category=category
        )
        try:
            catalog.create_product(data, image_bytes, f"{sku}.png")
            created += 1
            print(f"  + {sku:32s} {category.value}")
        except CatalogError as e:
            if e.status_code == 409:
                skipped += 1
                print(f"  = {sku:32s} (exists, skipped)")
            else:
                print(f"  ! {sku}: {e.detail}")
                return 1
    print(f"\nDone. Created {created}, skipped {skipped}. FAISS index + metadata written to B2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
