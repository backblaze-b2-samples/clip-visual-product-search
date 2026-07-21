"use client";

import { RefreshCw, Database } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { ApiError } from "@/lib/api-client";
import { useRebuildIndex } from "@/lib/queries";

export function IndexMaintenance() {
  const rebuild = useRebuildIndex();

  const onConfirm = () => {
    rebuild.mutate(undefined, {
      onSuccess: (stats) => {
        toast.success("Index rebuilt", {
          description: `${stats.index_vector_count} vectors from ${stats.embedding_count} embeddings.`,
        });
      },
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Rebuild failed";
        toast.error(detail);
      },
    });
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Index Maintenance</CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-4">
        <Alert>
          <Database />
          <AlertTitle>Rebuild the FAISS index from B2</AlertTitle>
          <AlertDescription>
            Re-reads every <code>catalog/embeddings/*.npy</code> object and rewrites the
            index + id map to B2. Safe to run any time; useful after bulk changes or if the
            index and catalog drift.
          </AlertDescription>
        </Alert>
        <div className="flex items-center justify-between rounded-md border border-border p-3">
          <div>
            <p className="text-sm font-medium">Rebuild search index</p>
            <p className="text-xs text-muted-foreground">
              Reconstructs the vector index from stored embeddings.
            </p>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={rebuild.isPending}>
                <RefreshCw className={`h-3.5 w-3.5 ${rebuild.isPending ? "animate-spin" : ""}`} />
                {rebuild.isPending ? "Rebuilding..." : "Rebuild index"}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Rebuild the search index?</AlertDialogTitle>
                <AlertDialogDescription>
                  This scans all embeddings in B2 and rewrites the FAISS index. It may take a
                  moment for large catalogs, but it is non-destructive.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onConfirm}>Rebuild</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
