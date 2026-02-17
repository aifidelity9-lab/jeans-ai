import asyncio
import logging
from pathlib import Path

import httpx
import replicate

from src.config import settings

logger = logging.getLogger(__name__)

KLING_MODEL = "kwaivgi/kling-v1.6-pro"


async def generate_video(
    image_path: str,
    prompt: str = "A fashion model walks naturally towards the camera, showing off her jeans, natural lighting, studio background",
    duration: int = 5,
    cfg_scale: float = 0.5,
) -> str:
    """Generate a video from a try-on image using Kling v1.6 Pro.

    Args:
        image_path: Local file path or URL of the input image.
        prompt: Text prompt describing the desired motion.
        duration: Video duration in seconds (5 or 10).
        cfg_scale: Prompt adherence (0-1). Lower = more creative.

    Returns:
        URL of the generated video.
    """
    loop = asyncio.get_event_loop()

    def _run():
        input_data = {
            "prompt": prompt,
            "duration": duration,
            "cfg_scale": cfg_scale,
            "negative_prompt": "blurry, distorted, ugly, deformed legs, extra limbs",
        }

        # Handle local file vs URL
        if image_path.startswith("http"):
            input_data["start_image"] = image_path
        else:
            input_data["start_image"] = open(image_path, "rb")

        return replicate.run(KLING_MODEL, input=input_data)

    output = await loop.run_in_executor(None, _run)
    result_url = str(output)
    logger.info(f"Video generated: {result_url}")
    return result_url


async def download_video(url: str, save_path: str) -> str:
    """Download a video from URL and save locally."""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
    logger.info(f"Video saved to {save_path}")
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
        List of dicts with image_path, video_url, local_path.
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

        tasks.append(generate_video(image_path=img_path, prompt=prompt))

    video_urls = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (img_path, result) in enumerate(zip(image_paths, video_urls)):
        if isinstance(result, Exception):
            logger.error(f"Video generation failed for {img_path}: {result}")
            results.append({"image_path": img_path, "error": str(result)})
            continue

        save_path = f"{output_dir}/video_{i:04d}.mp4"
        await download_video(result, save_path)
        results.append({
            "image_path": img_path,
            "video_url": result,
            "local_path": save_path,
        })

    return results
