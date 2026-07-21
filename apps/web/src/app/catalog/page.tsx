import { CatalogGallery } from "@/components/catalog/catalog-gallery";

export default function CatalogPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Catalog</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Every product and its CLIP embedding live under the <code>catalog/images/</code>{" "}
          prefix in Backblaze B2. This is the sample-scoped view; the{" "}
          <a href="/files" className="underline">Files</a> page browses the whole bucket.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CatalogGallery />
      </div>
    </div>
  );
}
