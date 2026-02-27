"""Test full pipeline: one garment + one model -> try-on -> video -> final."""

import asyncio
import time
from pathlib import Path

from src.tryon.engine import run_tryon
from src.video.generator import generate_video


async def main():
    model = "assets/models/jeans/5.png"
    garment = "assets/products/jeans/5.png"
    output_dir = "output/test_pipeline"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Stage 1: Try-on
    print(f"[Stage 1] Try-on: {model} + {garment}", flush=True)
    t0 = time.time()
    tryon_path = await run_tryon(
        human_img=model,
        garment_img=garment,
        garment_desc="Women's embroidered floral denim jeans",
        category="lower_body",
        output_dir=output_dir,
    )
    print(f"  Done in {time.time()-t0:.1f}s -> {tryon_path}", flush=True)

    # Stage 2: Video generation (Veo)
    print(f"[Stage 2] Video generation from try-on image...", flush=True)
    t1 = time.time()
    video_path = await generate_video(
        image_path=tryon_path,
        prompt="A fashion model walks naturally towards the camera, showing off her jeans, confident stride, studio lighting",
        duration=5,
        output_dir=output_dir,
    )
    print(f"  Done in {time.time()-t1:.1f}s -> {video_path}", flush=True)

    total = time.time() - t0
    print(f"\nTotal: {total:.0f}s ({total/60:.1f} min)")
    print(f"Try-on image: {tryon_path}")
    print(f"Video: {video_path}")


if __name__ == "__main__":
    asyncio.run(main())
