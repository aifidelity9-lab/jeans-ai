# Jeans AI

AI-powered fashion e-commerce platform. Automatically generates virtual try-on images, fashion videos, and publishes to TikTok.

Supports multiple garment categories (jeans, T-shirts, etc.) with category-specific models, prompts, and marketing content.

## Architecture

```
                    GarmentCategory (jeans / tshirts / ...)
                           |
              +------------+------------+
              |            |            |
         TryOnEngine  VideoGenerator  VideoComposer
         (Gemini API)   (Veo API)     (MoviePy)
              |            |            |
              +------+-----+------+-----+
                     |            |
                  Pipeline    DailyPipeline
                     |
                  FastAPI
```

### Core Classes

| Class | File | Responsibility |
|-------|------|----------------|
| `GarmentCategory` | `src/categories.py` | Category config: asset dirs, prompts, captions |
| `TryOnEngine` | `src/tryon/engine.py` | Virtual try-on via Google Gemini Image API |
| `VideoGenerator` | `src/video/generator.py` | Video generation via Google Veo 3.1 |
| `VideoComposer` | `src/editor/composer.py` | Video composition with text overlays + music |
| `Pipeline` | `src/tasks/daily_pipeline.py` | Orchestrates try-on -> video -> compose |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL + SQLAlchemy 2.0 |
| Queue | Redis + APScheduler |
| AI Try-On | Google Gemini 2.5 Flash (Nano Banana) |
| AI Video | Google Veo 3.1 Fast |
| Editing | MoviePy + FFmpeg |
| Publishing | TikTok Content Posting API |

## Directory Structure

```
jeans-ai/
├── src/
│   ├── categories.py           # GarmentCategory class + registry
│   ├── config.py               # Settings (API keys, DB, etc.)
│   ├── main.py                 # FastAPI app
│   ├── tryon/
│   │   └── engine.py           # TryOnEngine class
│   ├── video/
│   │   └── generator.py        # VideoGenerator class
│   ├── editor/
│   │   └── composer.py         # VideoComposer class
│   ├── tasks/
│   │   ├── daily_pipeline.py   # Pipeline class + daily batch
│   │   └── scheduler.py        # APScheduler (6:00 AM EST)
│   ├── api/
│   │   ├── tryon.py            # POST /api/tryon/single, /batch
│   │   ├── pipeline.py         # POST /api/pipeline/run, /batch, /daily
│   │   ├── products.py         # Product CRUD
│   │   └── publish.py          # TikTok publishing
│   ├── models/                 # SQLAlchemy ORM models
│   └── publisher/
│       └── tiktok.py           # TikTok OAuth + posting
├── assets/
│   ├── products/
│   │   ├── jeans/              # Jeans product images
│   │   └── tshirts/            # T-shirt product images
│   ├── models/
│   │   ├── jeans/              # Models for jeans try-on
│   │   └── tshirts/            # Models for T-shirt try-on
│   └── music/                  # Background music
├── tests/                      # Test scripts (see Testing below)
├── output/                     # Generated content
├── .vscode/launch.json         # VS Code debug configurations
├── .env                        # API keys (not in git)
└── pyproject.toml              # Dependencies
```

## Quick Start

### Prerequisites

- Python 3.12+
- Google Gemini API key (for try-on + video)
- PostgreSQL (optional, for production)
- Docker (optional, for Redis)

### Setup

```bash
git clone https://github.com/aifidelity9-lab/jeans-ai.git
cd jeans-ai

# Create virtual environment
uv venv --python 3.12

# Install dependencies
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env — set GEMINI_API_KEY
```

### Add Assets

Put garment product images and model images into the corresponding category directories:

```
assets/products/jeans/      <- jeans flat-lay photos
assets/products/tshirts/    <- T-shirt flat-lay photos
assets/models/jeans/        <- full-body model photos (for jeans)
assets/models/tshirts/      <- full-body model photos (for T-shirts)
```

Model images should be clean full-body photos (no phone UI, no watermarks).

---

## Testing

### Option A: VS Code (Recommended)

#### Setup

1. Open the project folder in VS Code
2. Press `Ctrl+Shift+D` to open the Debug panel
3. Top dropdown shows pre-configured test targets

#### Single Try-on Test

Tests one garment + one model combination. Fast, good for verifying setup.

1. Open `tests/test_single.py` (jeans) or `tests/test_tshirt_pipeline.py` (T-shirt)
2. Debug panel -> select **"Run current file"**
3. Press `F5`
4. Check output in the terminal, result image in `output/test_single/` or `output/test_tshirt/`

#### Batch Try-on Test (Photos Only)

Tests all garments x all models for one category. No video, just try-on images.

1. Debug panel -> select **"T-shirt batch try-on"** or **"Jeans batch try-on"**
2. Press `F5`
3. Watch progress in the terminal
4. Results saved to `output/batch_tshirt/` or `output/batch_all/`

#### Full Pipeline Test (Try-on + Video)

Tests the complete pipeline: try-on -> video generation.

1. Debug panel -> select **"T-shirt full pipeline"** or **"Jeans full pipeline"**
2. Press `F5`
3. Takes ~60s per combination (10s try-on + 50s video)
4. Results saved to `output/test_tshirt/` or `output/test_pipeline/`

#### Setting Breakpoints

1. Click left of any line number to add a red breakpoint dot
2. Press `F5` to run in debug mode
3. Execution pauses at breakpoints, inspect variables in the left panel
4. `F10` = step over, `F11` = step into, `F5` = continue

### Option B: Terminal

Open a terminal in VS Code with `` Ctrl+` `` or use any terminal.

```bash
cd D:/Projects/jeans-ai

# Activate virtual environment
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # Mac/Linux
```

#### Single Tests

```bash
# Jeans: single try-on
python -m tests.test_single

# T-shirt: single try-on + video
python -m tests.test_tshirt_pipeline

# Jeans: single try-on + video
python -m tests.test_full_pipeline
```

#### Batch Tests

```bash
# T-shirt: all T-shirts x all T-shirt models (photos only)
python -m tests.test_tshirt_batch

# Jeans: all jeans x all jeans models (photos only)
python -m tests.test_batch_all

# Jeans: all combinations with video (full pipeline)
python -m tests.test_batch_full_pipeline
```

### Test Files Reference

| Test File | Category | What it does | ~Time |
|-----------|----------|-------------|-------|
| `test_single.py` | Jeans | 1 jeans + 1 model -> photo | ~10s |
| `test_tshirt_pipeline.py` | T-shirt | 1 T-shirt + 1 model -> photo + video | ~60s |
| `test_full_pipeline.py` | Jeans | 1 jeans + 1 model -> photo + video | ~60s |
| `test_tshirt_batch.py` | T-shirt | All T-shirts x all models -> photos | ~10s each |
| `test_batch_all.py` | Jeans | All jeans x all models -> photos | ~10s each |
| `test_batch_full_pipeline.py` | Jeans | All combinations -> photos + videos | ~60s each |

### VS Code Debug Configurations

Pre-configured in `.vscode/launch.json`:

| Name | What it runs |
|------|-------------|
| T-shirt batch try-on | `tests.test_tshirt_batch` |
| T-shirt full pipeline | `tests.test_tshirt_pipeline` |
| Jeans batch try-on | `tests.test_batch_all` |
| Jeans full pipeline | `tests.test_full_pipeline` |
| Run current file | Whatever file is open |

---

## Adding a New Category

To add a new garment category (e.g. shirts):

### 1. Create asset directories

```bash
mkdir -p assets/products/shirts assets/models/shirts
```

### 2. Add category definition in `src/categories.py`

```python
SHIRTS = GarmentCategory(
    name="shirts",
    products_dir="assets/products/shirts",
    models_dir="assets/models/shirts",
    garment_desc="Women's shirt",
    tryon_category="upper_body",
    video_prompts=[
        "A fashion model walks confidently, showing off her shirt, studio lighting",
        # ... more prompts
    ],
    captions=[
        "Your new favorite shirt",
        # ... more captions
    ],
)
CATEGORIES["shirts"] = SHIRTS
```

### 3. Add product + model images to the new directories

### 4. Test

```bash
python -c "
from src.categories import get_category
cat = get_category('shirts')
print(f'Products: {len(cat.get_product_images())}')
print(f'Models: {len(cat.get_model_images())}')
"
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tryon/single` | POST | Single try-on (one garment + one model) |
| `/api/tryon/batch` | POST | Batch try-on (one garment x N models) |
| `/api/pipeline/run` | POST | Full pipeline: try-on -> video -> edit |
| `/api/pipeline/batch` | POST | One product x N models pipeline |
| `/api/pipeline/daily` | POST | Trigger daily auto-generation |
| `/api/products/` | GET/POST | Product CRUD |
| `/api/publish/tiktok/auth` | GET | TikTok OAuth |
| `/api/publish/tiktok/publish` | POST | Publish video to TikTok |

Start the server:

```bash
python run.py
# -> http://localhost:8001/docs
```

---

## Cost

| Component | Per Unit |
|-----------|---------|
| Try-on (Gemini Flash) | Free tier / pay-as-you-go |
| Video (Veo 3.1 Fast) | Free tier limited (~10/day), paid plan for more |

Both use the same Google Gemini API key.
