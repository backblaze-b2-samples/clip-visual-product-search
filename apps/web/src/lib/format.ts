import type { Currency } from "@clip-visual-product-search/shared";

/** Format a price with its currency symbol, falling back gracefully. */
export function formatPrice(price: number, currency: Currency): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(price);
  } catch {
    return `${price.toFixed(2)} ${currency}`;
  }
}

/** Cosine similarity (0..1 for normalized CLIP vectors) as a percentage. */
export function formatScore(score: number): string {
  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`;
}
