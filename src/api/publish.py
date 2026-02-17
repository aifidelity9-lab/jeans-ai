from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.publisher.tiktok import (
    get_auth_url,
    exchange_code,
    post_and_wait,
    check_publish_status,
)

router = APIRouter()

# In-memory token storage (use database in production)
_tokens: dict[str, dict] = {}


class PublishRequest(BaseModel):
    video_path: str
    title: str = "Check out these jeans! #fashion #jeans #ootd"
    privacy_level: str = "SELF_ONLY"


# ──────────────────────────────────────────────
# TikTok OAuth Flow
# ──────────────────────────────────────────────

@router.get("/tiktok/auth")
async def tiktok_auth(request: Request):
    """Step 1: Redirect user to TikTok for authorization."""
    redirect_uri = str(request.url_for("tiktok_callback"))
    auth_url = get_auth_url(redirect_uri=redirect_uri)
    return {"auth_url": auth_url, "message": "Open this URL in your browser to authorize TikTok"}


@router.get("/tiktok/callback", name="tiktok_callback")
async def tiktok_callback(code: str, state: str = "", request: Request = None):
    """Step 2: Handle OAuth callback, exchange code for tokens."""
    redirect_uri = str(request.url_for("tiktok_callback"))
    try:
        tokens = await exchange_code(code=code, redirect_uri=redirect_uri)
        open_id = tokens.get("open_id", "default")
        _tokens[open_id] = tokens
        return {
            "status": "authorized",
            "open_id": open_id,
            "expires_in": tokens.get("expires_in"),
            "message": "TikTok account connected! You can now publish videos.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# Video Publishing
# ──────────────────────────────────────────────

@router.post("/tiktok/publish")
async def publish_to_tiktok(req: PublishRequest):
    """Publish a video to TikTok."""
    if not _tokens:
        raise HTTPException(
            status_code=401,
            detail="No TikTok account connected. Visit /api/publish/tiktok/auth first.",
        )

    # Use first connected account
    open_id = next(iter(_tokens))
    access_token = _tokens[open_id]["access_token"]

    try:
        result = await post_and_wait(
            access_token=access_token,
            video_path=req.video_path,
            title=req.title,
            privacy_level=req.privacy_level,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiktok/status/{publish_id}")
async def get_status(publish_id: str):
    """Check publish status of a video."""
    if not _tokens:
        raise HTTPException(status_code=401, detail="No TikTok account connected.")

    open_id = next(iter(_tokens))
    access_token = _tokens[open_id]["access_token"]

    result = await check_publish_status(access_token, publish_id)
    return result
