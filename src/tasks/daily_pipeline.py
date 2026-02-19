"""Daily automated pipeline: generates try-on videos for all active products × models.

Schedule this with Celery Beat or a simple cron/scheduler.
Designed to run once per day and produce ~100 final videos.
"""

import asyncio
import logging
from datetime import datetime
from itertools import product as cartesian
from pathlib import Path

from src.config import settings
from src.tryon.engine import run_tryon, download_image
from src.video.generator import generate_video, download_video
from src.editor.composer import compose_video

logger = logging.getLogger(__name__)

# Default video prompts for variety
VIDEO_PROMPTS = [
    "A fashion model walks confidently towards the camera, showing off her jeans, studio lighting, clean background",
    "A woman turns slowly to show her outfit from different angles, natural movement, white background",
    "A model poses naturally, shifting weight between legs, showing the fit of her jeans, soft lighting",
    "A woman walks casually along a street, confident stride, showing her denim jeans, natural daylight",
    "A fashion model does a slow spin to show the full outfit, studio background, professional lighting",
]

# Marketing captions for variety
CAPTIONS = [
    "Your new favorite jeans",
    "Comfort meets style",
    "Perfect fit, every time",
    "Denim that moves with you",
    "Effortlessly cool",
    "Made for your curves",
    "From day to night",
    "The perfect pair exists",
    "Confidence looks good on you",
    "Upgrade your denim game",
]


def get_product_images(products_dir: str = "assets/products") -> list[str]:
    """Scan products directory for garment images."""
    p = Path(products_dir)
    if not p.exists():
        logger.warning(f"Products directory not found: {products_dir}")
        return []
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = [str(f) for f in p.iterdir() if f.suffix.lower() in extensions]
    logger.info(f"Found {len(images)} product images")
    return sorted(images)


def get_model_images(models_dir: str = "assets/models") -> list[str]:
    """Scan models directory for human images."""
    p = Path(models_dir)
    if not p.exists():
        logger.warning(f"Models directory not found: {models_dir}")
        return []
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images = [str(f) for f in p.iterdir() if f.suffix.lower() in extensions]
    logger.info(f"Found {len(images)} model images")
    return sorted(images)


async def run_single(
    garment_path: str,
    model_path: str,
    index: int,
    date_str: str,
) -> dict:
    """Run full pipeline for one garment × one model combination."""
    output_base = f"output/{date_str}"
    result = {
        "garment": garment_path,
        "model": model_path,
        "index": index,
        "status": "started",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Stage 1: Try-on
            logger.info(f"[{index}] Stage 1: Try-on {Path(garment_path).name} × {Path(model_path).name}")
            tryon_url = await run_tryon(
                human_img=model_path,
                garment_img=garment_path,
                garment_desc="Women's denim jeans",
            )
            tryon_local = await download_image(
                tryon_url, f"{output_base}/tryon/tryon_{index:04d}.png"
            )
            result["tryon"] = tryon_local

            # Stage 2: Video generation
            logger.info(f"[{index}] Stage 2: Video generation")
            prompt = VIDEO_PROMPTS[index % len(VIDEO_PROMPTS)]
            video_url = await generate_video(image_path=tryon_url, prompt=prompt)
            video_local = await download_video(
                video_url, f"{output_base}/videos/video_{index:04d}.mp4"
            )
            result["video"] = video_local

            # Stage 3: Compose final video
            logger.info(f"[{index}] Stage 3: Composing final video")
            caption = CAPTIONS[index % len(CAPTIONS)]
            final_path = compose_video(
                video_clips=[video_local],
                output_path=f"{output_base}/final/final_{index:04d}.mp4",
                caption=caption,
            )
            result["final"] = final_path
            result["status"] = "complete"
            logger.info(f"[{index}] Complete: {final_path}")
            break  # Success, exit retry loop

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                logger.warning(f"[{index}] Rate limited, retrying in {wait}s... (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
                continue
            result["status"] = "failed"
            result["error"] = error_str
            logger.error(f"[{index}] Failed: {e}")

    return result


async def run_daily_pipeline(
    max_videos: int = 100,
    concurrency: int = 3,
) -> dict:
    """Run the full daily pipeline.

    Generates try-on videos for all product × model combinations,
    up to max_videos limit.

    Args:
        max_videos: Maximum number of videos to generate.
        concurrency: How many to process in parallel.

    Returns:
        Summary dict with results.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"=== Daily Pipeline Started: {date_str} ===")

    products = get_product_images()
    models = get_model_images()

    if not products:
        return {"error": "No product images found in assets/products/"}
    if not models:
        return {"error": "No model images found in assets/models/"}

    # Generate all combinations
    combinations = list(cartesian(products, models))
    logger.info(f"Total combinations: {len(combinations)} (capped at {max_videos})")
    combinations = combinations[:max_videos]

    # Process in batches for concurrency control
    results = []
    for batch_start in range(0, len(combinations), concurrency):
        batch = combinations[batch_start:batch_start + concurrency]
        tasks = [
            run_single(garment, model, batch_start + i, date_str)
            for i, (garment, model) in enumerate(batch)
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in batch_results:
            if isinstance(r, Exception):
                results.append({"status": "failed", "error": str(r)})
            else:
                results.append(r)

        done = len(results)
        logger.info(f"Progress: {done}/{len(combinations)}")

    # Summary
    success = sum(1 for r in results if r.get("status") == "complete")
    failed = sum(1 for r in results if r.get("status") == "failed")

    summary = {
        "date": date_str,
        "total": len(combinations),
        "success": success,
        "failed": failed,
        "results": results,
    }

    logger.info(f"=== Daily Pipeline Complete: {success}/{len(combinations)} succeeded ===")
    return summary


def run_daily():
    """Entry point for running from command line or scheduler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = asyncio.run(run_daily_pipeline())
    print(f"\nDone! {result.get('success', 0)}/{result.get('total', 0)} videos generated.")
    return result


if __name__ == "__main__":
    run_daily()
