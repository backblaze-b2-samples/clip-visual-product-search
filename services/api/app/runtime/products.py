import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.service import catalog, search
from app.service.catalog import CatalogError
from app.types import (
    Category,
    Product,
    ProductCreate,
    ProductUpdate,
    SearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _http_error(e: CatalogError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/products", response_model=Product, status_code=201)
async def create_product_endpoint(
    sku: str = Form(...),
    title: str = Form(...),
    price: float = Form(...),
    currency: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        data = ProductCreate(
            sku=sku, title=title, price=price, currency=currency, category=category
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from None
    image_bytes = await image.read()
    filename = image.filename or "image"
    try:
        return await run_in_threadpool(
            catalog.create_product, data, image_bytes, filename
        )
    except CatalogError as e:
        raise _http_error(e) from None


@router.get("/products", response_model=list[Product])
def list_products_endpoint(category: Category | None = Query(default=None)):
    return catalog.list_products(category=category)


@router.get("/products/{sku}", response_model=Product)
def get_product_endpoint(sku: str):
    try:
        return catalog.get_product(sku)
    except CatalogError as e:
        raise _http_error(e) from None


@router.patch("/products/{sku}", response_model=Product)
async def update_product_endpoint(
    sku: str,
    title: str | None = Form(default=None),
    price: float | None = Form(default=None),
    currency: str | None = Form(default=None),
    category: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    try:
        data = ProductUpdate(
            title=title, price=price, currency=currency, category=category
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from None
    image_bytes = await image.read() if image is not None else None
    filename = image.filename if image is not None else None
    try:
        return await run_in_threadpool(
            catalog.update_product, sku, data, image_bytes, filename
        )
    except CatalogError as e:
        raise _http_error(e) from None


@router.delete("/products/{sku}")
def delete_product_endpoint(sku: str):
    try:
        catalog.delete_product(sku)
    except CatalogError as e:
        raise _http_error(e) from None
    return {"deleted": True, "sku": sku}


@router.post("/products/{sku}/similar", response_model=SearchResponse)
def similar_products_endpoint(
    sku: str,
    k: int = Query(default=12, ge=1, le=48),
    category: Category | None = Query(default=None),
):
    """Run verb: image-to-image search from the product's stored CLIP embedding."""
    try:
        return search.search_similar(sku, k=k, category=category)
    except CatalogError as e:
        raise _http_error(e) from None
