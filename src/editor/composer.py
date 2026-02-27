import logging
import platform
import random
from dataclasses import dataclass, field
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
    _DEFAULT_FONT = "C:/Windows/Fonts/arial.ttf"
elif platform.system() == "Darwin":
    _DEFAULT_FONT = "/System/Library/Fonts/Helvetica.ttc"
else:
    _DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@dataclass
class TextStyle:
    """Configuration for text overlay appearance."""
    font_size: int = 48
    color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 2
    font: str = _DEFAULT_FONT


class VideoComposer:
    """Composes final short-form videos from raw clips with overlays."""

    DEFAULT_CAPTIONS = [
        "Your new favorite look",
        "Comfort meets style",
        "Perfect fit, every time",
        "Effortlessly cool",
        "Made for your curves",
        "From day to night",
        "Confidence looks good on you",
    ]

    DEFAULT_CTAS = [
        "Shop now - Link in bio",
        "Tap to shop",
        "Limited stock available",
        "Free shipping today",
    ]

    def __init__(
        self,
        captions: list[str] | None = None,
        cta_texts: list[str] | None = None,
        caption_style: TextStyle | None = None,
        cta_style: TextStyle | None = None,
        resolution: tuple[int, int] = (1080, 1920),
        music_volume: float = 0.3,
    ):
        self.captions = captions or self.DEFAULT_CAPTIONS
        self.cta_texts = cta_texts or self.DEFAULT_CTAS
        self.caption_style = caption_style or TextStyle()
        self.cta_style = cta_style or TextStyle(font_size=40, color="yellow")
        self.resolution = resolution
        self.music_volume = music_volume

    def compose(
        self,
        video_clips: list[str],
        output_path: str,
        caption: str | None = None,
        cta_text: str | None = None,
        music_path: str | None = None,
        target_duration: float = 15.0,
    ) -> str:
        """Compose a final video from raw clips with text overlays.

        Returns path to the final composed video.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        caption = caption or random.choice(self.captions)
        cta_text = cta_text or random.choice(self.cta_texts)

        # Load and resize clips
        clips = []
        for clip_path in video_clips:
            clip = VideoFileClip(clip_path)
            clip = clip.resized(height=self.resolution[1])
            if clip.w > self.resolution[0]:
                x_center = clip.w / 2
                x1 = int(x_center - self.resolution[0] / 2)
                clip = clip.cropped(x1=x1, width=self.resolution[0])
            clips.append(clip)

        main_video = concatenate_videoclips(clips, method="compose") if len(clips) > 1 else clips[0]

        if main_video.duration > target_duration:
            main_video = main_video.subclipped(0, target_duration)
        elif main_video.duration < target_duration and len(clips) == 1:
            target_duration = main_video.duration

        # Caption overlay (top)
        cs = self.caption_style
        caption_clip = (
            TextClip(text=caption, font_size=cs.font_size, color=cs.color,
                     stroke_color=cs.stroke_color, stroke_width=cs.stroke_width, font=cs.font)
            .with_position(("center", 150))
            .with_duration(main_video.duration)
        )

        # CTA overlay (bottom, last 3 seconds)
        cta_start = max(0, main_video.duration - 3)
        cts = self.cta_style
        cta_clip = (
            TextClip(text=cta_text, font_size=cts.font_size, color=cts.color,
                     stroke_color=cts.stroke_color, stroke_width=cts.stroke_width, font=cts.font)
            .with_position(("center", self.resolution[1] - 250))
            .with_start(cta_start)
            .with_duration(main_video.duration - cta_start)
        )

        final = CompositeVideoClip([main_video, caption_clip, cta_clip], size=self.resolution)

        # Background music
        if music_path and Path(music_path).exists():
            music = AudioFileClip(music_path)
            if music.duration > final.duration:
                music = music.subclipped(0, final.duration)
            music = music.with_volume_scaled(self.music_volume)

            if final.audio:
                from moviepy import CompositeAudioClip
                final = final.with_audio(CompositeAudioClip([final.audio, music]))
            else:
                final = final.with_audio(music)

        final.write_videofile(output_path, fps=30, codec="libx264",
                              audio_codec="aac", preset="medium", logger=None)

        for clip in clips:
            clip.close()
        final.close()

        logger.info(f"Final video saved to {output_path}")
        return output_path

    def batch_compose(
        self,
        video_groups: list[list[str]],
        output_dir: str = "output/final",
        music_path: str | None = None,
    ) -> list[str]:
        """Compose multiple final videos from groups of raw clips."""
        results = []
        for i, clips in enumerate(video_groups):
            output_path = f"{output_dir}/final_{i:04d}.mp4"
            try:
                path = self.compose(video_clips=clips, output_path=output_path, music_path=music_path)
                results.append(path)
            except Exception as e:
                logger.error(f"Failed to compose video {i}: {e}")
                results.append(f"ERROR: {e}")
        return results


# ── Default singleton for backward compatibility ─────────────────
_default_composer: VideoComposer | None = None


def get_composer() -> VideoComposer:
    global _default_composer
    if _default_composer is None:
        _default_composer = VideoComposer()
    return _default_composer


def compose_video(**kwargs) -> str:
    return get_composer().compose(**kwargs)


def batch_compose(**kwargs) -> list[str]:
    return get_composer().batch_compose(**kwargs)
