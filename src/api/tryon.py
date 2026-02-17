from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.tryon.engine import run_tryon, batch_tryon

router = APIRouter()


class TryonRequest(BaseModel):
    human_img: str  # URL to model (person) image
    garment_img: str  # URL to garment (jeans) image
    garment_desc: str = "Women's jeans"
    category: str = "lower_body"
    crop: bool = True


class BatchTryonRequest(BaseModel):
    model_images: list[str]  # List of URLs to model images
    garment_img: str
    garment_desc: str = "Women's jeans"


@router.post("/single")
async def single_tryon(req: TryonRequest):
    """Test a single try-on: one model + one garment."""
    try:
        result_url = await run_tryon(
            human_img=req.human_img,
            garment_img=req.garment_img,
            garment_desc=req.garment_desc,
            category=req.category,
            crop=req.crop,
        )
        return {"status": "success", "result_url": result_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_tryon_api(req: BatchTryonRequest):
    """Run try-on for one garment across multiple models."""
    try:
        results = await batch_tryon(
            model_images=req.model_images,
            garment_img=req.garment_img,
            garment_desc=req.garment_desc,
        )
        return {"status": "success", "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
