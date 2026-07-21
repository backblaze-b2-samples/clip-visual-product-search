"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { search, ApiError, type SearchParams } from "@/lib/api-client";
import { SearchForm } from "@/components/search/search-form";
import { ResultsGrid } from "@/components/search/results-grid";
import { ErrorState } from "@/components/ui/error-state";

export default function SearchPage() {
  const mutation = useMutation({
    mutationFn: (params: SearchParams) => search(params),
    onError: (err) => {
      const detail = err instanceof ApiError ? err.message : "Search failed";
      toast.error(detail);
    },
  });

  const response = mutation.data;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Visual Product Search</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Find catalog items by describing them or uploading a photo. Queries and products
          are embedded into the same CLIP space, then ranked by cosine similarity against a
          FAISS index — all backed by Backblaze B2.
        </p>
      </div>

      <div className="animate-fade-in-up stagger-2">
        <SearchForm onSearch={(p) => mutation.mutate(p)} isPending={mutation.isPending} />
      </div>

      {mutation.isError && !mutation.isPending && (
        <ErrorState error={mutation.error as Error} onRetry={() => mutation.reset()} />
      )}

      <div className="animate-fade-in-up stagger-3">
        {response && !mutation.isPending && (
          <p className="mb-3 text-sm text-muted-foreground">
            {response.count} result{response.count === 1 ? "" : "s"}
            {response.query ? ` for "${response.query}"` : " for your image"}
          </p>
        )}
        <ResultsGrid
          results={response?.results ?? []}
          isPending={mutation.isPending}
          searched={mutation.isSuccess}
        />
      </div>
    </div>
  );
}
