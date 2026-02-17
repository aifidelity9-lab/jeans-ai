import logging
import math
import os
import time
from pathlib import Path

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://open.tiktokapis.com"
TIKTOK_AUTH = "https://www.tiktok.com/v2/auth/authorize/"


# ──────────────────────────────────────────────
# OAuth 2.0
# ──────────────────────────────────────────────

def get_auth_url(redirect_uri: str, state: str = "jeans_ai") -> str:
    """Generate TikTok OAuth authorization URL."""
    from urllib.parse import urlencode
    params = {
        "client_key": settings.tiktok_app_key,
        "response_type": "code",
        "scope": "user.info.basic,video.publish,video.upload",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{TIKTOK_AUTH}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/v2/oauth/token/",
            data={
                "client_key": settings.tiktok_app_key,
                "client_secret": settings.tiktok_app_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_token(refresh_token_str: str) -> dict:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/v2/oauth/token/",
            data={
                "client_key": settings.tiktok_app_key,
                "client_secret": settings.tiktok_app_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_str,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


# ──────────────────────────────────────────────
# Video Posting
# ──────────────────────────────────────────────

async def post_video(
    access_token: str,
    video_path: str,
    title: str = "",
    privacy_level: str = "SELF_ONLY",
    is_aigc: bool = True,
) -> dict:
    """Upload and post a video to TikTok via FILE_UPLOAD (chunked).

    Args:
        access_token: User's OAuth access token.
        video_path: Local path to the video file.
        title: Video caption (max 2200 chars). Include #hashtags here.
        privacy_level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS,
                       FOLLOWER_OF_CREATOR, or SELF_ONLY.
        is_aigc: Mark as AI-generated content (recommended for transparency).

    Returns:
        Dict with publish_id and status info.
    """
    video_size = os.path.getsize(video_path)
    chunk_size = 10 * 1024 * 1024  # 10 MB

    if video_size <= 5 * 1024 * 1024:
        chunk_size = video_size
    elif video_size > 64 * 1024 * 1024:
        chunk_size = max(chunk_size, math.ceil(video_size / 1000))

    total_chunks = math.ceil(video_size / chunk_size)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    # Step 1: Initialize upload
    payload = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_stitch": False,
            "disable_comment": False,
            "is_aigc": is_aigc,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/v2/post/publish/video/init/",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        init_data = resp.json()

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]
    logger.info(f"Upload initialized: publish_id={publish_id}, chunks={total_chunks}")

    # Step 2: Upload chunks sequentially
    async with httpx.AsyncClient(timeout=300) as client:
        with open(video_path, "rb") as f:
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                start = i * chunk_size
                end = start + len(chunk_data) - 1

                resp = await client.put(
                    upload_url,
                    content=chunk_data,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(chunk_data)),
                        "Content-Range": f"bytes {start}-{end}/{video_size}",
                    },
                )
                logger.info(f"Chunk {i+1}/{total_chunks}: status={resp.status_code}")

    return {"publish_id": publish_id, "status": "uploading"}


async def check_publish_status(access_token: str, publish_id: str) -> dict:
    """Check the publish status of a video."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/v2/post/publish/status/fetch/",
            headers=headers,
            json={"publish_id": publish_id},
        )
        resp.raise_for_status()
        return resp.json()


async def post_and_wait(
    access_token: str,
    video_path: str,
    title: str = "",
    privacy_level: str = "SELF_ONLY",
    max_wait: int = 60,
) -> dict:
    """Post a video and poll until published or failed.

    Returns:
        Final status dict with publish result.
    """
    result = await post_video(
        access_token=access_token,
        video_path=video_path,
        title=title,
        privacy_level=privacy_level,
    )
    publish_id = result["publish_id"]

    import asyncio
    for attempt in range(max_wait // 5):
        await asyncio.sleep(5)
        status = await check_publish_status(access_token, publish_id)
        state = status.get("data", {}).get("status", "UNKNOWN")
        logger.info(f"Publish status [{attempt+1}]: {state}")

        if state == "PUBLISH_COMPLETE":
            return {"status": "published", "data": status["data"]}
        elif state == "FAILED":
            reason = status.get("data", {}).get("fail_reason", "unknown")
            return {"status": "failed", "reason": reason}

    return {"status": "timeout", "publish_id": publish_id}
