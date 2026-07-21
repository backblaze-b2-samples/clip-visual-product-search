"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Sparkles, Pencil, Trash2, ArrowLeft } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ResultsGrid } from "@/components/search/results-grid";
import { findSimilar, ApiError } from "@/lib/api-client";
import { useProduct, useDeleteProduct } from "@/lib/queries";
import { formatPrice, formatScore } from "@/lib/format";

export function ProductDetail({ sku }: { sku: string }) {
  const router = useRouter();
  const { data: product, isLoading, error, refetch } = useProduct(sku);
  const deleteMutation = useDeleteProduct();
  const similar = useMutation({
    mutationFn: () => findSimilar(sku, 8),
    onError: (err) => {
      const detail = err instanceof ApiError ? err.message : "Find similar failed";
      toast.error(detail);
    },
  });

  if (isLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="aspect-square w-full rounded-md" />
        <Skeleton className="h-64 w-full rounded-md" />
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} title="Couldn't load product" onRetry={() => refetch()} />;
  }

  if (!product) return null;

  const onDelete = () => {
    deleteMutation.mutate(sku, {
      onSuccess: () => {
        toast.success(`${product.title} deleted`);
        router.push("/catalog");
      },
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Failed to delete product";
        toast.error(detail);
      },
    });
  };

  return (
    <div className="space-y-8">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link href="/catalog">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to catalog
        </Link>
      </Button>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <div className="aspect-square bg-muted">
            {product.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={product.image_url}
                alt={product.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No image
              </div>
            )}
          </div>
        </Card>

        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{product.category}</Badge>
              <span className="text-xs font-mono text-muted-foreground">{product.sku}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">{product.title}</h1>
            <p className="text-xl font-mono tabular-nums">
              {formatPrice(product.price, product.currency)}
            </p>
          </div>

          <Card>
            <CardHeader className="border-b border-border py-3 px-4">
              <CardTitle className="card-title text-sm">CLIP embedding</CardTitle>
            </CardHeader>
            <CardContent className="p-4 text-sm text-muted-foreground space-y-1">
              <p>512-d vector stored at</p>
              <code className="text-xs break-all">
                catalog/embeddings/{product.sku}.npy
              </code>
              <p className="pt-2">Image object</p>
              <code className="text-xs break-all">{product.image_key}</code>
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => similar.mutate()} disabled={similar.isPending}>
              <Sparkles className="h-4 w-4" />
              {similar.isPending ? "Finding..." : "Find similar"}
            </Button>
            <Button asChild variant="outline">
              <Link href={`/catalog/${encodeURIComponent(product.sku)}/edit`}>
                <Pencil className="h-4 w-4" />
                Edit
              </Link>
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline">
                  <Trash2 className="h-4 w-4" />
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete this product?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This permanently removes <strong>{product.title}</strong>, its image, and
                    its embedding from B2, and drops it from the FAISS index. This cannot be
                    undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={onDelete}
                    disabled={deleteMutation.isPending}
                    className={buttonVariants({ variant: "destructive" })}
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Delete"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </div>

      {(similar.isPending || similar.data) && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">
            Similar products
            {similar.data ? (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                (image-to-image, top match {similar.data.results[0]
                  ? formatScore(similar.data.results[0].score)
                  : "—"})
              </span>
            ) : null}
          </h2>
          <ResultsGrid
            results={similar.data?.results ?? []}
            isPending={similar.isPending}
            searched={similar.isSuccess}
          />
        </div>
      )}
    </div>
  );
}
