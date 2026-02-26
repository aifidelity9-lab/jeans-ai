import asyncio
import io
import logging
import shutil
import uuid
from pathlib import Path

import httpx
from PIL import Image
from google import genai
from google.genai import types as genai_types

from src.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-pro-image-preview"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def _load_image(source: str) -> Image.Image:
    """Load an image from a URL or local file path into a PIL Image."""
    if source.startswith("http"):
        async with httpx.AsyncClient() as client:
            resp = await client.get(source, follow_redirects=True)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content))
    else:
        return Image.open(source)


def _build_tryon_prompt(garment_desc: str, category: str) -> str:
    """Build a virtual try-on prompt for Gemini Image."""
    category_map = {
        "lower_body": "lower body (pants/jeans/skirt area)",
        "upper_body": "upper body (shirt/top/jacket area)",
        "dresses": "full body (dress)",
    }
    region = category_map.get(category, category)

    return (
        f"Virtual try-on: Replace the {region} clothing on the person in the first image "
        f"with the garment shown in the second image. The garment is: {garment_desc}. "
        f"Keep the person's pose, body shape, face, and background exactly the same. "
        f"Only change the {region} clothing to match the provided garment. "
        f"The result should look like a realistic photo of the person wearing this garment."
    )


async def run_tryon(
    human_img: str,
    garment_img: str,
    garment_desc: str = "Women's jeans",
    category: str = "lower_body",
    crop: bool = True,
    steps: int = 30,
    seed: int = 42,
    output_dir: str = "output/tryon",
) -> str:
    """Run virtual try-on via Google Gemini Image (Nano Banana Pro).

    Args:
        human_img: URL or local path to the model (person) image.
        garment_img: URL or local path to the garment (jeans) image.
        garment_desc: Text description of the garment.
        category: "upper_body", "lower_body", or "dresses".
        crop: Legacy param (unused with Gemini), kept for compatibility.
        steps: Legacy param (unused with Gemini), kept for compatibility.
        seed: Legacy param (unused with Gemini), kept for compatibility.
        output_dir: Directory to save the generated image.

    Returns:
        Local file path to the generated try-on image.
    """
    # Load both images as PIL concurrently
    human_pil, garment_pil = await asyncio.gather(
        _load_image(human_img),
        _load_image(garment_img),
    )

    prompt = _build_tryon_prompt(garment_desc, category)
    client = _get_client()

    # Gemini SDK is synchronous, run in executor
    loop = asyncio.get_event_loop()

    def _call_gemini():
        return client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, human_pil, garment_pil],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

    response = await loop.run_in_executor(None, _call_gemini)

    # Extract generated image from response
    result_image = None
    for part in response.parts:
        if part.inline_data:
            result_image = Image.open(io.BytesIO(part.inline_data.data))
            break

    if result_image is None:
        text_parts = [p.text for p in response.parts if hasattr(p, "text") and p.text]
        error_detail = "; ".join(text_parts) if text_parts else "No image in response"
        raise RuntimeError(f"Gemini try-on failed: {error_detail}")

    # Save result locally
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"tryon_{uuid.uuid4().hex[:12]}.png"
    save_path = str(Path(output_dir) / filename)
    result_image.save(save_path)

    logger.info(f"Try-on complete: {save_path}")
    return save_path


async def download_image(url_or_path: str, save_path: str) -> str:
    """Download an image from URL, or copy a local file to save_path.

    Handles both URLs (original behavior) and local file paths
    (for compatibility with Gemini engine which returns local paths).
    """
    if url_or_path.startswith("http"):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url_or_path, follow_redirects=True)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
        logger.info(f"Image downloaded to {save_path}")
        return save_path
    else:
        source = Path(url_or_path)
        target = Path(save_path)
        if source.resolve() == target.resolve():
            return save_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))
        logger.info(f"Image copied to {save_path}")
        return save_path


async def batch_tryon(
    model_images: list[str],
    garment_img: str,
    garment_desc: str = "Women's jeans",
    output_dir: str = "output/tryon",
) -> list[dict]:
    """Run try-on for one garment across multiple model images.

    Args:
        model_images: List of URLs or local paths to model (person) images.
        garment_img: URL or local path to the garment image.
        garment_desc: Text description of the garment.
        output_dir: Directory to save results.

    Returns:
        List of dicts with model_img, result_path, local_path.
    """
    results = []
    tasks = []

    for i, human_img in enumerate(model_images):
        tasks.append(run_tryon(
            human_img=human_img,
            garment_img=garment_img,
            garment_desc=garment_desc,
            output_dir=output_dir,
        ))

    tryon_results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (human_img, result) in enumerate(zip(model_images, tryon_results)):
        if isinstance(result, Exception):
            logger.error(f"Try-on failed for model {i}: {result}")
            results.append({"model_img": human_img, "error": str(result)})
            continue

        save_path = f"{output_dir}/tryon_{i:04d}.png"
        await download_image(result, save_path)
        results.append({
            "model_img": human_img,
            "result_path": save_path,
            "local_path": save_path,
        })

    return results
