"""Test single try-on: one garment + one model → one image."""

import asyncio
import time
from pathlib import Path

from src.tryon.engine import run_tryon


async def main():
    garment = "assets/products/jeans-1.jpg"
    model = "assets/models/2.png"
    output_dir = "output/test_single"

    print(f"Garment: {garment}")
    print(f"Model:   {model}")
    print("Generating try-on image...")

    t0 = time.time()
    result = await run_tryon(
        human_img=model,
        garment_img=garment,
        garment_desc="Women's blue denim jeans",
        category="lower_body",
        output_dir=output_dir,
    )
    elapsed = time.time() - t0

    print(f"Done in {elapsed:.1f}s")
    print(f"Result: {result}")
    print(f"File size: {Path(result).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    asyncio.run(main())
