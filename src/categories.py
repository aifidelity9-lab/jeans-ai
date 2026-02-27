"""Garment category definitions.

Each category encapsulates:
- Asset directory
- Try-on prompt template
- Video generation prompts
- Marketing captions
- Default garment description
"""

from dataclasses import dataclass, field
from pathlib import Path


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class GarmentCategory:
    name: str
    products_dir: str
    models_dir: str
    garment_desc: str
    tryon_category: str  # "upper_body", "lower_body", or "dresses"
    video_prompts: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)

    def get_product_images(self) -> list[str]:
        """Scan products directory for garment images."""
        return self._scan_dir(self.products_dir)

    def get_model_images(self) -> list[str]:
        """Scan models directory for model images."""
        return self._scan_dir(self.models_dir)

    def get_video_prompt(self, index: int) -> str:
        return self.video_prompts[index % len(self.video_prompts)]

    def get_caption(self, index: int) -> str:
        return self.captions[index % len(self.captions)]

    @staticmethod
    def _scan_dir(directory: str) -> list[str]:
        p = Path(directory)
        if not p.exists():
            return []
        return sorted(
            str(f) for f in p.iterdir()
            if f.suffix.lower() in VALID_EXTENSIONS
        )


# ── Category instances ──────────────────────────────────────────────

JEANS = GarmentCategory(
    name="jeans",
    products_dir="assets/products/jeans",
    models_dir="assets/models/jeans",
    garment_desc="Women's denim jeans",
    tryon_category="lower_body",
    video_prompts=[
        "A fashion model walks confidently towards the camera, showing off her jeans, studio lighting, clean background",
        "A woman turns slowly to show her outfit from different angles, natural movement, white background",
        "A model poses naturally, shifting weight between legs, showing the fit of her jeans, soft lighting",
        "A woman walks casually along a street, confident stride, showing her denim jeans, natural daylight",
        "A fashion model does a slow spin to show the full outfit, studio background, professional lighting",
    ],
    captions=[
        "Your new favorite jeans",
        "Comfort meets style",
        "Perfect fit, every time",
        "Denim that moves with you",
        "Effortlessly cool",
        "Made for your curves",
        "From day to night",
        "The perfect pair exists",
        "Confidence looks good on you",
        "Upgrade your denim game",
    ],
)

TSHIRTS = GarmentCategory(
    name="tshirts",
    products_dir="assets/products/tshirts",
    models_dir="assets/models/tshirts",
    garment_desc="Women's T-shirt",
    tryon_category="upper_body",
    video_prompts=[
        "A fashion model walks confidently towards the camera, showing off her T-shirt, studio lighting, clean background",
        "A woman turns slowly to show her T-shirt from different angles, natural movement, white background",
        "A model poses naturally, showing the fit of her T-shirt, soft lighting",
        "A woman walks casually along a street, confident stride, showing her T-shirt, natural daylight",
        "A fashion model does a slow spin to show the full outfit, studio background, professional lighting",
    ],
    captions=[
        "Your new go-to tee",
        "Effortless style starts here",
        "The perfect everyday T-shirt",
        "Comfort never looked so good",
        "Simple. Bold. You.",
        "Wear it your way",
        "The tee that fits just right",
        "Casual made cool",
        "Designed for your lifestyle",
        "Level up your basics",
    ],
)

# Registry: look up by name
CATEGORIES: dict[str, GarmentCategory] = {
    "jeans": JEANS,
    "tshirts": TSHIRTS,
}


def get_category(name: str) -> GarmentCategory:
    """Get a category by name. Raises KeyError if not found."""
    if name not in CATEGORIES:
        available = ", ".join(CATEGORIES.keys())
        raise KeyError(f"Unknown category '{name}'. Available: {available}")
    return CATEGORIES[name]
