"""Multi-agent orchestrator."""
import logging
from typing import Any
from app.agents.base import BaseAgent, AgentResponse
from app.agents.orchestrator.intent_classifier import IntentClassifier, _IntentResult
from app.agents.orchestrator.circuit_breaker import CircuitBreaker
from app.schemas.chat import IntentType

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, registry: dict[str, BaseAgent | None]):
        self._registry  = registry
        self._classifier = IntentClassifier()
        self._breakers   = {name: CircuitBreaker(name) for name in registry}

    async def handle(self, query: str, context: dict[str, Any]
                     ) -> tuple[AgentResponse, _IntentResult]:
        intent_result = await self._classifier.classify(query)
        intent_name   = intent_result.intent.value

        # Enrich context with extracted entities
        ctx = {**context}
        hints = {}
        if intent_result.category:    hints["category"]  = intent_result.category
        if intent_result.max_price:   hints["max_price"] = intent_result.max_price
        if intent_result.min_price:   hints["min_price"] = intent_result.min_price
        if hints: ctx["structured_hints"] = hints

        # "comparison" routes to recommendation with compare flag
        agent_key = intent_name
        if intent_name == "comparison":
            agent_key = "recommendation"; ctx["compare_mode"] = True

        agent   = self._registry.get(agent_key)
        breaker = self._breakers.get(agent_key)

        if agent is None or (breaker and not breaker.is_available()):
            logger.warning("Orchestrator: '%s' unavailable → general", agent_key)
            agent_key = "general"
            agent   = self._registry["general"]
            breaker = self._breakers["general"]

        try:
            response = await agent.process(query, ctx)
            if breaker:
                breaker.record_success() if response.success else breaker.record_failure()
            return response, intent_result
        except Exception as exc:
            logger.error("Orchestrator: '%s' raised: %s", agent_key, exc)
            if breaker: breaker.record_failure()
            fallback = self._registry.get("general")
            if fallback:
                return await fallback.process(query, context), intent_result
            return AgentResponse(success=False, data={}, error=str(exc)), intent_result


def build_orchestrator() -> "Orchestrator":
    from app.agents.recommendation.agent import RecommendationAgent
    from app.agents.review.agent import ReviewSummarizationAgent
    from app.agents.price.agent import PriceComparisonAgent
    from app.agents.orchestrator.general_agent import GeneralResponseAgent

    registry: dict[str, BaseAgent | None] = {
        "recommendation": RecommendationAgent(),
        "review":         ReviewSummarizationAgent(),
        "price":          PriceComparisonAgent(),
        "general":        GeneralResponseAgent(),
        "policy":         None,  # populated when SCRUM-15 is merged
    }
    try:
        from app.agents.policy.agent import PolicyAgent
        registry["policy"] = PolicyAgent()
        logger.info("Orchestrator: PolicyAgent registered")
    except ImportError:
        logger.info("Orchestrator: PolicyAgent not yet available (SCRUM-15 pending)")
    return Orchestrator(registry=registry)

_orchestrator: "Orchestrator | None" = None

def get_orchestrator() -> "Orchestrator":
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator

def reset_orchestrator():
    global _orchestrator
    _orchestrator = None
