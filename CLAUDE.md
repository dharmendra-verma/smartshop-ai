# SmartShop AI — Project Memory

## Project
**SmartShop AI** — AI-powered multi-agent e-commerce assistant.
FastAPI (port 8000) + pydantic-ai agents + Streamlit UI (port 8501) + PostgreSQL + Redis.

## Jira
| Key | Value |
|-----|-------|
| Cloud ID | `ba95f5fc-5994-47bc-81e4-161f6a62e829` |
| Project | `SCRUM` (SmartAIShope) |
| Done transition ID | `"31"` |
| Board URL | https://projecttracking.atlassian.net |

## Workflow
Three user tasks — determine which one from the user's message:
### Task 1 — "Check and plan an in-progress story from Jira"
You are expert planner
1. Query Jira for stories with status **In Progress** (`project = SCRUM AND status = "In Progress"`)
2. If none → notify user and stop (never move a story to In Progress yourself)
3. **GATE CHECK**: Confirm the story's Jira status is exactly `"In Progress"` before proceeding — if a user names a specific story ID, fetch it and verify its status first; if it is NOT `"In Progress"`, **stop and inform the user** — do NOT create a plan for it
4. Fetch full story details from Jira
5. Explore the codebase to understand the current state
6. Create `plans/plan/STORY-ID.md` with:
   - Story ID + title, acceptance criteria
   - Technical approach, file map, code snippets
   - Test requirements + expected new test count
   - Dependencies on prior stories
7. **Automatically** update `CLAUDE.md` In-Progress Plans section with the new plan entry — do NOT wait for the user to ask

### Task 2 — "A story is completed, wrap it up"
You are expert planner 
1. Read `.progress/STORY-ID.md` — verify status is Completed and all criteria met
2. Plan is already at `plans/completed/STORY-ID.md` (Claude Code moves it automatically)
3. Transition Jira to **Done** (transition ID `"31"`)
4. Add implementation comment to Jira: time spent, files changed, test count, summary
5. Update `CLAUDE.md`: move story to Completed Stories, update Test Count Tracker, update In-Progress Plans

### Task 3 — "Work on planned story"
You are expert developer in doing implemntation of the given todo under `plans/plan/STORY-ID.md`
Plan and start working in below sequence and with given instruciton
1. Pick the first `STORY-ID.md` Move it under `plans/inprogress/STORY-ID.md` folder
2. Analyze the `plans/inprogress/STORY-ID.md` and if needed create task as well within this todo 
3. Kepp on tracking the time spent by you on this implementation 
4. Do Implemention in app/ following our project structure
5. Create/update tests in tests/
6. Run test suite
7. Run the applicaiton to check if everything is ok
8. Generate completion report in `.progress/STORY-ID.md` along with the total time spent on the implementaiton
9. Notify user that task has been completed and ask if you can commit and push the changes in git
10. Once user notify commit and push the changes with STORY-ID.md
11. Check any documentation need to be updated
12. After completing task, always update this CLAUDE.md if there is any pattern, endpoints, architecture, project structre or Tech stack update


### Rules
- Never move a story to In Progress yourself in Jira
- **CRITICAL: Only plan stories that have Jira status `"In Progress"` — always verify status via Jira API before creating any plan file, regardless of what the user asks; if the story is not In Progress, stop and tell the user**
- **CRITICAL: When a user asks to create a NEW Jira story, create it in Jira first, then inform the user to move it to In Progress themselves before planning begins — never auto-plan a newly created story**
- Plans go in `plans/plan/` — Developer moves them to `plans/completed/` on implementation
- Windows filesystem: cannot `rm` files — truncate with `echo "" > file` instead
- After wrapping up, always update this CLAUDE.md (test counts, completed stories, in-progress plans)
- **After planning any story, always update CLAUDE.md In-Progress Plans automatically — never wait for the user to ask**
- **After completing any story, always update CLAUDE.md Completed Stories + Test Count Tracker + In-Progress Plans automatically — never wait for the user to ask**

## Test Count Tracker
| After story | Tests |
|-------------|-------|
| SCRUM-14 | 222 |
| SCRUM-15 | 235 |
| SCRUM-16 | 255 |
| SCRUM-17 | 269 |
| SCRUM-18 | 279 |
| SCRUM-40 | 287 |
| SCRUM-41 | 295 |
| SCRUM-42 | 307 |
| SCRUM-43 | 312 |
| SCRUM-19 | 341 |
| SCRUM-61 | 362 |

## Architecture
```
app/
  agents/          # pydantic-ai agents (base, recommendation, review, price, policy)
    intent_classifier.py
    circuit_breaker.py
    orchestrator.py
    general_agent.py
    dependencies.py   # AgentDependencies(db, settings)
  api/v1/          # FastAPI routers (products, recommendations, reviews, price, policy, chat)
  models/          # SQLAlchemy (Product, Review, Policy)
  schemas/         # Pydantic schemas
  services/
    pricing/       # MockPricingService + PriceCache (Redis/TTLCache)
    session/       # SessionManager + SessionStore (Redis/TTLCache)
    ingestion/     # CSV ingesters
  ui/
    streamlit_app.py
    api_client.py
    components/    # product_card, review_display, review_panel, chat_helpers, star_rating, floating_chat
    design_tokens.py
  core/            # config, database, cache (RedisCache, TTLCache), exceptions, query_cache, alerting
  middleware/       # error_handler, request_id, logging_middleware
```

## Key Patterns
| Pattern | Detail |
|---------|--------|
| Agent | `pydantic-ai Agent[DepsType, OutputType]`, `TestModel` for unit tests, `UsageLimits(request_limit=15)` on `.run()` to prevent loops |
| Singleton cache | `get_X()` + `reset_X()` module-level globals (PriceCache, SessionStore) |
| Dual backend | Redis primary → TTLCache fallback (PriceCache, SessionStore) |
| Test mocking | `AsyncMock` for `agent._agent.run` or `agent.process`; mock side_effects must accept `**kwargs` for `usage_limits`; `autouse` fixture calls `reset_X()` |
| API response | `AgentResponse(success, data, error, metadata)` from `BaseAgent` |
| Deps injection | `AgentDependencies.from_db(db)` → passed as `context["deps"]` |
| Error handling | Custom `SmartShopError` hierarchy; agents check `type(exc).__name__` for OpenAI errors → raise `AgentRateLimitError`/`AgentTimeoutError`; generic errors → `record_failure()` + return generic message |
| Request ID | `RequestIdMiddleware` adds 8-char UUID to `request.state.request_id` + `X-Request-Id` header |
| Query cache | `query_cache.cache_response()`/`get_cached_response()` — 24h TTL fallback in Orchestrator before general agent |
| Alerting | `alerting.record_failure(component)` — rolling 5min window, CRITICAL log at ≥10 failures; `/health/alerts` endpoint |

## Agents & Endpoints
| Agent | Endpoint | Intent |
|-------|----------|--------|
| RecommendationAgent | `POST /api/v1/recommendations` | recommendation, comparison |
| ReviewSummarizationAgent | `POST /api/v1/reviews/summarize` | review |
| PriceComparisonAgent | `POST /api/v1/price/compare` | price |
| PolicyAgent (FAISS RAG) | `POST /api/v1/policy/ask` | policy |
| Orchestrator | `POST /api/v1/chat` | all — routes by intent |
| GeneralResponseAgent | (fallback via orchestrator) | general |

## Completed Stories
SCRUM-8 (Load Product Catalog) → SCRUM-9 (FastAPI scaffold) → SCRUM-10 (RecommendationAgent) → SCRUM-11 (ReviewAgent) → SCRUM-12 (Streamlit UI) → SCRUM-13 (E2E integration) → SCRUM-14 (PriceAgent) → SCRUM-15 (PolicyAgent/RAG) → SCRUM-16 (Orchestrator/Intent Router) → SCRUM-17 (Session Memory) → SCRUM-18 (UI Polish) → SCRUM-40 (Product Images) → SCRUM-41 (Floating Chat Widget) → SCRUM-42 (Compact Product Card) → SCRUM-43 (Infinite Load) → SCRUM-19 (Error Handling & Resilience) → SCRUM-61 (Inline Reviews Panel)

## In-Progress Plans
- `plans/plan/SCRUM-20.md` — Performance Optimization (GZip, LLM cache, DB engine singleton, indexes, metrics)
- `plans/plan/SCRUM-60.md` — UI Revamp: Single-page layout, left filter panel (Category + Brand), auto-load product grid, chat-driven insights

## Tech Stack
| Tool | Version / Detail |
|------|-----------------|
| FastAPI | 0.109.0, port 8000 |
| pydantic-ai | 1.61.0 |
| OpenAI model | `gpt-4o-mini` (default), `text-embedding-3-small` (embeddings, 1536 dims) |
| FAISS | `IndexFlatIP` + L2-normalised vectors for cosine similarity |
| Streamlit | 1.30.0, port 8501 |
| DB | PostgreSQL, SQLAlchemy 2.0 |
| Cache | Redis → TTLCache fallback, key prefixes: `price:`, `session:` |
| Session TTL | 1800s (30 min) |
| Price TTL | 3600s (1 hr) |
| Alembic | migrations in `alembic/versions/` |
| Tests | pytest, target grows ~10–20 per story |
