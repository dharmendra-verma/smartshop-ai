"""Review model for customer product reviews."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.core.database import Base


class Review(Base):
    """Customer review model."""

    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product = relationship("Product", backref=backref("reviews", passive_deletes=True))

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        Index("idx_review_product_rating", "product_id", "rating"),
        Index("idx_review_sentiment", "sentiment"),
        Index("idx_review_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Review(review_id={self.review_id}, product_id={self.product_id}, rating={self.rating})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "review_id": self.review_id,
            "product_id": self.product_id,
            "rating": self.rating,
            "review_text": self.review_text,
            "sentiment": self.sentiment,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
