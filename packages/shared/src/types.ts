export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Product catalog + CLIP search ---

export const CATEGORIES = [
  "Apparel",
  "Footwear",
  "Accessories",
  "Home",
  "Electronics",
  "Beauty",
] as const;
export type Category = (typeof CATEGORIES)[number];

export const CURRENCIES = ["USD", "EUR", "GBP"] as const;
export type Currency = (typeof CURRENCIES)[number];

export type SearchMode = "text" | "image";

export interface Product {
  sku: string;
  title: string;
  price: number;
  currency: Currency;
  category: Category;
  image_key: string;
  created_at: string;
  image_url: string | null;
}

export interface SearchResult {
  product: Product;
  score: number;
}

export interface SearchResponse {
  mode: SearchMode;
  query: string | null;
  count: number;
  results: SearchResult[];
}

export interface CatalogStats {
  product_count: number;
  embedding_count: number;
  index_vector_count: number;
  catalog_bytes: number;
  catalog_bytes_human: string;
}

export interface CatalogGrowthPoint {
  date: string;
  products: number;
}
