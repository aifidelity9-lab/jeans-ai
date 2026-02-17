from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ModelImage(Base):
    """Base model (person) images for virtual try-on."""

    __tablename__ = "model_images"

    name: Mapped[str] = mapped_column(String(100))  # e.g. "caucasian_female_01"
    image_path: Mapped[str] = mapped_column(String(500))
    ethnicity: Mapped[str] = mapped_column(String(50))  # for diversity tracking
    body_type: Mapped[str] = mapped_column(String(50), default="")  # slim, regular, plus
    pose: Mapped[str] = mapped_column(String(50), default="standing")  # standing, walking, sitting
    status: Mapped[str] = mapped_column(String(20), default="active")
