import Link from "next/link";
import { Search, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CatalogStatsCards } from "@/components/dashboard/catalog-stats-cards";
import { RecentProductsTable } from "@/components/dashboard/recent-products-table";
import { CatalogGrowthChart } from "@/components/dashboard/catalog-growth-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your catalog, its CLIP embeddings, and the FAISS index — all stored in Backblaze B2.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild size="sm" variant="outline" className="h-8">
            <Link href="/catalog/new">
              <Plus className="h-3.5 w-3.5" />
              Add product
            </Link>
          </Button>
          <Button asChild size="sm" className="h-8">
            <Link href="/search">
              <Search className="h-3.5 w-3.5" />
              Search catalog
            </Link>
          </Button>
        </div>
      </div>
      <CatalogStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <CatalogGrowthChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentProductsTable />
        </div>
      </div>
    </div>
  );
}
