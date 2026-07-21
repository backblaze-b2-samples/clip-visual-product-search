"use client";

import { useState } from "react";
import { Search, Type, Image as ImageIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATEGORIES } from "@clip-visual-product-search/shared";
import type { Category, SearchMode } from "@clip-visual-product-search/shared";
import { ImageDropzone } from "@/components/catalog/image-dropzone";
import type { SearchParams } from "@/lib/api-client";

const TOP_K = [4, 8, 12, 24];
const ALL = "__all__";

interface SearchFormProps {
  onSearch: (params: SearchParams) => void;
  isPending: boolean;
}

export function SearchForm({ onSearch, isPending }: SearchFormProps) {
  const [mode, setMode] = useState<SearchMode>("text");
  const [query, setQuery] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [k, setK] = useState(12);
  const [category, setCategory] = useState<string>(ALL);

  const canSubmit = mode === "text" ? query.trim().length > 0 : image !== null;

  const submit = () => {
    if (!canSubmit) return;
    onSearch({
      mode,
      query: mode === "text" ? query.trim() : undefined,
      image: mode === "image" ? image : undefined,
      k,
      category: category === ALL ? undefined : (category as Category),
    });
  };

  return (
    <Card>
      <CardContent className="p-5 space-y-5">
        {/* Mode — segmented control (a selector, not free text) */}
        <div className="space-y-2">
          <Label>Search by</Label>
          <div
            role="tablist"
            aria-label="Search mode"
            className="inline-flex rounded-md border border-border p-0.5 bg-muted/40"
          >
            {(
              [
                { value: "text", label: "Text", icon: Type },
                { value: "image", label: "Image", icon: ImageIcon },
              ] as const
            ).map((m) => {
              const isActive = mode === m.value;
              return (
                <button
                  key={m.value}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setMode(m.value)}
                  className={[
                    "inline-flex items-center gap-1.5 rounded-[5px] px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-background shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  <m.icon className="h-3.5 w-3.5" />
                  {m.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Query input — free text (text mode) or an image picker (image mode) */}
        {mode === "text" ? (
          <div className="space-y-2">
            <Label htmlFor="search-query">Describe what you&apos;re looking for</Label>
            <Input
              id="search-query"
              placeholder="e.g. teal running shoe with white sole"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submit();
              }}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <Label>Upload a reference photo</Label>
            <ImageDropzone onFileSelected={setImage} disabled={isPending} />
          </div>
        )}

        {/* Refinements — finite-option selectors */}
        <div className="flex flex-wrap gap-4">
          <div className="space-y-2">
            <Label>Results</Label>
            <Select value={String(k)} onValueChange={(v) => setK(Number(v))}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TOP_K.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    Top {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-44">
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
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={submit} disabled={!canSubmit || isPending}>
            <Search className="h-4 w-4" />
            {isPending ? "Searching..." : "Search"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
