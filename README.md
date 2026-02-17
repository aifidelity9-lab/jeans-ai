# Jeans AI

AI-powered e-commerce platform for women's jeans. Automatically generates virtual try-on images, fashion videos, and publishes to TikTok.

## Architecture

```
Product Images + Model Images
        ↓
   AI Virtual Try-On (IDM-VTON via Replicate)
        ↓
   AI Video Generation (Kling v1.6 Pro via Replicate)
        ↓
   Auto Editing (MoviePy: captions + CTA + music)
        ↓
   Multi-Platform Publishing (TikTok Content Posting API)
```

## Tech Stack

- **Backend**: FastAPI + Python 3.12
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async)
- **Task Queue**: Redis + APScheduler
- **AI Try-On**: IDM-VTON on Replicate
- **AI Video**: Kling v1.6 Pro on Replicate
- **Video Editing**: MoviePy + FFmpeg
- **Publishing**: TikTok Content Posting API
- **Package Manager**: uv

## Quick Start

### Prerequisites

- Python 3.12+
- Docker (for Redis)
- PostgreSQL (running locally)
- Replicate API token
- TikTok Developer App (for publishing)

### Setup

```bash
# Clone
git clone https://github.com/aifidelity9-lab/jeans-ai.git
cd jeans-ai

# Create virtual environment
uv venv --python 3.12

# Install dependencies
uv pip install -e ".[dev]"
uv pip install replicate moviepy apscheduler

# Start Redis
docker compose up -d

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
python run.py
```

Server runs at http://localhost:8001/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/products/` | GET/POST | Manage product listings |
| `/api/tryon/single` | POST | Single virtual try-on |
| `/api/tryon/batch` | POST | Batch try-on across models |
| `/api/pipeline/run` | POST | Full pipeline: try-on → video → edit |
| `/api/pipeline/batch` | POST | Batch pipeline for one product × N models |
| `/api/pipeline/daily` | POST | Trigger daily auto-generation |
| `/api/publish/tiktok/auth` | GET | TikTok OAuth authorization |
| `/api/publish/tiktok/publish` | POST | Publish video to TikTok |

## Daily Auto-Generation

The system automatically runs at **6:00 AM EST** every day:

1. Scans `assets/products/` for garment images
2. Scans `assets/models/` for model images
3. Generates all product × model combinations
4. Outputs final videos to `output/YYYY-MM-DD/final/`

### Manual trigger:

```bash
# Via API
curl -X POST http://localhost:8001/api/pipeline/daily

# Via command line
python -m src.tasks.daily_pipeline
```

## Directory Structure

```
jeans-ai/
├── src/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   ├── models/              # SQLAlchemy models
│   ├── api/                 # API routes
│   │   ├── products.py      # Product CRUD
│   │   ├── tryon.py         # Try-on endpoints
│   │   ├── pipeline.py      # Pipeline endpoints
│   │   └── publish.py       # TikTok publishing
│   ├── tryon/
│   │   └── engine.py        # IDM-VTON integration
│   ├── video/
│   │   └── generator.py     # Kling video generation
│   ├── editor/
│   │   └── composer.py      # MoviePy video editing
│   ├── publisher/
│   │   └── tiktok.py        # TikTok API client
│   └── tasks/
│       ├── daily_pipeline.py # Daily batch pipeline
│       └── scheduler.py      # APScheduler config
├── assets/
│   ├── products/            # Jeans flat-lay images
│   ├── models/              # Full-body model images
│   └── music/               # Background music
├── output/                  # Generated content
├── docs/                    # GitHub Pages (TOS, Privacy)
├── docker-compose.yml       # Redis
├── pyproject.toml           # Dependencies
├── run.py                   # Server entry point
└── .env                     # API keys (not in git)
```

## Cost Estimate

| Component | Cost per Unit | Daily (100 videos) | Monthly |
|-----------|--------------|--------------------:|--------:|
| Try-on (Replicate) | ~$0.023/image | $11.50 | $345 |
| Video (Kling) | ~$0.10/video | $10.00 | $300 |
| **Total** | | **$21.50** | **$645** |

## License

Private - All rights reserved.
