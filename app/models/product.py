"""Product model for e-commerce catalog."""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    """Product catalog model."""

    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    brand = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("idx_product_category_brand", "category", "brand"),
        Index("idx_product_price", "price"),
    )

    def __repr__(self) -> str:
        return f"<Product(product_id={self.product_id}, name='{self.name}', price={self.price})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price is not None else None,
            "brand": self.brand,
            "category": self.category,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
