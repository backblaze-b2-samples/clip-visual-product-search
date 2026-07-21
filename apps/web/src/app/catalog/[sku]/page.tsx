import { ProductDetail } from "@/components/catalog/product-detail";

export default async function ProductPage({
  params,
}: {
  params: Promise<{ sku: string }>;
}) {
  const { sku } = await params;
  return <ProductDetail sku={sku} />;
}
