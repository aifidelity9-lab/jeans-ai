import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from src.tryon.engine import run_tryon, download_image
from src.video.generator import generate_video, download_video
from src.editor.composer import compose_video
from src.tasks.daily_pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class PipelineRequest(BaseModel):
    """Run the full pipeline for one product + one model."""
    garment_img: str  # URL or local path to garment image
    human_img: str  # URL or local path to model image
    garment_desc: str = "Women's light blue denim jeans"
    category: str = "lower_body"  # "lower_body" (jeans) or "upper_body" (tshirts)
    caption: str = "Your new favorite jeans"
    cta_text: str = "Shop now - Link in bio"
    video_prompt: str = (
        "A fashion model walks naturally towards the camera, "
        "showing off her outfit, confident stride, studio lighting"
    )


class BatchPipelineRequest(BaseModel):
    """Run pipeline for one product across multiple models."""
    garment_img: str
    human_imgs: list[str]
    garment_desc: str = "Women's light blue denim jeans"
    category: str = "lower_body"


@router.post("/run")
async def run_pipeline(req: PipelineRequest):
    """Full pipeline: try-on → video → edit → final video.

    Returns paths and URLs for each stage.
    """
    results = {"stages": {}}

    # Stage 1: Virtual try-on
    logger.info("Stage 1: Virtual try-on...")
    tryon_path = await run_tryon(
        human_img=req.human_img,
        garment_img=req.garment_img,
        garment_desc=req.garment_desc,
        category=req.category,
    )
    tryon_local = await download_image(tryon_path, "output/tryon/pipeline_tryon.png")
    results["stages"]["tryon"] = {"local": tryon_local}

    # Stage 2: Generate video from try-on image
    logger.info("Stage 2: Video generation...")
    video_path = await generate_video(
        image_path=tryon_local,
        prompt=req.video_prompt,
    )
    video_local = await download_video(video_path, "output/videos/pipeline_video.mp4")
    results["stages"]["video"] = {"local": video_local}

    # Stage 3: Compose final video with overlays
    logger.info("Stage 3: Composing final video...")
    final_path = compose_video(
        video_clips=[video_local],
        output_path="output/final/pipeline_final.mp4",
        caption=req.caption,
        cta_text=req.cta_text,
    )
    results["stages"]["final"] = {"local": final_path}

    results["status"] = "complete"
    results["final_video"] = final_path
    return results


@router.post("/batch")
async def run_batch_pipeline(req: BatchPipelineRequest):
    """Run pipeline for one garment across multiple models.

    This is what you'd use for daily production:
    1 garment × N models = N final videos.
    """
    results = []

    for i, human_img in enumerate(req.human_imgs):
        logger.info(f"Processing model {i+1}/{len(req.human_imgs)}...")
        try:
            # Try-on
            tryon_path = await run_tryon(
                human_img=human_img,
                garment_img=req.garment_img,
                garment_desc=req.garment_desc,
                category=req.category,
            )
            tryon_local = await download_image(
                tryon_path, f"output/tryon/batch_{i:04d}.png"
            )

            # Video
            video_path = await generate_video(image_path=tryon_local)
            video_local = await download_video(
                video_path, f"output/videos/batch_{i:04d}.mp4"
            )

            # Compose
            final_path = compose_video(
                video_clips=[video_local],
                output_path=f"output/final/batch_{i:04d}.mp4",
            )

            results.append({
                "model": human_img,
                "status": "complete",
                "final_video": final_path,
            })
        except Exception as e:
            logger.error(f"Failed for model {i}: {e}")
            results.append({
                "model": human_img,
                "status": "failed",
                "error": str(e),
            })

    return {
        "total": len(req.human_imgs),
        "success": sum(1 for r in results if r["status"] == "complete"),
        "results": results,
    }


@router.post("/daily")
async def trigger_daily_pipeline(
    max_videos: int = 100,
    concurrency: int = 3,
    category_name: str = "jeans",
):
    """Manually trigger the daily pipeline.

    Args:
        category_name: Category name (e.g. "jeans", "tshirts").
    """
    result = await run_daily_pipeline(
        max_videos=max_videos, concurrency=concurrency, category_name=category_name
    )
    return result
