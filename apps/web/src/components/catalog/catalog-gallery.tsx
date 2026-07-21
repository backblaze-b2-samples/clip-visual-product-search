"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, PackageOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATEGORIES } from "@clip-visual-product-search/shared";
import type { Category } from "@clip-visual-product-search/shared";
import { useProducts } from "@/lib/queries";
import { formatPrice } from "@/lib/format";

const ALL = "__all__";

export function CatalogGallery() {
  const [category, setCategory] = useState<string>(ALL);
  const { data: products = [], isLoading, error, refetch } = useProducts(
    category === ALL ? undefined : (category as Category),
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button asChild size="sm">
          <Link href="/catalog/new">
            <Plus className="h-3.5 w-3.5" />
            Add product
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-md" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} title="Couldn't load the catalog" onRetry={() => refetch()} />
      ) : products.length === 0 ? (
        <Card>
          <EmptyState
            icon={PackageOpen}
            title="No products yet"
            description="Add a product, or run `python scripts/seed-catalog.py` to populate a demo catalog."
            action={
              <Button asChild size="sm">
                <Link href="/catalog/new">
                  <Plus className="h-3.5 w-3.5" />
                  Add product
                </Link>
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {products.map((p) => (
            <Link key={p.sku} href={`/catalog/${encodeURIComponent(p.sku)}`} className="group">
              <Card className="overflow-hidden card-hover h-full">
                <div className="aspect-square bg-muted">
                  {p.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.image_url}
                      alt={p.title}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                      No image
                    </div>
                  )}
                </div>
                <div className="p-3 space-y-1">
                  <p className="text-sm font-semibold truncate group-hover:underline">
                    {p.title}
                  </p>
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary">{p.category}</Badge>
                    <span className="text-xs font-mono tabular-nums">
                      {formatPrice(p.price, p.currency)}
                    </span>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
