"""Batch full pipeline: all products x all models -> try-on -> video."""

import asyncio
import time
from itertools import product as cartesian
from pathlib import Path

from src.tryon.engine import run_tryon
from src.video.generator import generate_video

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_images(directory: str) -> list[str]:
    p = Path(directory)
    return sorted(
        str(f) for f in p.iterdir()
        if f.suffix.lower() in VALID_EXTENSIONS
    )


async def run_single(garment: str, model: str, index: int, output_dir: str) -> dict:
    g_name = Path(garment).stem
    m_name = Path(model).stem
    label = f"{g_name} x {m_name}"

    # Stage 1: Try-on
    try:
        t0 = time.time()
        tryon_path = await run_tryon(
            human_img=model,
            garment_img=garment,
            garment_desc="Women's denim jeans",
            category="lower_body",
            output_dir=f"{output_dir}/tryon",
        )
        t_tryon = time.time() - t0
        print(f"  [{index:02d}] TRYON OK  {label}  ({t_tryon:.1f}s)", flush=True)
    except Exception as e:
        print(f"  [{index:02d}] TRYON FAIL {label}  ({e})", flush=True)
        return {"status": "tryon_fail", "label": label, "error": str(e)}

    # Stage 2: Video generation
    try:
        t1 = time.time()
        video_path = await generate_video(
            image_path=tryon_path,
            prompt="A fashion model walks naturally towards the camera, showing off her jeans, confident stride, studio lighting",
            output_dir=f"{output_dir}/videos",
        )
        t_video = time.time() - t1
        total = time.time() - t0
        print(f"  [{index:02d}] VIDEO OK  {label}  (video {t_video:.1f}s, total {total:.1f}s)", flush=True)
        return {
            "status": "ok",
            "label": label,
            "tryon": tryon_path,
            "video": video_path,
        }
    except Exception as e:
        print(f"  [{index:02d}] VIDEO FAIL {label}  ({e})", flush=True)
        return {
            "status": "video_fail",
            "label": label,
            "tryon": tryon_path,
            "error": str(e),
        }


async def main():
    products = get_images("assets/products/jeans")
    models = get_images("assets/models/jeans")

    print(f"Products: {len(products)}")
    print(f"Models:   {len(models)}")

    combos = list(cartesian(products, models))
    total = len(combos)
    print(f"Total combinations: {total}")
    print(f"Estimated time: ~{total * 60 // 60} min (at ~60s each)\n")

    output_dir = "output/batch_full"
    Path(f"{output_dir}/tryon").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/videos").mkdir(parents=True, exist_ok=True)

    concurrency = 2
    ok = 0
    tryon_fail = 0
    video_fail = 0
    t_start = time.time()

    for batch_start in range(0, total, concurrency):
        batch = combos[batch_start:batch_start + concurrency]
        tasks = [
            run_single(g, m, batch_start + i, output_dir)
            for i, (g, m) in enumerate(batch)
        ]
        results = await asyncio.gather(*tasks)
        for r in results:
            if r["status"] == "ok":
                ok += 1
            elif r["status"] == "tryon_fail":
                tryon_fail += 1
            else:
                video_fail += 1

        done = batch_start + len(batch)
        elapsed = time.time() - t_start
        avg = elapsed / done
        remaining = avg * (total - done)
        print(
            f"  Progress: {done}/{total}  "
            f"(ok={ok} tryon_fail={tryon_fail} video_fail={video_fail})  "
            f"~{remaining / 60:.0f} min remaining\n",
            flush=True,
        )

    elapsed_total = time.time() - t_start
    print(f"\nDone! {ok}/{total} full pipeline OK")
    print(f"  Try-on failures: {tryon_fail}")
    print(f"  Video failures:  {video_fail}")
    print(f"Total time: {elapsed_total:.0f}s ({elapsed_total / 60:.1f} min)")
    print(f"Output: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
