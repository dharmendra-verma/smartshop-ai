"""Review model for customer product reviews."""

from sqlalchemy import Column, Integer, String, Text, Float, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship, backref

from app.core.database import Base


class Review(Base):
    """Customer review model."""

    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(
        String(20),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Float, nullable=False)
    text = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    review_date = Column(Date, nullable=True)

    product = relationship("Product", backref=backref("reviews", passive_deletes=True))

    __table_args__ = (
        CheckConstraint("rating >= 1.0 AND rating <= 5.0", name="check_rating_range"),
        Index("idx_review_product_rating", "product_id", "rating"),
        Index("idx_review_sentiment", "sentiment"),
        Index("idx_review_date", "review_date"),
    )

    def __repr__(self) -> str:
        return f"<Review(review_id={self.review_id}, product_id='{self.product_id}', rating={self.rating})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "review_id": self.review_id,
            "product_id": self.product_id,
            "rating": self.rating,
            "text": self.text,
            "sentiment": self.sentiment,
            "review_date": self.review_date.isoformat() if self.review_date else None,
        }
