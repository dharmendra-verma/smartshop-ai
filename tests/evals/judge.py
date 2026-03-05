"""LLM-as-judge for evaluating SmartShop AI agent response quality.

Uses GPT-4o-mini to score responses on five dimensions:
  relevance, correctness, reasoning_quality, helpfulness, overall

Usage:
    judge = LLMJudge()
    score = await judge.evaluate(query, response_text, agent_type="recommendation")
    assert score.overall >= 0.70
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Judge scoring schema
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an expert quality evaluator for SmartShop AI, an e-commerce
shopping assistant. Evaluate the assistant's response to the given user query on five dimensions,
each scored 0.0 (terrible) to 1.0 (excellent).

Scoring guide:
- relevance       : Does the response directly address what the user asked?
                    0.0 = completely off-topic | 0.5 = tangentially related | 1.0 = fully on-point
- correctness     : Is the information plausible, internally consistent, and appropriate?
                    0.0 = factually wrong / contradictory | 0.5 = partially correct | 1.0 = sound
- reasoning_quality: Does the response show coherent, well-structured reasoning?
                    0.0 = no reasoning | 0.5 = some reasoning visible | 1.0 = clear & logical
- helpfulness     : Would this response genuinely help the user accomplish their goal?
                    0.0 = useless | 0.5 = somewhat helpful | 1.0 = very helpful
- overall         : Holistic assessment — use this calibration:
                    < 0.50  = poor  |  0.50-0.70 = mediocre  |  0.70-0.85 = good  |  0.85+ = excellent

Provide a concise one-sentence explanation of your assessment."""


class EvalScore(BaseModel):
    """Structured evaluation scores from the LLM judge."""

    relevance: float = Field(ge=0.0, le=1.0, description="Query relevance (0–1)")
    correctness: float = Field(ge=0.0, le=1.0, description="Factual correctness (0–1)")
    reasoning_quality: float = Field(ge=0.0, le=1.0, description="Quality of reasoning (0–1)")
    helpfulness: float = Field(ge=0.0, le=1.0, description="Helpfulness to the user (0–1)")
    overall: float = Field(ge=0.0, le=1.0, description="Overall quality (0–1)")
    explanation: str = Field(description="One-sentence explanation of scores")

    @property
    def average(self) -> float:
        """Mean of the four primary dimensions (excludes 'overall')."""
        return (
            self.relevance + self.correctness + self.reasoning_quality + self.helpfulness
        ) / 4

    def __str__(self) -> str:
        return (
            f"overall={self.overall:.2f} "
            f"[relevance={self.relevance:.2f} correctness={self.correctness:.2f} "
            f"reasoning={self.reasoning_quality:.2f} helpfulness={self.helpfulness:.2f}] "
            f"— {self.explanation}"
        )


# ---------------------------------------------------------------------------
# Eval test case dataclass
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    """A single LLM-as-judge evaluation case."""

    name: str
    query: str
    agent_type: str          # "recommendation" | "review" | "price" | "policy" | "general"
    response_text: str       # Formatted response text presented to the judge

    # Optional context hint for the judge
    context: str = ""

    # Minimum score thresholds (set > 0 to enforce)
    min_relevance: float = 0.0
    min_correctness: float = 0.0
    min_reasoning_quality: float = 0.0
    min_helpfulness: float = 0.0
    min_overall: float = 0.0

    # Maximum score thresholds (set < 1 to enforce — used for "bad" response cases)
    max_relevance: float = 1.0
    max_correctness: float = 1.0
    max_reasoning_quality: float = 1.0
    max_helpfulness: float = 1.0
    max_overall: float = 1.0

    # Human-readable tags for grouping / reporting
    tags: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM Judge
# ---------------------------------------------------------------------------


class LLMJudge:
    """LLM-as-judge that scores SmartShop AI agent responses on multiple quality dimensions."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self._model_name = model_name
        self._agent: Agent = Agent(
            model=OpenAIModel(model_name),
            output_type=EvalScore,
            instructions=JUDGE_SYSTEM_PROMPT,
        )

    async def evaluate(
        self,
        query: str,
        response: str,
        agent_type: str = "",
        context: str = "",
    ) -> EvalScore:
        """Score a single agent response.

        Args:
            query:       The user's original query.
            response:    The agent's response text to evaluate.
            agent_type:  Label for the agent (e.g. "recommendation").
            context:     Optional evaluation context / criteria hint for the judge.

        Returns:
            EvalScore with per-dimension scores and an explanation.
        """
        prompt_parts: list[str] = []
        if agent_type:
            prompt_parts.append(f"Agent Type: {agent_type}")
        if context:
            prompt_parts.append(f"Evaluation Context: {context}")
        prompt_parts.append(f"User Query: {query}")
        prompt_parts.append(f"Agent Response:\n{response}")

        prompt = "\n\n".join(prompt_parts)

        result = await self._agent.run(prompt, usage_limits=UsageLimits(request_limit=3))
        score = result.output

        logger.info(
            "Judge [%s] Q=%r → %s",
            agent_type or "unknown",
            query[:60],
            str(score),
        )
        return score

    async def compare(
        self,
        query: str,
        good_response: str,
        bad_response: str,
        agent_type: str = "",
        context: str = "",
    ) -> tuple[EvalScore, EvalScore]:
        """Score two responses concurrently.

        Returns:
            (good_score, bad_score) — used for judge calibration tests.
        """
        good_score, bad_score = await asyncio.gather(
            self.evaluate(query, good_response, agent_type, context),
            self.evaluate(query, bad_response, agent_type, context),
        )
        return good_score, bad_score

    async def run_case(self, case: EvalCase) -> EvalScore:
        """Run a single EvalCase and return the score (does not assert)."""
        return await self.evaluate(
            query=case.query,
            response=case.response_text,
            agent_type=case.agent_type,
            context=case.context,
        )

    async def run_suite(self, cases: list[EvalCase]) -> list[tuple[EvalCase, EvalScore]]:
        """Run a list of EvalCases concurrently.

        Returns:
            List of (case, score) pairs.
        """
        scores = await asyncio.gather(*[self.run_case(c) for c in cases])
        return list(zip(cases, scores))
