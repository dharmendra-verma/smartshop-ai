# SmartShop AI — Eval Test Architecture

## Overview

The eval test suite uses an **LLM-as-judge** pattern to evaluate the quality of agent responses. Real agents process queries against mocked data, and a separate LLM judge scores the responses on multiple quality dimensions.

## How to Run

```bash
# All eval tests (requires real OpenAI API key)
RUN_EVALS=1 pytest tests/evals/ -v -m eval

# Single eval file
RUN_EVALS=1 pytest tests/evals/test_eval_recommendation.py -v

# With verbose judge output
RUN_EVALS=1 pytest tests/evals/ -v -m eval -s
```

Tests are **opt-in** — skipped by default unless `RUN_EVALS=1` is set to avoid accidental API costs in CI.

## File Structure

```
tests/evals/
├── __init__.py                        # Package marker
├── conftest.py                        # Skip logic, shared fixtures, mock data
├── judge.py                           # LLMJudge + EvalScore + EvalCase
├── test_eval_judge.py                 # Judge calibration (good vs bad ranking)
├── test_eval_intent_classifier.py     # Intent routing accuracy
├── test_eval_recommendation.py        # RecommendationAgent quality
├── test_eval_review.py                # ReviewSummarizationAgent quality
├── test_eval_price.py                 # PriceComparisonAgent quality
├── test_eval_policy.py                # PolicyAgent quality
├── test_eval_general.py               # GeneralResponseAgent quality
└── test_eval_orchestrator.py          # End-to-end orchestrator routing
```

## Gate: Skip Logic (`conftest.py`)

Before any eval test runs, two checks happen:

```
Has OPENAI_API_KEY? ──no──> SKIP ALL
        | yes
Has RUN_EVALS=1?   ──no──> SKIP ALL
        | yes
        v
    Run eval tests (real LLM API calls)
```

This is implemented in `pytest_collection_modifyitems()` — it auto-marks every test under `tests/evals/` with `pytest.mark.skip` unless both flags are set.

## The Judge (`judge.py`)

The core evaluation engine — uses GPT-4o-mini to grade agent responses on 5 dimensions.

### EvalScore (Pydantic model)

| Dimension           | What it measures                                   |
|---------------------|----------------------------------------------------|
| `relevance`         | Does the response address the user's query?        |
| `correctness`       | Is the information accurate and consistent?        |
| `reasoning_quality` | Is the reasoning coherent and well-structured?     |
| `helpfulness`       | Would this actually help the user?                 |
| `overall`           | Holistic assessment (0.50=mediocre, 0.70+=good, 0.85+=excellent) |

All scores are floats from 0.0 to 1.0.

### LLMJudge Class

| Method                          | Purpose                                         |
|---------------------------------|-------------------------------------------------|
| `evaluate(query, response, ...)`| Score a single response -> `EvalScore`           |
| `compare(query, good, bad)`     | Score two responses concurrently                 |
| `run_case(EvalCase)`            | Evaluate a structured test case                  |
| `run_suite([EvalCase])`         | Run multiple cases concurrently via asyncio.gather |

The judge is a **pydantic-ai Agent** with `output_type=EvalScore`, so GPT-4o-mini returns structured scores directly.

### EvalCase (Dataclass)

A structured test case containing:
- `query`, `response_text`, `agent_type`
- Min/max score thresholds per dimension (e.g., `min_overall=0.70`, `max_overall=0.45`)
- Optional `context` hint for the judge
- `tags` for grouping/reporting

## Shared Fixtures & Mock Data (`conftest.py`)

### Fixtures

- **`judge`** (session-scoped): `LLMJudge` instance — created once, reused across all test files
- **`make_mock_db()`**: Creates a mock SQLAlchemy session pre-loaded with test data. Chains all query methods (`.filter()`, `.order_by()`, `.limit()`, etc.) so any DB query returns the seeded data

### Test Data

| Constant           | Contents                                          |
|--------------------|---------------------------------------------------|
| `SAMPLE_PRODUCTS`  | 7 products (3 smartphones, 2 laptops, 2 headphones) |
| `SAMPLE_REVIEWS`   | 5 reviews (3 for Sony headphones, 2 for Budget Phone) |
| `SAMPLE_POLICIES`  | 3 policies (return, shipping, warranty)            |

### Response Formatter

`format_agent_response(result, agent_type)` converts an `AgentResponse` into human-readable text for the judge. Handles different response shapes: recommendations, reviews, prices, policies, and general responses.

## How an Eval Test Runs (Step-by-Step)

Taking `test_recommendation_budget_smartphones` as an example:

```
Step 1: Setup
+-- agent = RecommendationAgent()          <-- real agent with real LLM
+-- db = make_mock_db(SAMPLE_PRODUCTS)     <-- mocked DB with 7 products
+-- deps = AgentDependencies(db, settings)

Step 2: Agent Call (REAL LLM)
+-- agent.process("Find me budget smartphones under $300", context)
+-- GPT-4o-mini calls tools -> mock DB returns SAMPLE_PRODUCTS
+-- GPT-4o-mini reasons over products, picks matches
+-- Returns AgentResponse with recommendations

Step 3: Format for Judge
+-- format_agent_response(result) -> readable text like:
|   "Recommended Products:
|     1. Budget Phone X1 - $249.99 | Rating: 4.2
|        Reason: Best-value 5G smartphone under $300..."

Step 4: Judge Call (REAL LLM)
+-- judge.evaluate(query, response_text, "recommendation")
+-- GPT-4o-mini scores on 5 dimensions
+-- Returns EvalScore(relevance=0.90, correctness=0.85, ...)

Step 5: Assert
+-- assert result.success == True
+-- assert score.overall >= 0.65    <-- quality threshold
```

### Visual Flow

```
User Query --> Real Agent (GPT-4o-mini) --> AgentResponse
                    |                              |
              Mock DB (tools)              format_agent_response()
                                                   |
                                           Formatted Text
                                                   |
                                    LLM Judge (GPT-4o-mini) --> EvalScore
                                                                    |
                                                            assert overall >= 0.65
```

## Judge Calibration (`test_eval_judge.py`)

Before trusting the judge, these tests verify the judge itself is reliable:

| Test                                        | What it checks                                        |
|---------------------------------------------|-------------------------------------------------------|
| `test_judge_scores_good_response_above_threshold` | Pre-written good responses score `overall >= 0.70`  |
| `test_judge_scores_bad_response_below_threshold`  | Pre-written bad responses score `overall <= 0.45`   |
| `test_judge_ranks_good_above_bad`                 | For every pair: `good_score.overall > bad_score.overall` |

3 calibration test types x 5 agent types = 15 calibration checks.

Example calibration pair (recommendation):
- **Good**: "Budget Phone X1 - $249.99 | Rating: 4.2 | Reason: Best-value 5G under $300..."
- **Bad**: "I'm not sure what you're looking for. The weather today is sunny and 22C."

Plus edge case tests:
- Error responses (`[AGENT ERROR]`) should score < 0.50
- Judge always returns valid `EvalScore` with all fields 0.0-1.0

## What Each Eval Test File Covers

| File                             | Real LLM calls    | Mocked                        | Key Tests                                         |
|----------------------------------|-------------------|-------------------------------|----------------------------------------------------|
| `test_eval_judge.py`            | Judge only        | Nothing (synthetic responses) | Judge calibration — good vs bad ranking            |
| `test_eval_intent_classifier.py`| Classifier only   | Nothing                       | Intent + entity extraction accuracy                |
| `test_eval_recommendation.py`   | Agent + Judge     | DB                            | Budget, premium, comparison, reasoning, consistency|
| `test_eval_review.py`           | Agent + Judge     | DB + reviews                  | Sentiment accuracy, balanced pros/cons             |
| `test_eval_price.py`            | Agent + Judge     | DB + pricing service          | Best-deal identification, price reasoning          |
| `test_eval_policy.py`           | Agent + Judge     | DB + FAISS vector store       | Return/shipping/warranty policy accuracy           |
| `test_eval_general.py`          | Agent + Judge     | Nothing                       | Greetings, off-topic redirects, conciseness        |
| `test_eval_orchestrator.py`     | IntentClassifier + Judge | Specialist agents (pre-baked) | Routing accuracy across all intent types    |

## Cost per Run

Each test makes **2 real LLM calls** (agent + judge):
- ~40-50 API calls per full suite
- ~$0.01-0.02 total (gpt-4o-mini pricing)
- That is why it is opt-in with `RUN_EVALS=1`
