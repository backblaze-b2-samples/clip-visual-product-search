"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createProduct,
  deleteFile,
  deleteProduct,
  getCatalogGrowth,
  getCatalogStats,
  getFiles,
  getFileStats,
  getHealth,
  getPreviewUrl,
  getProduct,
  getProducts,
  getUploadActivity,
  rebuildIndex,
  updateProduct,
  type ProductFormValues,
} from "@/lib/api-client";
import type { Category, FileMetadata } from "@clip-visual-product-search/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  health: () => [...qk.all, "health"] as const,
  // Catalog + CLIP search
  products: (category?: string) => [...qk.all, "products", category ?? "all"] as const,
  product: (sku: string) => [...qk.all, "product", sku] as const,
  catalogStats: () => [...qk.all, "catalog", "stats"] as const,
  catalogGrowth: (days: number) => [...qk.all, "catalog", "growth", days] as const,
};

export type Health = Awaited<ReturnType<typeof getHealth>>;

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

// Health poll for the top-of-app B2 banner. `retry: false` and letting a
// failed fetch leave `data` undefined keeps a down API silent (the
// per-component ErrorState covers that); the banner only reacts to an up API
// reporting b2_connected: false. Polls every 60s and on window focus.
export function useHealth() {
  return useQuery<Health>({
    queryKey: qk.health(),
    queryFn: getHealth,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Product catalog + CLIP search ---

export function useProducts(category?: Category) {
  return useQuery({
    queryKey: qk.products(category),
    queryFn: () => getProducts(category),
  });
}

export function useProduct(sku: string | undefined) {
  return useQuery({
    queryKey: qk.product(sku ?? ""),
    queryFn: () => getProduct(sku as string),
    enabled: !!sku,
  });
}

export function useCatalogStats() {
  return useQuery({
    queryKey: qk.catalogStats(),
    queryFn: getCatalogStats,
  });
}

export function useCatalogGrowth(days = 14) {
  return useQuery({
    queryKey: qk.catalogGrowth(days),
    queryFn: () => getCatalogGrowth(days),
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: ProductFormValues) => createProduct(values),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useUpdateProduct(sku: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: Partial<Omit<ProductFormValues, "sku">>) =>
      updateProduct(sku, values),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sku: string) => deleteProduct(sku),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useRebuildIndex() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => rebuildIndex(),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}
