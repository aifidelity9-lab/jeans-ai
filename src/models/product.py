from sqlalchemy import String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Product(Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    image_path: Mapped[str] = mapped_column(String(500))  # flat-lay / hanging photo
    category: Mapped[str] = mapped_column(String(100), default="jeans")
    style: Mapped[str] = mapped_column(String(100), default="")  # skinny, bootcut, wide-leg, etc.
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived
