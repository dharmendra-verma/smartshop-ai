"""Policy model for store policies."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class Policy(Base):
    """Store policy model."""

    __tablename__ = "policies"

    policy_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    conditions = Column(Text, nullable=False)
    timeframe = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("idx_policy_type_timeframe", "policy_type", "timeframe"),
    )

    def __repr__(self) -> str:
        return f"<Policy(policy_id={self.policy_id}, policy_type='{self.policy_type}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "policy_id": self.policy_id,
            "policy_type": self.policy_type,
            "description": self.description,
            "conditions": self.conditions,
            "timeframe": self.timeframe,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
