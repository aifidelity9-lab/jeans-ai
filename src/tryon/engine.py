import asyncio
import logging
from pathlib import Path

import httpx
import replicate

from src.config import settings

logger = logging.getLogger(__name__)

IDMVTON_MODEL = "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"


async def run_tryon(
    human_img: str,
    garment_img: str,
    garment_desc: str = "Women's jeans",
    category: str = "lower_body",
    crop: bool = True,
    steps: int = 30,
    seed: int = 42,
) -> str:
    """Run virtual try-on via Replicate IDM-VTON.

    Args:
        human_img: URL or local path to the model (person) image.
        garment_img: URL or local path to the garment (jeans) image.
        garment_desc: Text description of the garment.
        category: "upper_body", "lower_body", or "dresses".
        crop: Whether to auto-crop the human image to 3:4 ratio.
        steps: Number of diffusion steps (20-40).
        seed: Random seed for reproducibility.

    Returns:
        URL of the generated try-on image.
    """
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(
        None,
        lambda: replicate.run(
            IDMVTON_MODEL,
            input={
                "human_img": human_img,
                "garm_img": garment_img,
                "garment_des": garment_desc,
                "category": category,
                "crop": crop,
                "steps": steps,
                "seed": seed,
            },
        ),
    )
    result_url = str(output)
    logger.info(f"Try-on complete: {result_url}")
    return result_url


async def download_image(url: str, save_path: str) -> str:
    """Download an image from URL and save locally."""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
    logger.info(f"Image saved to {save_path}")
    return save_path


async def batch_tryon(
    model_images: list[str],
    garment_img: str,
    garment_desc: str = "Women's jeans",
    output_dir: str = "output/tryon",
) -> list[dict]:
    """Run try-on for one garment across multiple model images.

    Args:
        model_images: List of URLs to model (person) images.
        garment_img: URL to the garment image.
        garment_desc: Text description of the garment.
        output_dir: Directory to save results.

    Returns:
        List of dicts with model_img, result_url, local_path.
    """
    results = []
    tasks = []

    for i, human_img in enumerate(model_images):
        tasks.append(run_tryon(
            human_img=human_img,
            garment_img=garment_img,
            garment_desc=garment_desc,
        ))

    # Run concurrently (Replicate handles queuing)
    tryon_urls = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (human_img, result) in enumerate(zip(model_images, tryon_urls)):
        if isinstance(result, Exception):
            logger.error(f"Try-on failed for model {i}: {result}")
            results.append({"model_img": human_img, "error": str(result)})
            continue

        save_path = f"{output_dir}/tryon_{i:04d}.png"
        await download_image(result, save_path)
        results.append({
            "model_img": human_img,
            "result_url": result,
            "local_path": save_path,
        })

    return results
