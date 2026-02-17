"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Standard agent response format."""
    success: bool
    data: Dict[str, Any]
    error: str | None = None
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """Base class for all agents in SmartShop AI."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def process(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a user query and return a response.

        Args:
            query: User's natural language query
            context: Additional context (session, history, etc.)

        Returns:
            AgentResponse with success status and data
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
