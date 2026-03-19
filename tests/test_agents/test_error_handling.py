"""Tests for SCRUM-69: Hardened error handling — general agent, intent classifier,
session parse alerting, and endpoint error boundaries."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


# ---- GeneralResponseAgent Tests ----


class TestGeneralResponseAgentErrorHandling:
    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        from app.agents.orchestrator.general_agent import GeneralResponseAgent

        agent = GeneralResponseAgent()
        with patch.object(agent._llm, "run", side_effect=RuntimeError("LLM down")):
            resp = await agent.process("hello", {})
        assert resp.success is False
        assert resp.error is not None
        assert "RuntimeError" in resp.error

    @pytest.mark.asyncio
    async def test_still_provides_fallback_answer(self):
        from app.agents.orchestrator.general_agent import GeneralResponseAgent

        agent = GeneralResponseAgent()
        with patch.object(agent._llm, "run", side_effect=Exception("fail")):
            resp = await agent.process("hello", {})
        assert "answer" in resp.data
        assert "help" in resp.data["answer"].lower()

    @pytest.mark.asyncio
    async def test_records_failure_on_any_exception(self):
        from app.agents.orchestrator.general_agent import GeneralResponseAgent

        agent = GeneralResponseAgent()
        with (
            patch.object(agent._llm, "run", side_effect=ValueError("bad")),
            patch("app.core.alerting.record_failure") as mock_rf,
        ):
            await agent.process("hello", {})
        mock_rf.assert_called_once_with("general-agent")


# ---- IntentClassifier Tests ----


class TestIntentClassifierFailureFlag:
    @pytest.mark.asyncio
    async def test_classification_failed_true_on_error(self):
        from app.agents.orchestrator.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        with patch.object(
            classifier._agent, "run", side_effect=RuntimeError("LLM timeout")
        ):
            result = await classifier.classify("find laptops")
        assert result.classification_failed is True
        assert result.confidence == 0.0
        assert result.intent.value == "general"

    @pytest.mark.asyncio
    async def test_classification_failed_false_on_success(self):
        from app.agents.orchestrator.intent_classifier import (
            IntentClassifier,
            _IntentResult,
        )
        from app.schemas.chat import IntentType

        classifier = IntentClassifier()
        mock_result = MagicMock()
        mock_result.output = _IntentResult(
            intent=IntentType.RECOMMENDATION,
            confidence=0.9,
            reasoning="clear product request",
        )
        mock_result.usage.return_value = MagicMock(input_tokens=50, output_tokens=20)
        with patch.object(classifier._agent, "run", new_callable=AsyncMock) as m:
            m.return_value = mock_result
            result = await classifier.classify("find laptops")
        assert result.classification_failed is False


# ---- Session Parse Alerting Tests ----


class TestSessionParseAlerting:
    def test_parse_failure_calls_record_failure(self):
        from app.services.session.session_manager import SessionManager

        store = MagicMock()
        store.get.return_value = "not-valid-json{{"
        mgr = SessionManager(store=store)

        with patch("app.core.alerting.record_failure") as mock_rf:
            result = mgr.get_history("session-123")

        assert result == []
        mock_rf.assert_called_once_with("session_parse")

    def test_valid_json_no_alert(self):
        import json
        from app.services.session.session_manager import SessionManager

        store = MagicMock()
        store.get.return_value = json.dumps(
            [{"role": "user", "content": "hello", "timestamp": 1.0}]
        )
        mgr = SessionManager(store=store)

        with patch("app.core.alerting.record_failure") as mock_rf:
            result = mgr.get_history("session-123")

        assert len(result) == 1
        mock_rf.assert_not_called()


# ---- Endpoint Error Boundary Tests ----


class TestEndpointErrorBoundaries:
    @pytest.mark.asyncio
    async def test_recommendation_endpoint_503_on_unexpected_error(self):
        from app.api.v1.recommendations import get_recommendations
        from app.schemas.recommendation import RecommendationRequest

        request = RecommendationRequest(query="find laptops")
        mock_db = MagicMock()

        with (
            patch(
                "app.api.v1.recommendations.AgentDependencies.from_db",
                side_effect=Exception("DB connection lost"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_recommendations(request, mock_db)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_review_endpoint_503_on_unexpected_error(self):
        from app.api.v1.reviews import summarize_reviews
        from app.schemas.review import ReviewSummarizationRequest

        request = ReviewSummarizationRequest(query="summarize reviews for iPhone")
        mock_db = MagicMock()

        with (
            patch(
                "app.api.v1.reviews.AgentDependencies.from_db",
                side_effect=Exception("DB timeout"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await summarize_reviews(request, mock_db)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_price_endpoint_503_on_unexpected_error(self):
        from app.api.v1.price import compare_prices
        from app.schemas.price import PriceCompareRequest

        request = PriceCompareRequest(query="compare phones")
        mock_db = MagicMock()

        with (
            patch(
                "app.api.v1.price.AgentDependencies.from_db",
                side_effect=Exception("DB error"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await compare_prices(request, mock_db)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_policy_endpoint_503_on_unexpected_error(self):
        from app.api.v1.policy import ask_policy
        from app.schemas.policy import PolicyAskRequest

        request = PolicyAskRequest(query="return policy")
        mock_db = MagicMock()

        with (
            patch(
                "app.api.v1.policy.AgentDependencies.from_db",
                side_effect=Exception("DB error"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await ask_policy(request, mock_db)
        assert exc_info.value.status_code == 503
