"""Base agent class for all specialized agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Cost per 1M tokens by model (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
}
DEFAULT_PRICING = {"input": 0.15, "output": 0.60}


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

    def log_usage(self, result, model_name: str = "gpt-4o-mini") -> Dict[str, Any]:
        """Log token usage and estimated cost from a pydantic-ai run result."""
        usage = result.usage()
        input_tk = usage.input_tokens or 0
        output_tk = usage.output_tokens or 0
        total_tk = usage.total_tokens or 0
        requests = usage.requests or 0

        pricing = MODEL_PRICING.get(model_name, DEFAULT_PRICING)
        cost = (input_tk * pricing["input"] + output_tk * pricing["output"]) / 1_000_000

        logger.info(
            "%s usage | tokens: %d in + %d out = %d total | "
            "requests: %d | est. cost: $%.6f",
            self.name,
            input_tk,
            output_tk,
            total_tk,
            requests,
            cost,
        )

        return {
            "input_tokens": input_tk,
            "output_tokens": output_tk,
            "total_tokens": total_tk,
            "requests": requests,
            "estimated_cost_usd": round(cost, 6),
        }

    def _handle_agent_error(self, exc: Exception, query: str = "") -> AgentResponse:
        """
        Shared error handler for all agents.
        - RateLimitError → record_failure + raise AgentRateLimitError
        - Timeout        → record_failure + raise AgentTimeoutError
        - Anything else  → log + record_failure + return failure AgentResponse
        """
        from app.core.exceptions import AgentRateLimitError, AgentTimeoutError
        from app.core.alerting import record_failure

        exc_type = type(exc).__name__
        if "RateLimitError" in exc_type:
            record_failure(self.name)
            raise AgentRateLimitError(
                f"OpenAI rate limit: {exc}",
                user_message="I'm experiencing high demand. Please try again in a moment.",
                context={"agent": self.name, "query": query[:100]},
            ) from exc
        if "Timeout" in exc_type:
            record_failure(self.name)
            raise AgentTimeoutError(
                f"OpenAI timeout: {exc}",
                user_message="The AI assistant is taking too long. Please try again.",
                context={"agent": self.name},
            ) from exc
        logger.error("%s failed: %s", self.name, exc, exc_info=True)
        record_failure(self.name)
        return AgentResponse(
            success=False,
            data={},
            error="Service temporarily unavailable.",
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
