"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useCatalogGrowth } from "@/lib/queries";

const DAYS = 14;

const chartConfig = {
  products: {
    label: "Products added",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

const skeletonBarHeights = ["h-24", "h-32", "h-20", "h-36", "h-28", "h-40", "h-24"];

function GrowthChartSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="h-[240px] w-full rounded-md border border-border bg-muted/20 px-4 py-4"
    >
      <span className="sr-only">Loading catalog growth</span>
      <div aria-hidden className="flex h-full items-end gap-3">
        {skeletonBarHeights.map((height, i) => (
          <Skeleton key={i} className={`${height} min-w-0 flex-1 motion-reduce:animate-none`} />
        ))}
      </div>
    </div>
  );
}

export function CatalogGrowthChart() {
  const { data: growth, isLoading, error, refetch } = useCatalogGrowth(DAYS);

  const data = useMemo(
    () =>
      (growth ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        products: d.products,
      })),
    [growth],
  );

  const total = data.reduce((sum, d) => sum + d.products, 0);
  const known = growth !== undefined;
  const hasAny = data.some((d) => d.products > 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Catalog Growth</CardTitle>
        <CardDescription className="text-xs">Products added · last {DAYS} days</CardDescription>
        <CardAction className="text-right self-center">
          {isLoading ? (
            <div aria-hidden className="space-y-1">
              <Skeleton className="ml-auto h-2.5 w-10 motion-reduce:animate-none" />
              <Skeleton className="ml-auto h-6 w-12 motion-reduce:animate-none" />
            </div>
          ) : (
            <>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Total
              </div>
              <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
                {known ? total : "-"}
              </div>
            </>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <GrowthChartSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !hasAny ? (
          <EmptyState
            icon={BarChart3}
            title="No products yet"
            description="Seed the catalog or add a product to see growth here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="products-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-products)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-products)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                tickMargin={6}
                fontSize={11}
                width={28}
              />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar
                dataKey="products"
                fill="url(#products-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
