import { ProductForm } from "@/components/catalog/product-form";

export default function NewProductPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Add Product</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload a product photo and its details. On save, the image is embedded with CLIP,
          added to the FAISS index, and written to Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ProductForm mode="create" />
      </div>
    </div>
  );
}
