"""
CR2 (Canon RAW) batch converter.

Converts CR2 files to JPG or PNG with optional resizing.

Usage as CLI:
    python -m src.editor.cr2_converter ./photos --format jpg --quality 92
    python -m src.editor.cr2_converter ./photos --format png --max-size 2048
    python -m src.editor.cr2_converter ./photos -o ./output --format jpg -q 85

Usage in code:
    from src.editor.cr2_converter import convert_cr2, batch_convert

    convert_cr2("photo.CR2", "photo.jpg", fmt="jpg", quality=92)
    results = batch_convert("./raw_photos", fmt="jpg", max_size=2048)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import rawpy
from PIL import Image

CR2_EXTENSIONS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".rw2", ".orf"}


def convert_cr2(
    src: str | Path,
    dst: str | Path | None = None,
    *,
    fmt: str = "jpg",
    quality: int = 92,
    max_size: int | None = None,
) -> Path:
    """Convert a single RAW file to JPG or PNG.

    Args:
        src: Path to the RAW file.
        dst: Output path. If None, writes next to src with new extension.
        fmt: Output format — "jpg" or "png".
        quality: JPEG quality 1-100 (ignored for PNG).
        max_size: If set, resize so the longest side <= max_size (keeps aspect ratio).

    Returns:
        Path to the converted file.
    """
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")

    ext = ".jpg" if fmt.lower() in ("jpg", "jpeg") else ".png"
    if dst is None:
        dst = src.with_suffix(ext)
    dst = Path(dst)

    with rawpy.imread(str(src)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=False,
            output_bps=8,
        )

    img = Image.fromarray(rgb)

    if max_size and max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    dst.parent.mkdir(parents=True, exist_ok=True)

    if ext == ".jpg":
        img.save(str(dst), "JPEG", quality=quality, optimize=True)
    else:
        img.save(str(dst), "PNG", optimize=True)

    return dst


def batch_convert(
    src_dir: str | Path,
    dst_dir: str | Path | None = None,
    *,
    fmt: str = "jpg",
    quality: int = 92,
    max_size: int | None = None,
) -> list[dict]:
    """Convert all RAW files in a directory.

    Args:
        src_dir: Directory containing RAW files.
        dst_dir: Output directory. If None, writes next to each source file.
        fmt: Output format — "jpg" or "png".
        quality: JPEG quality 1-100 (ignored for PNG).
        max_size: If set, resize so the longest side <= max_size.

    Returns:
        List of dicts with "src", "dst", "status", and optional "error" keys.
    """
    src_dir = Path(src_dir)
    if not src_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {src_dir}")

    raw_files = sorted(
        f for f in src_dir.iterdir()
        if f.is_file() and f.suffix.lower() in CR2_EXTENSIONS
    )

    if not raw_files:
        print(f"No RAW files found in {src_dir}")
        return []

    ext = ".jpg" if fmt.lower() in ("jpg", "jpeg") else ".png"
    results = []

    for i, src in enumerate(raw_files, 1):
        if dst_dir:
            dst = Path(dst_dir) / (src.stem + ext)
        else:
            dst = None

        try:
            out = convert_cr2(src, dst, fmt=fmt, quality=quality, max_size=max_size)
            size_kb = out.stat().st_size / 1024
            results.append({"src": str(src), "dst": str(out), "status": "ok"})
            print(f"  [{i}/{len(raw_files)}] {src.name} -> {out.name} ({size_kb:.0f} KB)")
        except Exception as e:
            results.append({"src": str(src), "dst": None, "status": "error", "error": str(e)})
            print(f"  [{i}/{len(raw_files)}] {src.name} FAILED: {e}")

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nDone: {ok}/{len(raw_files)} converted")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="CR2/RAW batch converter — converts Canon CR2 (and other RAW formats) to JPG or PNG",
    )
    parser.add_argument("folder", help="Folder containing RAW files")
    parser.add_argument("-o", "--output", default=None, help="Output folder (default: same as source)")
    parser.add_argument("-f", "--format", default="jpg", choices=["jpg", "png"], help="Output format (default: jpg)")
    parser.add_argument("-q", "--quality", type=int, default=92, help="JPEG quality 1-100 (default: 92)")
    parser.add_argument("--max-size", type=int, default=None, help="Resize longest side to this (keeps aspect ratio)")
    args = parser.parse_args()

    batch_convert(
        args.folder,
        dst_dir=args.output,
        fmt=args.format,
        quality=args.quality,
        max_size=args.max_size,
    )


if __name__ == "__main__":
    main()
