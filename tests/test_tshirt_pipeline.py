"""Test T-shirt full pipeline: one T-shirt + one model -> try-on -> video."""

import asyncio
import time
from pathlib import Path

from src.tryon.engine import run_tryon
from src.video.generator import generate_video


async def main():
    model = "assets/models/tshirts/5.png"  # will need tshirt-specific models
    output_dir = "output/test_tshirt"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Check for tshirt images
    tshirt_dir = Path("assets/products/tshirts")
    if not tshirt_dir.exists() or not any(tshirt_dir.iterdir()):
        print("No T-shirt images found in assets/products/tshirts/")
        print("Please add at least one T-shirt product image first.")
        return

    garment = str(sorted(tshirt_dir.iterdir())[0])
    print(f"Using T-shirt: {garment}")
    print(f"Using model: {model}")

    # Stage 1: Try-on
    print(f"\n[Stage 1] T-shirt try-on...", flush=True)
    t0 = time.time()
    tryon_path = await run_tryon(
        human_img=model,
        garment_img=garment,
        garment_desc="Women's T-shirt",
        category="upper_body",
        output_dir=output_dir,
    )
    print(f"  Done in {time.time()-t0:.1f}s -> {tryon_path}", flush=True)

    # Stage 2: Video generation (Veo)
    print(f"[Stage 2] Video generation from try-on image...", flush=True)
    t1 = time.time()
    video_path = await generate_video(
        image_path=tryon_path,
        prompt="A fashion model walks naturally towards the camera, showing off her T-shirt, confident stride, studio lighting",
        output_dir=output_dir,
    )
    print(f"  Done in {time.time()-t1:.1f}s -> {video_path}", flush=True)

    total = time.time() - t0
    print(f"\nTotal: {total:.0f}s ({total/60:.1f} min)")
    print(f"Try-on image: {tryon_path}")
    print(f"Video: {video_path}")


if __name__ == "__main__":
    asyncio.run(main())
