"""Low-level byte/object helpers for the catalog, embedding, and index artifacts.

Boto3 stays confined to `repo/` (AGENTS.md invariant). These functions are the
sole data-access surface the catalog/index/search services use to read and write
the three parallel B2 artifact sets: product images, per-SKU `.npy` embeddings,
and the FAISS index + id map. The presigned-URL and connectivity helpers live in
`b2_client.py` and are reused via `get_s3_client`.
"""

import io

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import _invalidate_list_cache, _public_url, get_s3_client


def get_inline_url(key: str, expires_in: int = 3600) -> str:
    """Presigned GET URL for inline browser rendering (no attachment disposition).

    Streams product/catalog images into <img> tags and result grids. Prefers a
    public URL when `B2_PUBLIC_URL_BASE` is set; otherwise a short-lived
    presigned GET. Raises RuntimeError on presign failure.
    """
    public = _public_url(key)
    if public:
        return public
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Write raw bytes to B2 at `key`. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()


def get_bytes(key: str) -> bytes | None:
    """Read an object's bytes, or None if it does not exist."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def object_exists(key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.b2_bucket_name, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return False
        raise RuntimeError(f"B2 head failed for '{key}': {e}") from e


def list_prefix(prefix: str) -> list[dict]:
    """Return [{'key', 'size', 'last_modified'}] for every object under `prefix`."""
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return out


def delete_key(key: str) -> None:
    """Delete a single object. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 delete failed for '{key}': {e}") from e
    _invalidate_list_cache()


def delete_prefix(prefix: str) -> None:
    """Delete every object under `prefix` (scoped to the given SKU folder)."""
    for obj in list_prefix(prefix):
        delete_key(obj["key"])
