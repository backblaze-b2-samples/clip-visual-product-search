"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useDropzone } from "react-dropzone";
import { ImagePlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ImageDropzoneProps {
  onFileSelected: (file: File | null) => void;
  /** Existing image URL (edit form) shown until a new file is picked. */
  initialPreview?: string | null;
  disabled?: boolean;
}

const ACCEPT = { "image/jpeg": [], "image/png": [], "image/webp": [], "image/gif": [] };
const MAX_SIZE = 100 * 1024 * 1024; // 100MB

export function ImageDropzone({
  onFileSelected,
  initialPreview,
  disabled,
}: ImageDropzoneProps) {
  const describedBy = useId();
  const [preview, setPreview] = useState<string | null>(initialPreview ?? null);
  const [ownsPreview, setOwnsPreview] = useState(false);

  // Revoke any object URL we created to avoid leaks.
  useEffect(() => {
    return () => {
      if (ownsPreview && preview) URL.revokeObjectURL(preview);
    };
  }, [ownsPreview, preview]);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      const url = URL.createObjectURL(file);
      setPreview(url);
      setOwnsPreview(true);
      onFileSelected(file);
    },
    [onFileSelected],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    disabled,
    multiple: false,
  });

  const clear = () => {
    if (ownsPreview && preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setOwnsPreview(false);
    onFileSelected(null);
  };

  const active = isDragActive && !disabled;

  return (
    <div className="space-y-2">
      <div
        {...getRootProps({
          "aria-describedby": describedBy,
          "aria-label": "Product image",
          role: "button",
        })}
        className={[
          "flex min-h-44 flex-col items-center justify-center rounded-md",
          "border-2 border-dashed px-4 py-6 text-center transition-colors",
          active
            ? "border-primary bg-[var(--accent-subtle)]"
            : "border-border hover:border-primary/60 hover:bg-muted/60",
          disabled ? "cursor-not-allowed opacity-70" : "cursor-pointer",
        ].join(" ")}
      >
        <input {...getInputProps({ "aria-label": "Choose a product image" })} />
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={preview}
            alt="Selected product preview"
            className="max-h-40 rounded-md object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-md bg-muted border border-border">
              <ImagePlus className="h-5 w-5 text-muted-foreground" aria-hidden />
            </div>
            <p className="text-sm font-semibold">
              Drag &amp; drop a product image, or click to browse
            </p>
            <p id={describedBy} className="text-xs text-muted-foreground">
              JPEG, PNG, WebP, or GIF · up to 100 MB
            </p>
          </div>
        )}
      </div>
      {preview && !disabled && (
        <div className="flex justify-end">
          <Button type="button" variant="ghost" size="sm" onClick={clear}>
            <X className="h-3.5 w-3.5" />
            Remove image
          </Button>
        </div>
      )}
    </div>
  );
}
