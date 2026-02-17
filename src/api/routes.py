from fastapi import APIRouter

from src.api.products import router as products_router
from src.api.pipeline import router as pipeline_router
from src.api.tryon import router as tryon_router
from src.api.publish import router as publish_router

router = APIRouter()
router.include_router(products_router, prefix="/products", tags=["products"])
router.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"])
router.include_router(tryon_router, prefix="/tryon", tags=["tryon"])
router.include_router(publish_router, prefix="/publish", tags=["publish"])
