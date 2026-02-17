import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.product import Product

router = APIRouter()


@router.get("/")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.status == "active"))
    products = result.scalars().all()
    return products


@router.post("/")
async def create_product(
    name: str = Form(...),
    sku: str = Form(...),
    price: float = Form(...),
    style: str = Form(""),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Save uploaded product image
    product_id = uuid.uuid4()
    ext = Path(image.filename).suffix
    image_path = f"{settings.assets_dir}/products/{product_id}{ext}"
    Path(image_path).parent.mkdir(parents=True, exist_ok=True)

    with open(image_path, "wb") as f:
        content = await image.read()
        f.write(content)

    product = Product(
        id=product_id,
        name=name,
        sku=sku,
        price=price,
        style=style,
        image_path=image_path,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/{product_id}")
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one()
