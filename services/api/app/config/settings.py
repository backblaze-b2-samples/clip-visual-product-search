from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    # Standard B2_* names (parent CLAUDE.md standard #3). The endpoint is
    # derived from the region so a fork only sets B2_REGION; B2_ENDPOINT stays
    # an optional explicit override.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    # Optional explicit endpoint override. When empty, `endpoint_url` derives
    # it from b2_region — no region string is hardcoded in source.
    b2_endpoint: str = ""
    # Optional. Only used to build public object URLs when the bucket is
    # public; the app streams images via presigned URLs when this is unset, so
    # it must never be treated as required.
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and exploration; set false to hide the full API surface.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits (product images)
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Optional confinement for key-addressed reads/deletes in the full-bucket
    # explorer. Empty by default so the by-key routes accept any key shape.
    allowed_key_prefix: str = ""

    # Rate limiting (per client IP, per 60s window). In-process per replica.
    rate_limit_per_minute: int = 120
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc).
    download_count_file: str = "data/download_count.json"

    # --- Catalog / CLIP layout ---
    # Bucket key prefixes for the three parallel artifact sets. B2 is the sole
    # store — there is no application database.
    catalog_images_prefix: str = "catalog/images/"
    catalog_embeddings_prefix: str = "catalog/embeddings/"
    catalog_index_key: str = "catalog/index/faiss.index"
    catalog_id_map_key: str = "catalog/index/id_map.json"
    catalog_metadata_key: str = "catalog/metadata.csv"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def endpoint_url(self) -> str:
        """Resolve the S3 endpoint: explicit override wins, else derive from region."""
        if self.b2_endpoint:
            return self.b2_endpoint
        if self.b2_region:
            return f"https://s3.{self.b2_region}.backblazeb2.com"
        return ""

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield
        # a stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
