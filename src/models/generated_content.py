import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class GeneratedContent(Base):
    """Tracks all generated try-on images and videos."""

    __tablename__ = "generated_content"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    model_image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_images.id"))
    content_type: Mapped[str] = mapped_column(String(20))  # tryon_image, raw_video, final_video
    file_path: Mapped[str] = mapped_column(String(500))
    s3_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, done, failed
    publish_status: Mapped[str] = mapped_column(String(20), default="unpublished")  # unpublished, published
    platform: Mapped[str] = mapped_column(String(50), default="")  # tiktok, instagram, youtube, etc.
    caption: Mapped[str] = mapped_column(Text, default="")
