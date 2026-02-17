from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.database import engine
from src.models import Base
from src.tasks.scheduler import setup_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start daily scheduler
    setup_scheduler()
    yield
    shutdown_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Jeans AI",
    description="AI-powered jeans e-commerce pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
