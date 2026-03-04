"""Custom exception hierarchy for SmartShop AI."""


class SmartShopError(Exception):
    """Base exception for all SmartShop AI errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: dict | None = None,
    ):
        super().__init__(message)
        self.user_message = user_message or "Something went wrong. Please try again."
        self.context = context or {}


class AgentTimeoutError(SmartShopError):
    """Raised when an agent's LLM call times out."""


class AgentRateLimitError(SmartShopError):
    """Raised when the LLM provider rate-limits a request."""


class AgentResponseError(SmartShopError):
    """Raised when an agent receives an invalid or unexpected response."""


class DatabaseError(SmartShopError):
    """Raised on database connectivity or query errors."""


class DataQualityError(SmartShopError):
    """Raised when ingested data fails quality checks."""


class CacheError(SmartShopError):
    """Raised on cache read/write errors."""
