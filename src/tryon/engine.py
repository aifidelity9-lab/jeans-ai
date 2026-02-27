import asyncio
import io
import logging
import shutil
import uuid
from pathlib import Path

import numpy as np
import httpx
from PIL import Image
from google import genai
from google.genai import types as genai_types

from src.config import settings

logger = logging.getLogger(__name__)


class TryOnEngine:
    """Virtual try-on engine using Google Gemini Image API."""

    DEFAULT_MODEL = "gemini-2.5-flash-image"
    TARGET_RATIO = 3 / 2  # h/w = 1.5
    TARGET_WIDTH = 768
    TARGET_HEIGHT = 1152

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        target_width: int = TARGET_WIDTH,
        target_height: int = TARGET_HEIGHT,
    ):
        self._api_key = api_key or settings.gemini_api_key
        self.model = model
        self.target_width = target_width
        self.target_height = target_height
        self.target_ratio = target_height / target_width
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    # ── Image loading ────────────────────────────────────────────

    @staticmethod
    async def load_image(source: str) -> Image.Image:
        """Load an image from a URL or local file path."""
        if source.startswith("http"):
            async with httpx.AsyncClient() as http:
                resp = await http.get(source, follow_redirects=True)
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content))
        return Image.open(source)

    @staticmethod
    async def download(url_or_path: str, save_path: str) -> str:
        """Download from URL or copy local file to save_path."""
        if url_or_path.startswith("http"):
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient() as http:
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

    # ── Image preprocessing ──────────────────────────────────────

    def prepare_model_image(self, img: Image.Image) -> Image.Image:
        """Standardize to portrait ratio with padding for full-body framing."""
        img = img.convert("RGB")
        w, h = img.size
        ratio = h / w
        tw, th = self.target_width, self.target_height

        if ratio > self.target_ratio:
            new_h = th
            new_w = int(new_h / ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            canvas = Image.new("RGB", (tw, th), self._bg_color(img))
            canvas.paste(img, ((tw - new_w) // 2, 0))
            img = canvas
        elif ratio < self.target_ratio:
            new_w = tw
            new_h = int(new_w * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            canvas = Image.new("RGB", (tw, th), self._bg_color(img))
            canvas.paste(img, (0, (th - new_h) // 2))
            img = canvas
        else:
            img = img.resize((tw, th), Image.LANCZOS)

        # Extra breathing room (10% top/bottom)
        pad = int(th * 0.10)
        bg = self._bg_color(img)
        padded = Image.new("RGB", (tw, th + pad * 2), bg)
        padded.paste(img, (0, pad))
        return padded

    @staticmethod
    def auto_crop(img: Image.Image) -> Image.Image:
        """Trim uniform-color borders from generated image."""
        arr = np.array(img)
        h, w = arr.shape[:2]

        def _find_edge(axis_arr, reverse=False):
            edge_color = axis_arr[-1].astype(float) if reverse else axis_arr[0].astype(float)
            rng = range(len(axis_arr) - 1, -1, -1) if reverse else range(len(axis_arr))
            for i in rng:
                diff = np.mean(np.abs(axis_arr[i].astype(float) - edge_color))
                if diff > 15:
                    return max(0, i - 3) if not reverse else min(len(axis_arr), i + 3)
            return 0 if not reverse else len(axis_arr)

        top = _find_edge(arr[:, w // 4: w * 3 // 4].mean(axis=1))
        bottom = _find_edge(arr[:, w // 4: w * 3 // 4].mean(axis=1), reverse=True)
        left = _find_edge(arr[h // 4: h * 3 // 4].mean(axis=0))
        right = _find_edge(arr[h // 4: h * 3 // 4].mean(axis=0), reverse=True)

        if right - left > w * 0.5 and bottom - top > h * 0.5:
            img = img.crop((left, top, right, bottom))
        return img

    @staticmethod
    def _bg_color(img: Image.Image) -> tuple:
        w, h = img.size
        samples = [
            img.getpixel((w // 2, 2)),
            img.getpixel((w // 2, h - 3)),
            img.getpixel((2, h // 2)),
            img.getpixel((w - 3, h // 2)),
        ]
        return tuple(sum(s[c] for s in samples) // 4 for c in range(3))

    # ── Prompt building ──────────────────────────────────────────

    @staticmethod
    def build_prompt(garment_desc: str, category: str) -> str:
        """Build try-on prompt based on garment category."""
        if category == "upper_body":
            return (
                f"Edit the first image: replace the person's upper body clothing with the "
                f"EXACT garment from the second image ({garment_desc}).\n\n"
                f"CRITICAL REQUIREMENTS:\n"
                f"- Output a FULL BODY photo: head to toe, whole body visible\n"
                f"- Match the garment's exact color, pattern, print, neckline, and sleeve style "
                f"from the second image\n"
                f"- The garment must fit naturally on the torso, following shoulder and chest contours\n"
                f"- Keep face, hair, pose, lower body clothing, shoes, and background identical\n\n"
                f"AVOID: cropped, cut off, half body, close-up, "
                f"wrong color, wrong pattern, floating, bad anatomy"
            )
        elif category == "dresses":
            return (
                f"Edit the first image: replace the person's entire outfit with the "
                f"EXACT dress from the second image ({garment_desc}).\n\n"
                f"CRITICAL REQUIREMENTS:\n"
                f"- Output a FULL BODY photo: head to toe, whole body visible\n"
                f"- Match the dress's exact color, pattern, length, and style from the second image\n"
                f"- The dress must fit naturally on the body\n"
                f"- Keep face, hair, pose, shoes, and background identical\n\n"
                f"AVOID: cropped, cut off, half body, close-up, "
                f"wrong color, wrong pattern, floating, bad anatomy"
            )
        else:
            return (
                f"Edit the first image: replace the person's lower body (pants/jeans/skirt area) "
                f"clothing with the EXACT garment from the second image ({garment_desc}).\n\n"
                f"CRITICAL REQUIREMENTS:\n"
                f"- Output a FULL BODY photo: head to toe, whole body, complete legs, "
                f"feet visible, shoes visible, floor visible\n"
                f"- Standing pose, full shot, the person must be completely visible\n"
                f"- Match the garment's exact color, texture, pattern, and style from the second image\n"
                f"- The garment must fit naturally on the body, following leg contours\n"
                f"- Keep face, hair, pose, upper body clothing, shoes, and background identical\n\n"
                f"AVOID: cropped, cut off, half body, upper body only, close-up, "
                f"cropped legs, cropped feet, missing feet, floating, bad anatomy"
            )

    # ── Core try-on ──────────────────────────────────────────────

    async def run(
        self,
        human_img: str,
        garment_img: str,
        garment_desc: str = "Women's jeans",
        category: str = "lower_body",
        output_dir: str = "output/tryon",
    ) -> str:
        """Run virtual try-on. Returns local path to generated image."""
        human_pil, garment_pil = await asyncio.gather(
            self.load_image(human_img),
            self.load_image(garment_img),
        )

        human_pil = self.prepare_model_image(human_pil)
        prompt = self.build_prompt(garment_desc, category)

        loop = asyncio.get_event_loop()
        client = self.client

        def _call():
            return client.models.generate_content(
                model=self.model,
                contents=[prompt, human_pil, garment_pil],
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

        response = await loop.run_in_executor(None, _call)

        result_image = None
        for part in response.parts:
            if part.inline_data:
                result_image = Image.open(io.BytesIO(part.inline_data.data))
                break

        if result_image is None:
            text_parts = [p.text for p in response.parts if hasattr(p, "text") and p.text]
            raise RuntimeError(f"Gemini try-on failed: {'; '.join(text_parts) or 'No image'}")

        result_image = self.auto_crop(result_image)

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filename = f"tryon_{uuid.uuid4().hex[:12]}.png"
        save_path = str(Path(output_dir) / filename)
        result_image.save(save_path)

        logger.info(f"Try-on complete: {save_path}")
        return save_path

    async def batch_run(
        self,
        model_images: list[str],
        garment_img: str,
        garment_desc: str = "Women's jeans",
        category: str = "lower_body",
        output_dir: str = "output/tryon",
    ) -> list[dict]:
        """Run try-on for one garment across multiple models."""
        tasks = [
            self.run(human_img=img, garment_img=garment_img,
                     garment_desc=garment_desc, category=category,
                     output_dir=output_dir)
            for img in model_images
        ]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, (img, result) in enumerate(zip(model_images, results_raw)):
            if isinstance(result, Exception):
                logger.error(f"Try-on failed for model {i}: {result}")
                results.append({"model_img": img, "error": str(result)})
            else:
                save_path = f"{output_dir}/tryon_{i:04d}.png"
                await self.download(result, save_path)
                results.append({"model_img": img, "result_path": save_path})
        return results


# ── Default singleton for backward compatibility ─────────────────
_default_engine: TryOnEngine | None = None


def get_engine() -> TryOnEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = TryOnEngine()
    return _default_engine


# ── Backward-compatible module-level functions ───────────────────
async def run_tryon(**kwargs) -> str:
    return await get_engine().run(**kwargs)


async def download_image(url_or_path: str, save_path: str) -> str:
    return await TryOnEngine.download(url_or_path, save_path)


async def batch_tryon(**kwargs) -> list[dict]:
    return await get_engine().batch_run(**kwargs)
