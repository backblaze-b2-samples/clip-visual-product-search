import logging

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.service import catalog
from app.service import index as index_service
from app.types import CatalogGrowthPoint, CatalogStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/catalog/stats", response_model=CatalogStats)
def catalog_stats_endpoint():
    return catalog.get_stats()


@router.get("/catalog/stats/growth", response_model=list[CatalogGrowthPoint])
def catalog_growth_endpoint(days: int = 14):
    days = max(1, min(days, 90))
    return catalog.get_growth(days=days)


@router.post("/index/rebuild", response_model=CatalogStats)
async def rebuild_index_endpoint():
    """Admin action (wired to Settings → 'Rebuild index'): rebuild FAISS from B2."""
    count = await run_in_threadpool(index_service.rebuild_from_b2)
    logger.info("Index rebuilt from B2: %d vectors", count)
    return catalog.get_stats()
