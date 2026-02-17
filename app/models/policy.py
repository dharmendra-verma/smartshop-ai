"""Policy model for store policies and FAQs."""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class Policy(Base):
    """Store policy model."""

    __tablename__ = "policies"

    policy_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)  # shipping, returns, privacy, etc.
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("idx_policy_category_effective", "category", "effective_date"),
    )

    def __repr__(self) -> str:
        return f"<Policy(policy_id={self.policy_id}, category='{self.category}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "policy_id": self.policy_id,
            "category": self.category,
            "question": self.question,
            "answer": self.answer,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
