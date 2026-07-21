"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { CATEGORIES, CURRENCIES } from "@clip-visual-product-search/shared";
import type { Category, Currency, Product } from "@clip-visual-product-search/shared";
import { ImageDropzone } from "./image-dropzone";
import { ApiError } from "@/lib/api-client";
import { useCreateProduct, useUpdateProduct } from "@/lib/queries";

const schema = z.object({
  sku: z.string().min(1, "SKU is required").max(128),
  title: z.string().min(1, "Title is required").max(200),
  price: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, "Enter a price like 89.00"),
  currency: z.enum(CURRENCIES as unknown as [Currency, ...Currency[]]),
  category: z.enum(CATEGORIES as unknown as [Category, ...Category[]]),
});

type FormValues = z.infer<typeof schema>;

interface ProductFormProps {
  mode: "create" | "edit";
  product?: Product;
}

export function ProductForm({ mode, product }: ProductFormProps) {
  const router = useRouter();
  const isEdit = mode === "edit";
  const [image, setImage] = useState<File | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct(product?.sku ?? "");
  const submitting = createMutation.isPending || updateMutation.isPending;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      sku: product?.sku ?? "",
      title: product?.title ?? "",
      price: product ? String(product.price) : "",
      currency: (product?.currency ?? "USD") as Currency,
      category: (product?.category ?? "Footwear") as Category,
    },
  });

  const onSubmit = async (values: FormValues) => {
    if (!isEdit && !image) {
      setImageError("A product image is required.");
      return;
    }
    try {
      if (isEdit && product) {
        await updateMutation.mutateAsync({
          title: values.title,
          price: Number(values.price),
          currency: values.currency,
          category: values.category,
          image: image ?? undefined,
        });
        toast.success("Product updated");
        router.push(`/catalog/${encodeURIComponent(product.sku)}`);
      } else {
        const created = await createMutation.mutateAsync({
          sku: values.sku,
          title: values.title,
          price: Number(values.price),
          currency: values.currency,
          category: values.category,
          image,
        });
        toast.success("Product added and indexed");
        router.push(`/catalog/${encodeURIComponent(created.sku)}`);
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Something went wrong";
      toast.error(detail);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Product details</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <FormField
              control={form.control}
              name="sku"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>SKU</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="sku-teal-runner-01"
                      disabled={isEdit}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    {isEdit
                      ? "SKU is immutable once a product is created."
                      : "A unique id for this item, e.g. sku-teal-runner-01."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder="Teal Trail Runner" {...field} />
                  </FormControl>
                  {!isEdit && (
                    <FormDescription>A short, descriptive product name.</FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Price</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="decimal"
                        placeholder="89.00"
                        className="font-mono tabular-nums"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Currency</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {CURRENCIES.map((c) => (
                          <SelectItem key={c} value={c}>
                            {c}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Category</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-60">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {!isEdit && (
                    <FormDescription>
                      Pick the closest category (e.g. Footwear).
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">
              Product image{isEdit ? " (optional — replaces & re-embeds)" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-2">
            <ImageDropzone
              onFileSelected={(f) => {
                setImage(f);
                if (f) setImageError(null);
              }}
              initialPreview={isEdit ? product?.image_url ?? null : null}
              disabled={submitting}
            />
            {imageError && <p className="text-sm text-destructive">{imageError}</p>}
            <p className="text-xs text-muted-foreground">
              The image is embedded with CLIP and added to the FAISS index on save.
            </p>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting
              ? isEdit
                ? "Saving..."
                : "Adding..."
              : isEdit
                ? "Save changes"
                : "Add product"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
