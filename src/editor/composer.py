import logging
import platform
import random
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)

# Resolve font path per platform
if platform.system() == "Windows":
    _FONT = "C:/Windows/Fonts/arial.ttf"
elif platform.system() == "Darwin":
    _FONT = "/System/Library/Fonts/Helvetica.ttc"
else:
    _FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Default captions for jeans marketing (English for US market)
DEFAULT_CAPTIONS = [
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
]

# Call-to-action overlays
CTA_TEXTS = [
    "Shop now - Link in bio",
    "Tap to shop",
    "Limited stock available",
    "Free shipping today",
]


def compose_video(
    video_clips: list[str],
    output_path: str,
    caption: str | None = None,
    cta_text: str | None = None,
    music_path: str | None = None,
    target_duration: float = 15.0,
    resolution: tuple[int, int] = (1080, 1920),
) -> str:
    """Compose a final short-form video from raw clips.

    Args:
        video_clips: List of paths to raw video files.
        output_path: Where to save the final video.
        caption: Marketing caption overlay. Random if None.
        cta_text: Call-to-action text at the end. Random if None.
        music_path: Path to background music file. None = no music.
        target_duration: Target video duration in seconds.
        resolution: Output resolution (width, height). Default 1080x1920 (9:16).

    Returns:
        Path to the final composed video.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if not caption:
        caption = random.choice(DEFAULT_CAPTIONS)
    if not cta_text:
        cta_text = random.choice(CTA_TEXTS)

    # Load and resize all clips to target resolution
    clips = []
    for clip_path in video_clips:
        clip = VideoFileClip(clip_path)
        clip = clip.resized(height=resolution[1])

        # Center crop to target width if needed
        if clip.w > resolution[0]:
            x_center = clip.w / 2
            x1 = int(x_center - resolution[0] / 2)
            clip = clip.cropped(x1=x1, width=resolution[0])

        clips.append(clip)

    # Concatenate clips
    if len(clips) > 1:
        main_video = concatenate_videoclips(clips, method="compose")
    else:
        main_video = clips[0]

    # Trim or loop to target duration
    if main_video.duration > target_duration:
        main_video = main_video.subclipped(0, target_duration)
    elif main_video.duration < target_duration and len(clips) == 1:
        # If single clip is shorter, just use its natural duration
        target_duration = main_video.duration

    # Add caption text overlay (top area)
    caption_clip = (
        TextClip(
            text=caption,
            font_size=48,
            color="white",
            stroke_color="black",
            stroke_width=2,
            font=_FONT,
        )
        .with_position(("center", 150))
        .with_duration(main_video.duration)
    )

    # Add CTA text overlay (bottom area, last 3 seconds)
    cta_start = max(0, main_video.duration - 3)
    cta_clip = (
        TextClip(
            text=cta_text,
            font_size=40,
            color="yellow",
            stroke_color="black",
            stroke_width=2,
            font=_FONT,
        )
        .with_position(("center", resolution[1] - 250))
        .with_start(cta_start)
        .with_duration(main_video.duration - cta_start)
    )

    # Composite everything
    final = CompositeVideoClip(
        [main_video, caption_clip, cta_clip],
        size=resolution,
    )

    # Add background music if provided
    if music_path and Path(music_path).exists():
        music = AudioFileClip(music_path)
        if music.duration > final.duration:
            music = music.subclipped(0, final.duration)
        music = music.with_volume_scaled(0.3)  # 30% volume so it doesn't overpower

        if final.audio:
            from moviepy import CompositeAudioClip
            final = final.with_audio(CompositeAudioClip([final.audio, music]))
        else:
            final = final.with_audio(music)

    # Export
    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger=None,
    )

    # Cleanup
    for clip in clips:
        clip.close()
    final.close()

    logger.info(f"Final video saved to {output_path}")
    return output_path


def batch_compose(
    video_groups: list[list[str]],
    output_dir: str = "output/final",
    music_path: str | None = None,
) -> list[str]:
    """Compose multiple final videos from groups of raw clips.

    Args:
        video_groups: List of clip groups. Each group becomes one final video.
        output_dir: Directory to save final videos.
        music_path: Optional background music.

    Returns:
        List of paths to final videos.
    """
    results = []
    for i, clips in enumerate(video_groups):
        output_path = f"{output_dir}/final_{i:04d}.mp4"
        try:
            path = compose_video(
                video_clips=clips,
                output_path=output_path,
                music_path=music_path,
            )
            results.append(path)
        except Exception as e:
            logger.error(f"Failed to compose video {i}: {e}")
            results.append(f"ERROR: {e}")
    return results
