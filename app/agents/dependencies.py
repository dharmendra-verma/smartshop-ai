"""Shared dependency container for all pydantic-ai agents."""

from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings


@dataclass
class AgentDependencies:
    """
    Injected into all pydantic-ai agent tools via RunContext[AgentDependencies].

    Shared by: RecommendationAgent, ReviewAgent, PriceAgent, PolicyAgent, Orchestrator.
    Extended by individual agents if they need additional deps (e.g. vector store for SCRUM-15).
    """
    db: Session
    settings: Settings

    @classmethod
    def from_db(cls, db: Session) -> "AgentDependencies":
        """Convenience constructor used in FastAPI endpoints."""
        return cls(db=db, settings=get_settings())
