import type {
  CatalogGrowthPoint,
  CatalogStats,
  Category,
  DailyUploadCount,
  FileMetadata,
  Product,
  SearchMode,
  SearchResponse,
  UploadStats,
} from "@clip-visual-product-search/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

/**
 * Build the right status-0 ApiError for a thrown fetch().
 *
 * fetch() rejects with a TypeError for genuinely-offline/DNS failures AND for
 * responses the browser refused to expose — most notably a cross-origin 500
 * that shipped without `Access-Control-Allow-Origin`. We can't tell those apart
 * from the error object, but `navigator.onLine === false` reliably means the
 * device has no connectivity. Anything else reached the network, so the most
 * likely cause is the server erroring with a CORS-blocked response — point the
 * developer at the API logs instead of blaming their connection.
 */
function networkError(): ApiError {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return new ApiError("You appear to be offline — check your connection", 0);
  }
  return new ApiError(
    "Couldn't reach the API, or the server returned an error the browser blocked (CORS). Check the API logs.",
    0,
  );
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw networkError();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

function isEndpointUnavailable(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 404 &&
    (error.message === "Not Found" || error.message === "API error: 404")
  );
}

async function apiFetchWithLegacyFallback<T>(
  path: string,
  legacyPath: () => string,
  init?: RequestInit
): Promise<T> {
  try {
    return await apiFetch<T>(path, init);
  } catch (error) {
    if (isEndpointUnavailable(error)) {
      return apiFetch<T>(legacyPath(), init);
    }
    throw error;
  }
}

function fileKeyQuery(key: string): string {
  if (key.length === 0) {
    throw new ApiError("File key is required", 400);
  }
  return new URLSearchParams({ key }).toString();
}

function legacyFileKeyPath(
  key: string,
  options: { blockRouteCollisions?: boolean } = {}
): string {
  if (!isLegacyPathFallbackSafe(key, options)) {
    throw new ApiError("Current API version required for this file key", 404);
  }
  return encodeURIComponent(key);
}

function isLegacyPathFallbackSafe(
  key: string,
  { blockRouteCollisions = false }: { blockRouteCollisions?: boolean } = {}
): boolean {
  if (/(\.\.\/|\/\.\.|\\|%2e%2e|%00|\x00)/i.test(key)) return false;
  if (!blockRouteCollisions) return true;

  const lowerKey = key.toLowerCase();
  if (lowerKey === "stats" || lowerKey === "stats/activity") return false;
  if (lowerKey.endsWith("/download") || lowerKey.endsWith("/preview")) return false;
  return true;
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetchWithLegacyFallback<FileMetadata>(
    `/files-by-key/metadata?${fileKeyQuery(key)}`,
    () => `/files/${legacyFileKeyPath(key, { blockRouteCollisions: true })}`
  );
}

export async function getDownloadUrl(key: string) {
  return apiFetchWithLegacyFallback<{ url: string }>(
    `/files-by-key/download?${fileKeyQuery(key)}`,
    () => `/files/${legacyFileKeyPath(key)}/download`
  );
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetchWithLegacyFallback<{ url: string }>(
    `/files-by-key/preview?${fileKeyQuery(key)}`,
    () => `/files/${legacyFileKeyPath(key)}/preview`
  );
}

export async function deleteFile(key: string) {
  return apiFetchWithLegacyFallback<{ deleted: boolean; key: string }>(
    `/files-by-key?${fileKeyQuery(key)}`,
    () => `/files/${legacyFileKeyPath(key)}`,
    {
      method: "DELETE",
    }
  );
}

// --- Product catalog + CLIP search ---

export async function getProducts(category?: Category) {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch<Product[]>(`/products${qs}`);
}

export async function getProduct(sku: string) {
  return apiFetch<Product>(`/products/${encodeURIComponent(sku)}`);
}

export interface ProductFormValues {
  sku: string;
  title: string;
  price: number;
  currency: string;
  category: string;
  image?: File | null;
}

export async function createProduct(values: ProductFormValues) {
  const form = new FormData();
  form.append("sku", values.sku);
  form.append("title", values.title);
  form.append("price", String(values.price));
  form.append("currency", values.currency);
  form.append("category", values.category);
  if (values.image) form.append("image", values.image);
  return apiFetch<Product>("/products", { method: "POST", body: form });
}

export async function updateProduct(
  sku: string,
  values: Partial<Omit<ProductFormValues, "sku">>,
) {
  const form = new FormData();
  if (values.title !== undefined) form.append("title", values.title);
  if (values.price !== undefined) form.append("price", String(values.price));
  if (values.currency) form.append("currency", values.currency);
  if (values.category) form.append("category", values.category);
  if (values.image) form.append("image", values.image);
  return apiFetch<Product>(`/products/${encodeURIComponent(sku)}`, {
    method: "PATCH",
    body: form,
  });
}

export async function deleteProduct(sku: string) {
  return apiFetch<{ deleted: boolean; sku: string }>(
    `/products/${encodeURIComponent(sku)}`,
    { method: "DELETE" },
  );
}

export async function findSimilar(sku: string, k = 12, category?: Category) {
  const params = new URLSearchParams({ k: String(k) });
  if (category) params.set("category", category);
  return apiFetch<SearchResponse>(
    `/products/${encodeURIComponent(sku)}/similar?${params.toString()}`,
    { method: "POST" },
  );
}

export interface SearchParams {
  mode: SearchMode;
  query?: string;
  image?: File | null;
  k?: number;
  category?: Category;
}

export async function search(params: SearchParams) {
  const form = new FormData();
  form.append("mode", params.mode);
  form.append("k", String(params.k ?? 12));
  if (params.query) form.append("query", params.query);
  if (params.category) form.append("category", params.category);
  if (params.image) form.append("image", params.image);
  return apiFetch<SearchResponse>("/search", { method: "POST", body: form });
}

export async function getCatalogStats() {
  return apiFetch<CatalogStats>("/catalog/stats");
}

export async function getCatalogGrowth(days = 14) {
  return apiFetch<CatalogGrowthPoint[]>(`/catalog/stats/growth?days=${days}`);
}

export async function rebuildIndex() {
  return apiFetch<CatalogStats>("/index/rebuild", { method: "POST" });
}
