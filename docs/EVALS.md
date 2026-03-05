# LLM-as-Judge Evaluation Framework

SmartShop AI includes an LLM-as-judge evaluation framework in `tests/evals/` that verifies **AI response quality** — relevance, correctness, reasoning, and helpfulness. These tests complement unit tests: unit tests verify plumbing, eval tests verify the quality of AI reasoning.

---

## Architecture

```
User query
    │
    ▼
┌─────────────────────────────────┐
│  Agent (e.g. RecommendationAgent)│  ← real LLM call (gpt-4o-mini)
│  mocked DB (SAMPLE_PRODUCTS)    │
└──────────────┬──────────────────┘
               │ AgentResponse
               ▼
┌──────────────────────────┐
│  format_agent_response()  │  ← converts data dict → readable string
└──────────┬───────────────┘
           │ response_text
           ▼
┌──────────────────────────┐
│  LLMJudge.evaluate()     │  ← real LLM call (gpt-4o-mini as judge)
│  JUDGE_SYSTEM_PROMPT      │
└──────────┬───────────────┘
           │ EvalScore
           ▼
┌──────────────────────────────────────┐
│  pytest assertions                    │
│  assert score.overall >= min_overall  │
└──────────────────────────────────────┘
```

---

## Core Classes

### EvalScore

**File:** `tests/evals/judge.py`

```python
class EvalScore(BaseModel):
    relevance: float          # Does response address the query? (0–1)
    correctness: float        # Is information plausible/accurate? (0–1)
    reasoning_quality: float  # Is reasoning coherent? (0–1)
    helpfulness: float        # Would this help the user? (0–1)
    overall: float            # Holistic quality score (0–1)
    explanation: str          # One-sentence judge reasoning

    @property
    def average(self) -> float:
        """Mean of 4 primary dimensions."""
```

### EvalCase

```python
@dataclass
class EvalCase:
    name: str           # Human-readable test case name
    query: str          # User query to evaluate
    agent_type: str     # "recommendation" | "review" | "price" | "policy" | "general"
    response_text: str  # Formatted agent response presented to judge
    context: str        # Optional evaluation hint for the judge
    min_overall: float  # Minimum passing threshold
    max_overall: float  # Maximum threshold (for bad-response tests)
```

### LLMJudge

```python
judge = LLMJudge(model_name="gpt-4o-mini")

# Score a single response
score: EvalScore = await judge.evaluate(query, response_text, agent_type, context)

# Score two responses concurrently (good vs bad)
good_score, bad_score = await judge.compare(query, good_response, bad_response)

# Run a full suite
results = await judge.run_suite(cases)  # → list[(EvalCase, EvalScore)]
```

---

## Score Calibration

| Response Quality | Expected `overall` |
|------------------|-------------------|
| Excellent | >= 0.85 |
| Good | 0.70 – 0.85 |
| Mediocre | 0.50 – 0.70 |
| Poor | < 0.50 |

Good responses assert `min_overall >= 0.65–0.70`. Bad/off-topic responses assert `max_overall <= 0.45`.

---

## Test File Index

| File | Tests | Purpose |
|------|-------|---------|
| `tests/evals/judge.py` | — | `LLMJudge`, `EvalScore`, `EvalCase` classes |
| `tests/evals/conftest.py` | — | Skip logic, shared fixtures, sample data, `make_mock_db()`, `format_agent_response()` |
| `test_eval_judge.py` | 18 | **Judge calibration** — good responses >= 0.70; bad responses <= 0.45; good ranks above bad |
| `test_eval_intent_classifier.py` | 20 | **Intent routing** — 12 query→intent pairs, entity extraction, confidence |
| `test_eval_recommendation.py` | 8 | **Recommendation quality** — budget filtering, use-case matching, comparisons |
| `test_eval_review.py` | 7 | **Review summary quality** — sentiment accuracy, pro/con balance |
| `test_eval_price.py` | 7 | **Price comparison quality** — competitive assessment, multi-store |
| `test_eval_policy.py` | 10 | **Policy answer accuracy** — return window, fees, shipping, warranty |
| `test_eval_general.py` | 13 | **General agent quality** — on-brand redirects, off-topic handling |
| `test_eval_orchestrator.py` | 14 | **E2E routing** — all 6 intents, context enrichment, graceful fallback |

**Total eval tests: 97**

---

## How to Run

```bash
# Run all evals (makes real OpenAI API calls)
RUN_EVALS=1 pytest tests/evals/ -v -m eval

# Run a single eval file
RUN_EVALS=1 pytest tests/evals/test_eval_judge.py -v -s

# Skip evals (default — no API calls)
pytest tests/evals/   # → 97 skipped
```

**Requirements:**
- `OPENAI_API_KEY` environment variable set
- `RUN_EVALS=1` opt-in flag

Without both, all eval tests are automatically skipped — zero API cost.

---

## Shared Test Data

Defined in `tests/evals/conftest.py`:

| Constant | Content |
|----------|---------|
| `SAMPLE_PRODUCTS` | 7 products (smartphones, laptops, headphones) with realistic prices/ratings |
| `SAMPLE_REVIEWS` | 5 reviews for PROD001 and PROD006 (mixed positive/neutral/negative) |
| `SAMPLE_POLICIES` | 3 policies (return 30d, shipping 5-7d, warranty 1yr) |

### Mock DB Helper

```python
db = make_mock_db(products=SAMPLE_PRODUCTS, reviews=SAMPLE_REVIEWS, policies=SAMPLE_POLICIES)
```

### Response Formatter

```python
text = format_agent_response(result: AgentResponse, agent_type: str) -> str
```

Converts structured agent response data into readable text suitable for judge evaluation.

---

## Adding an Eval Test for a New Agent

```python
# tests/evals/test_eval_newagent.py
import pytest
from app.agents.newagent.agent import NewAgent
from app.agents.dependencies import AgentDependencies
from tests.evals.conftest import SAMPLE_PRODUCTS, format_agent_response, make_mock_db
from app.core.config import get_settings

@pytest.mark.asyncio
@pytest.mark.eval
async def test_newagent_quality(judge):
    db = make_mock_db(products=SAMPLE_PRODUCTS)
    deps = AgentDependencies(db=db, settings=get_settings())
    agent = NewAgent()
    result = await agent.process("my query", context={"deps": deps})
    response_text = format_agent_response(result, "new")
    score = await judge.evaluate("my query", response_text, "new")
    assert result.success
    assert score.overall >= 0.65
```

Also add a good/bad calibration pair to `test_eval_judge.py`.

---

## CI Integration

- Eval tests are **opt-in** — `RUN_EVALS=1` + `OPENAI_API_KEY` required
- Regular `pytest` runs skip evals — zero API cost in CI
- Recommended: run evals before major releases or after prompt changes
- Average cost: ~$0.01–0.05 per full suite (97 tests x 2 LLM calls each)
