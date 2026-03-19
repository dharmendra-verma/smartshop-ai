"""Tests for SCRUM-68: AI routing accuracy — confidence gating, comparison mode,
hallucination tracking, best_deal validation, FAISS threshold, fallback context."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.orchestrator.orchestrator import Orchestrator, reset_orchestrator
from app.agents.base import AgentResponse
from app.schemas.chat import IntentType


@pytest.fixture(autouse=True)
def reset():
    reset_orchestrator()
    yield
    reset_orchestrator()


def _agent(name="mock", success=True):
    a = MagicMock()
    a.name = name
    a.process = AsyncMock(
        return_value=AgentResponse(
            success=success,
            data={"agent": name, "answer": "ok"},
            error=None if success else "fail",
        )
    )
    return a


def _orch(registry=None):
    reg = registry or {
        "recommendation": _agent("rec"),
        "review": _agent("rev"),
        "price": _agent("price"),
        "policy": _agent("pol"),
        "general": _agent("gen"),
    }
    return Orchestrator(registry=reg)


def _intent(intent: IntentType, confidence=0.9, **kw):
    from app.agents.orchestrator.intent_classifier import _IntentResult

    return _IntentResult(intent=intent, confidence=confidence, reasoning="test", **kw)


# ---- Confidence Gating Tests ----


class TestConfidenceGating:
    @pytest.mark.asyncio
    async def test_low_confidence_routes_to_general(self):
        """Low confidence (<0.6) should route to general agent."""
        o = _orch()
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.RECOMMENDATION, confidence=0.3),
        ):
            resp, ir = await o.handle("something ambiguous", {})
        # general agent should have been called, not recommendation
        o._registry["general"].process.assert_called_once()
        o._registry["recommendation"].process.assert_not_called()

    @pytest.mark.asyncio
    async def test_high_confidence_routes_normally(self):
        """High confidence (>=0.6) should route to intended agent."""
        o = _orch()
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.RECOMMENDATION, confidence=0.85),
        ):
            resp, ir = await o.handle("Find laptops under $500", {})
        o._registry["recommendation"].process.assert_called_once()

    @pytest.mark.asyncio
    async def test_general_intent_not_gated(self):
        """General intent should not be redirected even with low confidence."""
        o = _orch()
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.GENERAL, confidence=0.0),
        ):
            resp, ir = await o.handle("hello", {})
        o._registry["general"].process.assert_called_once()

    @pytest.mark.asyncio
    async def test_exact_threshold_routes_normally(self):
        """Confidence exactly at threshold should route normally."""
        o = _orch()
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.PRICE, confidence=0.6),
        ):
            resp, ir = await o.handle("price of iPhone", {})
        o._registry["price"].process.assert_called_once()


# ---- Comparison Mode Tests ----


class TestComparisonMode:
    @pytest.mark.asyncio
    async def test_compare_mode_enriches_query(self):
        """compare_mode should be set in context for comparison intents."""
        o = _orch()
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.COMPARISON),
        ):
            await o.handle("Compare iPhone vs Samsung", {})
        ctx = o._registry["recommendation"].process.call_args[0][1]
        assert ctx.get("compare_mode") is True


# ---- Fallback Context Tests ----


class TestFallbackContext:
    @pytest.mark.asyncio
    async def test_fallback_passes_reason_when_agent_unavailable(self):
        """When agent is None, fallback should include reason and original intent."""
        o = _orch(
            {
                "recommendation": None,
                "review": _agent("rev"),
                "price": _agent("p"),
                "policy": None,
                "general": _agent("gen"),
            }
        )
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.RECOMMENDATION),
        ):
            await o.handle("Find laptops", {})
        ctx = o._registry["general"].process.call_args[0][1]
        assert "fallback_reason" in ctx
        assert "original_intent" in ctx
        assert ctx["original_intent"] == "recommendation"

    @pytest.mark.asyncio
    async def test_fallback_passes_context_on_agent_exception(self):
        """When agent raises, fallback context should include error info."""
        failing = _agent("rec")
        failing.process.side_effect = Exception("LLM timeout")
        o = _orch(
            {
                "recommendation": failing,
                "general": _agent("gen"),
                "review": _agent("rev"),
                "price": _agent("p"),
                "policy": None,
            }
        )
        with patch.object(
            o._classifier,
            "classify",
            new_callable=AsyncMock,
            return_value=_intent(IntentType.RECOMMENDATION),
        ):
            await o.handle("Find laptops", {})
        ctx = o._registry["general"].process.call_args[0][1]
        assert "fallback_reason" in ctx
        assert "LLM timeout" in ctx["fallback_reason"]


# ---- Hallucination Tracking Tests ----


class TestHallucinationTracking:
    def test_hydrate_returns_hallucinated_ids(self):
        from app.agents.recommendation.agent import (
            _hydrate_recommendations,
            _RecommendationOutput,
            _ProductResult,
        )

        output = _RecommendationOutput(
            recommendations=[
                _ProductResult(
                    product_id="PROD001", relevance_score=0.9, reason="great"
                ),
                _ProductResult(
                    product_id="FAKE_ID", relevance_score=0.8, reason="hallucinated"
                ),
            ],
            reasoning_summary="test",
        )
        mock_db = MagicMock()
        mock_product = MagicMock()
        mock_product.to_dict.return_value = {
            "id": "PROD001",
            "name": "iPhone",
            "relevance_score": 0.9,
        }
        # First call returns product, second returns None (hallucinated)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_product,
            None,
        ]
        deps = MagicMock()
        deps.db = mock_db

        results, hallucinated = _hydrate_recommendations(output, deps)
        assert len(results) == 1
        assert hallucinated == ["FAKE_ID"]

    def test_hydrate_no_hallucinations(self):
        from app.agents.recommendation.agent import (
            _hydrate_recommendations,
            _RecommendationOutput,
            _ProductResult,
        )

        output = _RecommendationOutput(
            recommendations=[
                _ProductResult(
                    product_id="PROD001", relevance_score=0.9, reason="great"
                ),
            ],
            reasoning_summary="test",
        )
        mock_db = MagicMock()
        mock_product = MagicMock()
        mock_product.to_dict.return_value = {"id": "PROD001", "name": "iPhone"}
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        deps = MagicMock()
        deps.db = mock_db

        results, hallucinated = _hydrate_recommendations(output, deps)
        assert len(results) == 1
        assert hallucinated == []


# ---- Price Agent best_deal Validation Tests ----


class TestBestDealValidation:
    def _make_product(self, name, product_id="P1"):
        from app.agents.price.agent import _ProductComparison, _PricePoint

        return _ProductComparison(
            product_id=product_id,
            name=name,
            our_price=999.0,
            competitor_prices=[_PricePoint(source="Amazon", price=979.0)],
            best_price=979.0,
            best_source="Amazon",
            savings_pct=2.0,
        )

    @pytest.mark.asyncio
    async def test_valid_best_deal_unchanged(self):
        from app.agents.price.agent import PriceComparisonAgent, _ComparisonOutput

        agent = PriceComparisonAgent()
        mock_output = MagicMock()
        mock_output.output = _ComparisonOutput(
            products=[
                self._make_product("iPhone 15", "P1"),
                self._make_product("Galaxy S24", "P2"),
            ],
            best_deal="iPhone 15",
            recommendation="iPhone 15 is the best value.",
        )
        mock_output.usage.return_value = MagicMock(
            input_tokens=100, output_tokens=50, total_tokens=150
        )

        deps = MagicMock()
        with patch.object(agent._agent, "run", new_callable=AsyncMock) as m:
            m.return_value = mock_output
            resp = await agent.process("compare phones", {"deps": deps})

        assert resp.data["best_deal"] == "iPhone 15"

    @pytest.mark.asyncio
    async def test_hallucinated_best_deal_corrected(self):
        from app.agents.price.agent import PriceComparisonAgent, _ComparisonOutput

        agent = PriceComparisonAgent()
        mock_output = MagicMock()
        mock_output.output = _ComparisonOutput(
            products=[
                self._make_product("iPhone 15", "P1"),
                self._make_product("Galaxy S24", "P2"),
            ],
            best_deal="Pixel 9 Pro",  # hallucinated — not in products
            recommendation="Pixel 9 Pro is great.",
        )
        mock_output.usage.return_value = MagicMock(
            input_tokens=100, output_tokens=50, total_tokens=150
        )

        deps = MagicMock()
        with patch.object(agent._agent, "run", new_callable=AsyncMock) as m:
            m.return_value = mock_output
            resp = await agent.process("compare phones", {"deps": deps})

        # Should be corrected to first product
        assert resp.data["best_deal"] == "iPhone 15"


# ---- FAISS Similarity Threshold Tests ----


class TestFaissSimilarityThreshold:
    def test_low_score_results_filtered(self):
        from app.agents.policy.vector_store import PolicyVectorStore

        import numpy as np

        vs = PolicyVectorStore.__new__(PolicyVectorStore)
        vs._metadata = [
            {
                "policy_id": 1,
                "policy_type": "return",
                "text": "30-day returns",
                "description": "30-day returns",
                "conditions": "receipt required",
            },
            {
                "policy_id": 2,
                "policy_type": "shipping",
                "text": "free shipping",
                "description": "free shipping",
                "conditions": "over $50",
            },
        ]
        # Mock FAISS index
        mock_index = MagicMock()
        mock_index.ntotal = 2
        # First result high score, second below threshold
        mock_index.search.return_value = (
            np.array([[0.85, 0.2]], dtype=np.float32),
            np.array([[0, 1]], dtype=np.int64),
        )
        vs._index = mock_index

        with patch.object(vs, "_embed_batch", return_value=np.zeros((1, 1536))):
            results = vs.search("return policy", k=3, min_score=0.4)

        assert len(results) == 1
        assert results[0].policy_type == "return"
        assert results[0].score == pytest.approx(0.85)

    def test_all_results_above_threshold_returned(self):
        from app.agents.policy.vector_store import PolicyVectorStore

        import numpy as np

        vs = PolicyVectorStore.__new__(PolicyVectorStore)
        vs._metadata = [
            {
                "policy_id": 1,
                "policy_type": "return",
                "text": "30-day returns",
                "description": "30-day returns",
                "conditions": "receipt required",
            },
        ]
        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_index.search.return_value = (
            np.array([[0.9]], dtype=np.float32),
            np.array([[0]], dtype=np.int64),
        )
        vs._index = mock_index

        with patch.object(vs, "_embed_batch", return_value=np.zeros((1, 1536))):
            results = vs.search("return", k=3, min_score=0.4)

        assert len(results) == 1

    def test_all_results_below_threshold_returns_empty(self):
        from app.agents.policy.vector_store import PolicyVectorStore

        import numpy as np

        vs = PolicyVectorStore.__new__(PolicyVectorStore)
        vs._metadata = [
            {
                "policy_id": 1,
                "policy_type": "return",
                "text": "30-day returns",
                "description": "desc",
                "conditions": "cond",
            },
        ]
        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_index.search.return_value = (
            np.array([[0.1]], dtype=np.float32),
            np.array([[0]], dtype=np.int64),
        )
        vs._index = mock_index

        with patch.object(vs, "_embed_batch", return_value=np.zeros((1, 1536))):
            results = vs.search("totally irrelevant", k=3, min_score=0.4)

        assert len(results) == 0
