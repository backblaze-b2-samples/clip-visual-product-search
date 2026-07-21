import { EditProduct } from "@/components/catalog/edit-product";

export default async function EditProductPage({
  params,
}: {
  params: Promise<{ sku: string }>;
}) {
  const { sku } = await params;
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Edit Product</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Update metadata, or replace the image to re-embed and re-index this product.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <EditProduct sku={sku} />
      </div>
    </div>
  );
}
