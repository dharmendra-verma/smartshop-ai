# SCRUM-10: Develop Product Recommendation Agent with Pydantic AI

## Status: COMPLETED

## Time Tracking
- **Estimated**: 4-6 hours
- **Actual**: ~35 minutes

## Summary
Implemented the Product Recommendation Agent using pydantic-ai 1.61.0, establishing the foundational agent architecture pattern for all future agents (SCRUM-11, 14, 15, 16, 17). Includes shared dependency injection, tool-based reasoning, structured output, and TestModel-based unit tests.

## Files Created
| File | Purpose |
|------|---------|
| `app/agents/dependencies.py` | Shared `AgentDependencies` dataclass for DI across all agents |
| `app/agents/recommendation/__init__.py` | Package init, exports `RecommendationAgent` |
| `app/agents/recommendation/agent.py` | `RecommendationAgent` (BaseAgent subclass wrapping pydantic-ai Agent) |
| `app/agents/recommendation/tools.py` | DB query tools: `search_products_by_filters`, `get_product_details`, `get_categories` |
| `app/agents/recommendation/prompts.py` | System prompt with reasoning instructions and scoring guide |
| `app/api/v1/recommendations.py` | `POST /api/v1/recommendations` endpoint |
| `app/schemas/recommendation.py` | Request/response Pydantic models for the API |
| `tests/test_agents/test_recommendation_agent.py` | 14 tests using TestModel (no real API calls) |

## Files Modified
| File | Changes |
|------|---------|
| `requirements.txt` | Upgraded `pydantic-ai` from `0.0.13` (broken) to `>=1.0.0,<2.0.0` |
| `app/api/v1/__init__.py` | Added recommendations router |

## API Changes
- pydantic-ai 1.61.0 uses `output_type` (not `result_type`) and `instructions` (not `system_prompt`)
- Result accessed via `result.output` (not `result.data`)

## Endpoint
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/recommendations` | AI-powered product recommendations with NL query + optional filters |

**Request body:**
```json
{
  "query": "budget smartphones under $500",
  "max_results": 5,
  "max_price": 500,
  "min_rating": 4.0,
  "category": "smartphones"
}
```

## Test Results
- **Total tests**: 137 (14 new + 123 existing)
- **Passed**: 137
- **Failed**: 0
- **Coverage**: 82% overall
- **New module coverage**: agent.py 74%, tools.py 91%, schemas 100%, prompts 100%

## Acceptance Criteria Checklist
- [x] pydantic-ai upgraded to 1.x (1.61.0 installed)
- [x] `AgentDependencies` dataclass created (shared across all future agents)
- [x] `RecommendationAgent` implements `BaseAgent.process()` contract
- [x] pydantic-ai Agent with OpenAI model, typed output, tool-based reasoning
- [x] Tool: `search_products_by_filters` — queries DB with category/brand/price/rating filters
- [x] Tool: `get_product_details` — fetches a single product by ID
- [x] Tool: `get_categories` — lists available categories
- [x] Returns ranked list with relevance scores and reasoning per product
- [x] Handles natural language queries
- [x] `POST /api/v1/recommendations` endpoint wired into FastAPI
- [x] Unit tests using `TestModel` (no real API calls): 14 tests passing

## Architecture Patterns Established
| Pattern | Description |
|---------|-------------|
| Two-layer agent | `BaseAgent.process()` wraps internal pydantic-ai `Agent` |
| Shared deps | `AgentDependencies(db, settings)` injected via `RunContext` |
| 4-file agent package | `agent.py`, `tools.py`, `prompts.py`, `__init__.py` |
| TestModel testing | Deterministic tests without API calls or mocks |
| Structured output | Pydantic models as `output_type` for type-safe LLM responses |
| Hydration pattern | LLM returns IDs, agent fetches full data from DB |

## Notes
- `OpenAIModel` is deprecated in 1.61.0 in favor of `OpenAIChatModel`; kept for compatibility with `gpt-4o-mini` config
- Requires `OPENAI_API_KEY` environment variable for live usage
- TestModel tests work without any API key
