import asyncio
import logging
import shutil
import time
import uuid
from pathlib import Path

import httpx
from google import genai
from google.genai import types as genai_types

from src.config import settings

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Video generation engine using Google Veo API."""

    DEFAULT_MODEL = "veo-3.1-fast-generate-preview"
    DEFAULT_ASPECT_RATIO = "9:16"
    DEFAULT_DURATION = 8  # Veo requires 8s when using reference image

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        duration: int = DEFAULT_DURATION,
    ):
        self._api_key = api_key or settings.gemini_api_key
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.duration = duration
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    # ── File helpers ─────────────────────────────────────────────

    @staticmethod
    async def download(url_or_path: str, save_path: str) -> str:
        """Download from URL or copy local file to save_path."""
        if url_or_path.startswith("http"):
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(timeout=120) as http:
                resp = await http.get(url_or_path, follow_redirects=True)
                resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(resp.content)
            return save_path
        source = Path(url_or_path)
        target = Path(save_path)
        if source.resolve() == target.resolve():
            return save_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))
        return save_path

    # ── Core video generation ────────────────────────────────────

    async def generate(
        self,
        image_path: str,
        prompt: str = "A fashion model walks naturally towards the camera, showing off her outfit, natural lighting, studio background",
        output_dir: str = "output/videos",
    ) -> str:
        """Generate a video from a try-on image. Returns local path to video."""
        # Load image bytes
        if image_path.startswith("http"):
            async with httpx.AsyncClient() as http:
                resp = await http.get(image_path, follow_redirects=True)
                resp.raise_for_status()
                image_bytes = resp.content
        else:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        image = genai_types.Image(image_bytes=image_bytes, mime_type=mime_type)

        client = self.client
        loop = asyncio.get_event_loop()

        def _start():
            return client.models.generate_videos(
                model=self.model,
                prompt=prompt,
                image=image,
                config=genai_types.GenerateVideosConfig(
                    aspect_ratio=self.aspect_ratio,
                    duration_seconds=self.duration,
                    negative_prompt="blurry, distorted, ugly, deformed legs, extra limbs",
                ),
            )

        logger.info(f"Starting Veo video generation ({self.duration}s)...")
        operation = await loop.run_in_executor(None, _start)

        def _poll():
            op = operation
            while not op.done:
                time.sleep(5)
                op = client.operations.get(op)
            return op

        logger.info("Waiting for video generation to complete...")
        result_op = await loop.run_in_executor(None, _poll)

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

    async def batch_generate(
        self,
        image_paths: list[str],
        prompts: list[str] | None = None,
        output_dir: str = "output/videos",
    ) -> list[dict]:
        """Generate videos from multiple images."""
        default_prompts = [
            "A fashion model walks confidently towards the camera, showing off her outfit, studio lighting",
            "A woman turns slowly to show her outfit from different angles, natural movement, clean background",
            "A model poses naturally, shifting weight, showing the fit of her outfit, soft lighting",
            "A woman walks along a street, casual confident stride, showing her outfit, natural daylight",
            "A fashion model does a slow spin to show the full outfit, studio background, professional lighting",
        ]

        tasks = []
        for i, img_path in enumerate(image_paths):
            prompt = prompts[i] if prompts and i < len(prompts) else default_prompts[i % len(default_prompts)]
            tasks.append(self.generate(image_path=img_path, prompt=prompt, output_dir=output_dir))

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, (img_path, result) in enumerate(zip(image_paths, raw_results)):
            if isinstance(result, Exception):
                logger.error(f"Video generation failed for {img_path}: {result}")
                results.append({"image_path": img_path, "error": str(result)})
            else:
                save_path = f"{output_dir}/video_{i:04d}.mp4"
                await self.download(result, save_path)
                results.append({"image_path": img_path, "video_path": result, "local_path": save_path})
        return results


# ── Default singleton for backward compatibility ─────────────────
_default_generator: VideoGenerator | None = None


def get_generator() -> VideoGenerator:
    global _default_generator
    if _default_generator is None:
        _default_generator = VideoGenerator()
    return _default_generator


# ── Backward-compatible module-level functions ───────────────────
async def generate_video(image_path: str, prompt: str = "A fashion model walks naturally towards the camera, showing off her outfit, natural lighting, studio background", output_dir: str = "output/videos", **kwargs) -> str:
    return await get_generator().generate(image_path=image_path, prompt=prompt, output_dir=output_dir)


async def download_video(url_or_path: str, save_path: str) -> str:
    return await VideoGenerator.download(url_or_path, save_path)


async def batch_generate_videos(**kwargs) -> list[dict]:
    return await get_generator().batch_generate(**kwargs)
