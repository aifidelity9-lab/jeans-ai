<div align="center">

# 👖 Jeans AI

### ✨ *Where AI Meets Fashion* ✨

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TikTok](https://img.shields.io/badge/TikTok-API-000000?style=for-the-badge&logo=tiktok&logoColor=white)](https://developers.tiktok.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)

**AI-powered e-commerce platform for women's jeans.**
**Automatically generates virtual try-on images, fashion videos, and publishes to TikTok.**

---

</div>

## 🎨 Architecture

```mermaid
graph TD
    A[👖 Product Images] --> C[🤖 AI Virtual Try-On]
    B[💃 Model Images] --> C
    C -->|IDM-VTON| D[🎬 AI Video Generation]
    D -->|Kling v1.6 Pro| E[✂️ Auto Editing]
    E -->|MoviePy| F[📱 TikTok Publishing]
    style A fill:#FF6B6B,color:#fff
    style B fill:#4ECDC4,color:#fff
    style C fill:#45B7D1,color:#fff
    style D fill:#96CEB4,color:#fff
    style E fill:#FFEAA7,color:#333
    style F fill:#000,color:#fff
```

## 🔄 Business Logic Flow

```mermaid
flowchart TB
    subgraph INPUT["📥 Input Layer"]
        direction LR
        P["👖 Product Photos<br/>(flat-lay jeans)"]
        M["💃 Model Photos<br/>(diverse full-body)"]
        DB[(🗄️ PostgreSQL<br/>Products & Models)]
    end

    subgraph AI["🧠 AI Processing Layer"]
        direction LR
        TRYON["👗 Virtual Try-On<br/>IDM-VTON on Replicate<br/>~$0.023/image"]
        VIDEO["🎥 Video Generation<br/>Kling v1.6 Pro<br/>~$0.10/video"]
    end

    subgraph EDIT["✂️ Post-Production Layer"]
        direction LR
        RESIZE["📐 Resize to 9:16<br/>(1080×1920)"]
        TEXT["✏️ Add Caption<br/>+ CTA Overlay"]
        MUSIC["🎵 Add Background<br/>Music (30% vol)"]
        EXPORT["📦 Export MP4<br/>(H.264 / AAC)"]
    end

    subgraph PUBLISH["📱 Distribution Layer"]
        direction LR
        TT["<img src='https://img.shields.io/badge/-TikTok-000?style=flat-square&logo=tiktok&logoColor=white' />"]
        IG["<img src='https://img.shields.io/badge/-Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white' />"]
        YT["<img src='https://img.shields.io/badge/-YouTube-FF0000?style=flat-square&logo=youtube&logoColor=white' />"]
    end

    subgraph SCHEDULE["⏰ Scheduler"]
        CRON["🤖 APScheduler<br/>Daily 6:00 AM EST"]
        API["🌐 Manual Trigger<br/>POST /api/pipeline/daily"]
    end

    P --> DB
    M --> DB
    DB --> TRYON
    TRYON -->|"N products × M models<br/>= N×M try-on images"| VIDEO
    VIDEO -->|"5-sec fashion clips"| RESIZE
    RESIZE --> TEXT --> MUSIC --> EXPORT
    EXPORT -->|"up to 100 videos/day"| TT
    EXPORT --> IG
    EXPORT --> YT
    SCHEDULE -.->|triggers| TRYON

    style INPUT fill:#1a1a2e,color:#fff
    style AI fill:#16213e,color:#fff
    style EDIT fill:#0f3460,color:#fff
    style PUBLISH fill:#533483,color:#fff
    style SCHEDULE fill:#e94560,color:#fff
```

```mermaid
sequenceDiagram
    participant U as 👤 User / Scheduler
    participant API as 🚀 FastAPI
    participant R as 🤖 Replicate
    participant MP as ✂️ MoviePy
    participant TT as 📱 TikTok

    U->>API: POST /api/pipeline/daily
    loop For each Product × Model
        API->>R: IDM-VTON try-on request
        R-->>API: Try-on image URL
        API->>R: Kling v1.6 video request
        R-->>API: Video URL (.mp4)
        API->>MP: Compose (resize + caption + CTA)
        MP-->>API: Final video path
    end
    API->>TT: OAuth + Upload video
    TT-->>API: Publish complete
    API-->>U: ✅ 100 videos generated & published
```

## 💎 Tech Stack

| Layer | Technology | Badge |
|-------|-----------|-------|
| 🚀 **Backend** | FastAPI + Python 3.12 | ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) |
| 🗄️ **Database** | PostgreSQL + SQLAlchemy 2.0 | ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) |
| ⚡ **Queue** | Redis + APScheduler | ![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat-square&logo=redis&logoColor=white) |
| 👗 **AI Try-On** | IDM-VTON on Replicate | ![AI](https://img.shields.io/badge/-IDM--VTON-FF6F61?style=flat-square) |
| 🎥 **AI Video** | Kling v1.6 Pro on Replicate | ![Video](https://img.shields.io/badge/-Kling_v1.6-8B5CF6?style=flat-square) |
| ✂️ **Editing** | MoviePy + FFmpeg | ![MoviePy](https://img.shields.io/badge/-MoviePy-FF9800?style=flat-square) |
| 📱 **Publishing** | TikTok Content Posting API | ![TikTok](https://img.shields.io/badge/-TikTok-000?style=flat-square&logo=tiktok&logoColor=white) |
| 📦 **Package** | uv (Rust-powered) | ![uv](https://img.shields.io/badge/-uv-DE5C9D?style=flat-square) |

## 🚀 Quick Start

### Prerequisites

> 💡 Make sure you have these installed before starting

- 🐍 Python 3.12+
- 🐳 Docker (for Redis)
- 🐘 PostgreSQL (running locally)
- 🔑 Replicate API token
- 📱 TikTok Developer App

### Setup

```bash
# 📥 Clone
git clone https://github.com/aifidelity9-lab/jeans-ai.git
cd jeans-ai

# 🏗️ Create virtual environment
uv venv --python 3.12

# 📦 Install dependencies
uv pip install -e ".[dev]"
uv pip install replicate moviepy apscheduler

# 🐳 Start Redis
docker compose up -d

# ⚙️ Configure environment
cp .env.example .env
# Edit .env with your API keys

# 🚀 Run server
python run.py
```

> 🌐 Server runs at **http://localhost:8001/docs**

## 🔌 API Endpoints

### 📦 Products
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/products/` | `GET` | List all products |
| `/api/products/` | `POST` | Upload new product |

### 👗 Virtual Try-On
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tryon/single` | `POST` | Single try-on test |
| `/api/tryon/batch` | `POST` | Batch try-on across models |

### 🎬 Pipeline
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pipeline/run` | `POST` | Full pipeline: try-on → video → edit |
| `/api/pipeline/batch` | `POST` | One product × N models |
| `/api/pipeline/daily` | `POST` | 🔥 Trigger daily auto-generation |

### 📱 Publishing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/publish/tiktok/auth` | `GET` | TikTok OAuth |
| `/api/publish/tiktok/publish` | `POST` | Publish to TikTok |

## ⏰ Daily Auto-Generation

> 🤖 The system automatically runs at **6:00 AM EST** every day

```
1. 📸 Scans assets/products/ for garment images
2. 💃 Scans assets/models/ for model images
3. 🔄 Generates all product × model combinations
4. 🎬 Outputs final videos to output/YYYY-MM-DD/final/
```

### Manual trigger:

```bash
# 🌐 Via API
curl -X POST http://localhost:8001/api/pipeline/daily

# 💻 Via command line
python -m src.tasks.daily_pipeline
```

## 📁 Directory Structure

```
jeans-ai/
├── 🐍 src/
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
├── 👖 assets/
│   ├── products/            # Jeans flat-lay images
│   ├── models/              # Full-body model images
│   └── music/               # Background music
├── 🎬 output/               # Generated content
├── 📄 docs/                 # GitHub Pages
├── 🐳 docker-compose.yml    # Redis
├── 📦 pyproject.toml        # Dependencies
├── 🚀 run.py                # Server entry point
└── 🔑 .env                  # API keys (not in git)
```

## 💰 Cost Estimate

<div align="center">

| Component | Per Unit | Daily (100 videos) | Monthly |
|:---------:|:--------:|:-------------------:|:-------:|
| 👗 Try-on (Replicate) | ~$0.023/image | $11.50 | $345 |
| 🎥 Video (Kling) | ~$0.10/video | $10.00 | $300 |
| **💵 Total** | | **$21.50** | **$645** |

</div>

---

<div align="center">

### Made with 🤖 AI + 💖 Fashion

**Rebecca** — *Denim, Reinvented.*

</div>
