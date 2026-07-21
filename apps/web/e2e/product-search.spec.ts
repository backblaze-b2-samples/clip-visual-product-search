import { test, expect } from "@playwright/test";

// Smoke stub for the product-search flow. Full end-to-end coverage (real CLIP
// embedding + FAISS ranking) is exercised by the seed script and the backend
// suite; this checks the marquee UI wiring renders and accepts input without a
// running backend or B2 credentials.

test("search page renders the cross-modal search form", async ({ page }) => {
  await page.goto("/search");
  await expect(page.getByRole("heading", { name: /visual product search/i })).toBeVisible();
  // Mode segmented control is a selector, not free text.
  await expect(page.getByRole("tab", { name: /text/i })).toBeVisible();
  await expect(page.getByRole("tab", { name: /image/i })).toBeVisible();
  // Text query input is present in the default (text) mode.
  await page.getByLabel(/describe what you/i).fill("teal running shoe");
  await expect(page.getByRole("button", { name: /^search$/i })).toBeEnabled();
});

test("catalog page exposes the Add product action", async ({ page }) => {
  await page.goto("/catalog");
  await expect(page.getByRole("heading", { name: /^catalog$/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /add product/i }).first()).toBeVisible();
});
