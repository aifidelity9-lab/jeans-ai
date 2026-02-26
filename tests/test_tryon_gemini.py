"""Quick integration test for Gemini-based virtual try-on."""

import asyncio
import time
from pathlib import Path

from src.tryon.engine import run_tryon, _load_image, _get_client, _build_tryon_prompt
from google.genai import types as genai_types


async def test_single_tryon():
    """Test a single try-on with real assets, with step-by-step logging."""
    human_img = "assets/models/2.png"
    garment_img = "assets/products/jeans-1.jpg"
    output_dir = "output/test_gemini"

    # Step 1: Load images
    print(f"[1/4] Loading images...")
    t0 = time.time()
    human_pil = await _load_image(human_img)
    garment_pil = await _load_image(garment_img)
    print(f"       Done in {time.time()-t0:.1f}s  (human: {human_pil.size}, garment: {garment_pil.size})")

    # Step 2: Build prompt
    prompt = _build_tryon_prompt("Women's blue denim jeans", "lower_body")
    print(f"[2/4] Prompt: {prompt[:80]}...")

    # Step 3: Call Gemini API (this is the slow part)
    print(f"[3/4] Calling Gemini API (timeout 120s)...")
    t1 = time.time()
    client = _get_client()

    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=[prompt, human_pil, garment_pil],
                    config=genai_types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                ),
            ),
            timeout=120,
        )
        print(f"       API responded in {time.time()-t1:.1f}s")
    except asyncio.TimeoutError:
        print(f"       TIMEOUT after {time.time()-t1:.1f}s - API did not respond within 120s")
        print("       This is likely a network issue (proxy/firewall blocking long connections)")
        return

    # Step 4: Extract image
    print(f"[4/4] Extracting result image...")
    result_image = None
    for part in response.parts:
        if part.inline_data:
            result_image = part.as_image()
            break

    if result_image is None:
        text_parts = [p.text for p in response.parts if hasattr(p, "text") and p.text]
        print(f"       ERROR: No image returned. Text: {text_parts}")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    save_path = f"{output_dir}/test_result.png"
    result_image.save(save_path)
    print(f"       Saved to: {save_path} ({result_image.size})")
    print("SUCCESS!")


if __name__ == "__main__":
    asyncio.run(test_single_tryon())
