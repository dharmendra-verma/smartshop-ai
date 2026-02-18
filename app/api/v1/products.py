"""Product API endpoints — v1."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse, ProductListResponse

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    db: Session = Depends(get_db),
):
    """List products with optional filtering and pagination."""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    total = query.count()
    pages = (total + page_size - 1) // page_size
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product
