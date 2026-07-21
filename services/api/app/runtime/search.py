import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.service import search
from app.service.catalog import CatalogError
from app.types import Category, SearchMode, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    mode: SearchMode = Form(...),
    query: str | None = Form(default=None),
    k: int = Form(default=12),
    category: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    """Marquee cross-modal search entry point.

    `mode=text` reads `query`; `mode=image` reads the uploaded `image`. Both
    embed into the same CLIP space, so results are ranked by cosine similarity
    against every catalog product's embedding.
    """
    k = max(1, min(k, 48))
    cat = Category(category) if category else None
    try:
        if mode == SearchMode.text:
            return await run_in_threadpool(search.search_text, query or "", k, cat)
        image_bytes = await image.read() if image is not None else b""
        return await run_in_threadpool(search.search_image, image_bytes, k, cat)
    except CatalogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
