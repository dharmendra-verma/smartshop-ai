"""LLM-based intent classifier with structured output."""

import logging
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits
from app.core.config import get_settings
from app.schemas.chat import IntentType

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = """Classify user queries for a shopping assistant into one of:
- recommendation: wants product suggestions ("Find laptops under $800")
- comparison:     wants to compare products ("Compare iPhone vs Samsung")
- review:         wants customer opinion ("What do reviews say about X?")
- policy:         asks about store policies ("What's the return policy?")
- price:          wants price comparison across retailers ("Best price for Galaxy S24?")
- general:        anything else (greetings, service questions)

Extract entities: product_name, category, max_price (USD float), min_price (USD float).
Be accurate and concise."""


@dataclass
class _ClassifierDeps:
    pass


class _IntentResult(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    product_name: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    reasoning: str = Field(description="One-sentence explanation")
    classification_failed: bool = Field(
        default=False,
        description="True when classification failed and result is a fallback",
    )


class IntentClassifier:
    """Classifies intent using GPT-4o-mini. Falls back to GENERAL on any failure."""

    def __init__(self, model_name: str | None = None):
        s = get_settings()
        self._agent: Agent[_ClassifierDeps, _IntentResult] = Agent(
            model=OpenAIModel(model_name or s.OPENAI_MODEL),
            deps_type=_ClassifierDeps,
            output_type=_IntentResult,
            instructions=CLASSIFIER_PROMPT,
        )

    async def classify(self, query: str) -> _IntentResult:
        try:
            result = await self._agent.run(
                query, deps=_ClassifierDeps(), usage_limits=UsageLimits(request_limit=5)
            )
            usage = result.usage()
            input_tk = usage.input_tokens or 0
            output_tk = usage.output_tokens or 0
            cost = (input_tk * 0.15 + output_tk * 0.60) / 1_000_000
            logger.info(
                "Intent: '%s' → %s (%.2f) | tokens: %d in + %d out | cost: $%.6f",
                query[:60],
                result.output.intent,
                result.output.confidence,
                input_tk,
                output_tk,
                cost,
            )
            return result.output
        except Exception as exc:
            logger.error("IntentClassifier failed: %s — defaulting to GENERAL", exc)
            return _IntentResult(
                intent=IntentType.GENERAL,
                confidence=0.0,
                reasoning=f"Classification failed: {exc}",
                classification_failed=True,
            )
