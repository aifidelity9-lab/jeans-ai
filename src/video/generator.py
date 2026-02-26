import asyncio
import logging
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image as PILImage
from google import genai
from google.genai import types as genai_types

from src.config import settings

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-3.1-fast-generate-preview"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def generate_video(
    image_path: str,
    prompt: str = "A fashion model walks naturally towards the camera, showing off her jeans, natural lighting, studio background",
    duration: int = 5,
    cfg_scale: float = 0.5,
    output_dir: str = "output/videos",
) -> str:
    """Generate a video from a try-on image using Google Veo.

    Args:
        image_path: Local file path or URL of the input image.
        prompt: Text prompt describing the desired motion.
        duration: Video duration in seconds (4, 6, or 8).
        cfg_scale: Legacy param (unused with Veo), kept for compatibility.
        output_dir: Directory to save the generated video.

    Returns:
        Local file path to the generated video.
    """
    # Load input image
    if image_path.startswith("http"):
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(image_path, follow_redirects=True)
            resp.raise_for_status()
            import io
            image = PILImage.open(io.BytesIO(resp.content))
    else:
        image = PILImage.open(image_path)

    # Map duration to nearest Veo-supported value
    veo_duration = str(min(8, max(4, duration)))

    client = _get_client()
    loop = asyncio.get_event_loop()

    # Start video generation (async operation)
    def _start():
        return client.models.generate_videos(
            model=VEO_MODEL,
            prompt=prompt,
            image=image,
            config=genai_types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=veo_duration,
                negative_prompt="blurry, distorted, ugly, deformed legs, extra limbs",
            ),
        )

    logger.info(f"Starting Veo video generation ({veo_duration}s)...")
    operation = await loop.run_in_executor(None, _start)

    # Poll until done
    def _poll():
        op = operation
        while not op.done:
            time.sleep(5)
            op = client.operations.get(op)
        return op

    logger.info("Waiting for video generation to complete...")
    result_op = await loop.run_in_executor(None, _poll)

    # Save the video locally
    generated_video = result_op.response.generated_videos[0]

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"video_{uuid.uuid4().hex[:12]}.mp4"
    save_path = str(Path(output_dir) / filename)

    def _save():
        client.files.download(file=generated_video.video)
        generated_video.video.save(save_path)

    await loop.run_in_executor(None, _save)

    logger.info(f"Video saved to {save_path}")
    return save_path


async def download_video(url_or_path: str, save_path: str) -> str:
    """Download a video from URL, or copy a local file to save_path."""
    if url_or_path.startswith("http"):
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(url_or_path, follow_redirects=True)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
        logger.info(f"Video downloaded to {save_path}")
        return save_path
    else:
        import shutil
        source = Path(url_or_path)
        target = Path(save_path)
        if source.resolve() == target.resolve():
            return save_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))
        logger.info(f"Video copied to {save_path}")
        return save_path


async def batch_generate_videos(
    image_paths: list[str],
    prompts: list[str] | None = None,
    output_dir: str = "output/videos",
) -> list[dict]:
    """Generate videos from multiple try-on images.

    Args:
        image_paths: List of local paths or URLs to try-on images.
        prompts: Optional list of prompts (one per image). Uses default if None.
        output_dir: Directory to save results.

    Returns:
        List of dicts with image_path, video_path, local_path.
    """
    default_prompts = [
        "A fashion model walks confidently towards the camera, showing off her jeans, studio lighting",
        "A woman turns slowly to show her outfit from different angles, natural movement, clean background",
        "A model poses naturally, shifting weight between legs, showing the fit of her jeans, soft lighting",
        "A woman walks along a street, casual confident stride, showing her denim jeans, natural daylight",
        "A fashion model does a slow spin to show the full outfit, studio background, professional lighting",
    ]

    results = []
    tasks = []

    for i, img_path in enumerate(image_paths):
        if prompts and i < len(prompts):
            prompt = prompts[i]
        else:
            prompt = default_prompts[i % len(default_prompts)]

        tasks.append(generate_video(image_path=img_path, prompt=prompt, output_dir=output_dir))

    video_results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (img_path, result) in enumerate(zip(image_paths, video_results)):
        if isinstance(result, Exception):
            logger.error(f"Video generation failed for {img_path}: {result}")
            results.append({"image_path": img_path, "error": str(result)})
            continue

        save_path = f"{output_dir}/video_{i:04d}.mp4"
        await download_video(result, save_path)
        results.append({
            "image_path": img_path,
            "video_path": result,
            "local_path": save_path,
        })

    return results
