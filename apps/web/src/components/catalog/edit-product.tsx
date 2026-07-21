"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useProduct } from "@/lib/queries";
import { ProductForm } from "./product-form";

export function EditProduct({ sku }: { sku: string }) {
  const { data: product, isLoading, error, refetch } = useProduct(sku);

  if (isLoading) return <Skeleton className="h-96 w-full max-w-2xl rounded-md" />;
  if (error) return <ErrorState error={error} title="Couldn't load product" onRetry={() => refetch()} />;
  if (!product) return null;

  return <ProductForm mode="edit" product={product} />;
}
