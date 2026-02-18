"""Product model for e-commerce catalog."""

from sqlalchemy import Column, Integer, String, Text, Numeric, Float, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    """Product catalog model."""

    __tablename__ = "products"

    id = Column(String(20), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    brand = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=False, index=True)
    stock = Column(Integer, nullable=True, default=0)
    rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("idx_product_category_brand", "category", "brand"),
        Index("idx_product_price", "price"),
    )

    def __repr__(self) -> str:
        return f"<Product(id='{self.id}', name='{self.name}', price={self.price})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price is not None else None,
            "brand": self.brand,
            "category": self.category,
            "stock": self.stock,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
