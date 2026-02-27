"""Batch try-on: all products × all models → photos."""

import asyncio
import time
from itertools import product as cartesian
from pathlib import Path

from src.tryon.engine import run_tryon


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
    try:
        t0 = time.time()
        result = await run_tryon(
            human_img=model,
            garment_img=garment,
            garment_desc="Women's denim jeans",
            category="lower_body",
            output_dir=output_dir,
        )
        elapsed = time.time() - t0
        print(f"  [{index:02d}] OK  {g_name} × {m_name}  ({elapsed:.1f}s)", flush=True)
        return {"status": "ok", "file": result}
    except Exception as e:
        print(f"  [{index:02d}] FAIL {g_name} × {m_name}  ({e})", flush=True)
        return {"status": "fail", "error": str(e)}


async def main():
    products = get_images("assets/products/jeans")
    models = get_images("assets/models/jeans")

    print(f"Products: {len(products)}")
    print(f"Models:   {len(models)}")

    combos = list(cartesian(products, models))
    total = len(combos)
    print(f"Total combinations: {total}")
    print(f"Estimated time: ~{total * 10 // 60} min\n")

    output_dir = "output/batch_all"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    concurrency = 3
    success = 0
    failed = 0
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
                success += 1
            else:
                failed += 1
        done = batch_start + len(batch)
        elapsed = time.time() - t_start
        avg = elapsed / done
        remaining = avg * (total - done)
        print(f"  Progress: {done}/{total}  (~{remaining:.0f}s remaining)\n", flush=True)

    elapsed_total = time.time() - t_start
    print(f"\nDone! {success}/{total} succeeded, {failed} failed")
    print(f"Total time: {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    print(f"Output: {output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
