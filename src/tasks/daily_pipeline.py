"""Daily automated pipeline: generates try-on videos for all active products x models."""

import asyncio
import logging
from datetime import datetime
from itertools import product as cartesian
from pathlib import Path

from src.categories import GarmentCategory, get_category, JEANS
from src.tryon.engine import TryOnEngine
from src.video.generator import VideoGenerator
from src.editor.composer import VideoComposer

logger = logging.getLogger(__name__)


class Pipeline:
    """Full pipeline: try-on -> video -> compose."""

    def __init__(
        self,
        tryon_engine: TryOnEngine | None = None,
        video_generator: VideoGenerator | None = None,
        composer: VideoComposer | None = None,
        max_retries: int = 3,
    ):
        self.tryon = tryon_engine or TryOnEngine()
        self.video = video_generator or VideoGenerator()
        self.composer = composer or VideoComposer()
        self.max_retries = max_retries

    async def run_single(
        self,
        garment_path: str,
        model_path: str,
        index: int,
        output_base: str,
        category: GarmentCategory = JEANS,
    ) -> dict:
        """Run full pipeline for one garment x one model combination."""
        result = {
            "garment": garment_path,
            "model": model_path,
            "index": index,
            "category": category.name,
            "status": "started",
        }

        for attempt in range(self.max_retries):
            try:
                # Stage 1: Try-on
                logger.info(f"[{index}] Stage 1: Try-on {Path(garment_path).name} x {Path(model_path).name}")
                tryon_path = await self.tryon.run(
                    human_img=model_path,
                    garment_img=garment_path,
                    garment_desc=category.garment_desc,
                    category=category.tryon_category,
                    output_dir=f"{output_base}/tryon",
                )
                result["tryon"] = tryon_path

                # Stage 2: Video generation
                logger.info(f"[{index}] Stage 2: Video generation")
                prompt = category.get_video_prompt(index)
                video_path = await self.video.generate(
                    image_path=tryon_path, prompt=prompt,
                    output_dir=f"{output_base}/videos",
                )
                result["video"] = video_path

                # Stage 3: Compose final video
                logger.info(f"[{index}] Stage 3: Composing final video")
                caption = category.get_caption(index)
                final_path = self.composer.compose(
                    video_clips=[video_path],
                    output_path=f"{output_base}/final/final_{index:04d}.mp4",
                    caption=caption,
                )
                result["final"] = final_path
                result["status"] = "complete"
                logger.info(f"[{index}] Complete: {final_path}")
                break

            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < self.max_retries - 1:
                    wait = 15 * (attempt + 1)
                    logger.warning(f"[{index}] Rate limited, retrying in {wait}s... (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                result["status"] = "failed"
                result["error"] = error_str
                logger.error(f"[{index}] Failed: {e}")

        return result

    async def run_batch(
        self,
        category: GarmentCategory,
        max_videos: int = 100,
        concurrency: int = 3,
    ) -> dict:
        """Run full pipeline for all product x model combinations in a category."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_base = f"output/{date_str}"
        logger.info(f"=== Pipeline Started: {date_str} ({category.name}) ===")

        products = category.get_product_images()
        models = category.get_model_images()

        if not products:
            return {"error": f"No product images found in {category.products_dir}"}
        if not models:
            return {"error": f"No model images found in {category.models_dir}"}

        combinations = list(cartesian(products, models))[:max_videos]
        logger.info(f"Total combinations: {len(combinations)} (capped at {max_videos})")

        results = []
        for batch_start in range(0, len(combinations), concurrency):
            batch = combinations[batch_start:batch_start + concurrency]
            tasks = [
                self.run_single(garment, model, batch_start + i, output_base, category)
                for i, (garment, model) in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in batch_results:
                if isinstance(r, Exception):
                    results.append({"status": "failed", "error": str(r)})
                else:
                    results.append(r)

            logger.info(f"Progress: {len(results)}/{len(combinations)}")

        success = sum(1 for r in results if r.get("status") == "complete")
        failed = sum(1 for r in results if r.get("status") == "failed")

        summary = {
            "date": date_str,
            "category": category.name,
            "total": len(combinations),
            "success": success,
            "failed": failed,
            "results": results,
        }
        logger.info(f"=== Pipeline Complete: {success}/{len(combinations)} succeeded ===")
        return summary


# ── Convenience functions (backward compatible) ──────────────────

async def run_daily_pipeline(
    max_videos: int = 100,
    concurrency: int = 3,
    category_name: str = "jeans",
) -> dict:
    cat = get_category(category_name)
    pipeline = Pipeline()
    return await pipeline.run_batch(cat, max_videos=max_videos, concurrency=concurrency)


def run_daily():
    """Entry point for command line or scheduler."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = asyncio.run(run_daily_pipeline())
    print(f"\nDone! {result.get('success', 0)}/{result.get('total', 0)} videos generated.")
    return result


if __name__ == "__main__":
    run_daily()
