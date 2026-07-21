"use client";

import Link from "next/link";
import { SearchX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import type { SearchResult } from "@clip-visual-product-search/shared";
import { formatPrice, formatScore } from "@/lib/format";

interface ResultsGridProps {
  results: SearchResult[];
  isPending: boolean;
  /** Shown when a search has run and returned nothing. */
  searched: boolean;
}

export function ResultsGrid({ results, isPending, searched }: ResultsGridProps) {
  if (isPending) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-64 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (searched && results.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={SearchX}
          title="No matches found"
          description="Try a different description or photo, or widen the category filter."
        />
      </Card>
    );
  }

  if (results.length === 0) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {results.map((r) => (
        <Link
          key={r.product.sku}
          href={`/catalog/${encodeURIComponent(r.product.sku)}`}
          className="group"
        >
          <Card className="overflow-hidden card-hover h-full">
            <div className="relative aspect-square bg-muted">
              {r.product.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={r.product.image_url}
                  alt={r.product.title}
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                  No image
                </div>
              )}
              <Badge className="absolute top-2 right-2 bg-background/90 text-foreground shadow-sm">
                {formatScore(r.score)} match
              </Badge>
            </div>
            <div className="p-3 space-y-1">
              <p className="text-sm font-semibold truncate group-hover:underline">
                {r.product.title}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{r.product.category}</span>
                <span className="text-xs font-mono tabular-nums">
                  {formatPrice(r.product.price, r.product.currency)}
                </span>
              </div>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
