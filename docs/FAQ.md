# SmartShop AI — FAQ Document

## Architecture & Design

**Q: Why use multiple specialized agents instead of one general-purpose LLM?**
Each agent is optimized for its domain with tailored system prompts, output schemas, and data sources. This produces more accurate, focused responses than a single generalist agent. The orchestrator automatically routes queries to the right expert, so the user experience is seamless.

**Q: How does the intent classification work?**
The Intent Classifier is a lightweight LLM call that categorizes user queries into one of six intents: recommendation, review, price, policy, comparison, or general. The Orchestrator then routes to the corresponding agent. Classification adds minimal latency (~50ms) but ensures the right agent handles each query.

**Q: Why pydantic-ai instead of LangChain or CrewAI?**
pydantic-ai provides type-safe agent definitions with Pydantic models, direct integration with our existing Pydantic schemas, and a clean testing story with `TestModel` for unit tests. It's lightweight and doesn't impose the overhead of larger frameworks.

**Q: How does the FAISS-based RAG pipeline work?**
Store policies are embedded using OpenAI's `text-embedding-3-small` model (1536 dimensions), stored in a FAISS `IndexFlatIP` index with L2-normalized vectors for cosine similarity. When a policy question comes in, the query is embedded and the most relevant policy chunks are retrieved, then passed to the Policy Agent as context for generating an accurate answer.

**Q: What happens if an AI agent fails?**
We have a circuit breaker pattern. If an agent fails, the circuit breaker records the failure. After repeated failures, the orchestrator falls back to cached responses (24-hour query cache) or the general agent. The alerting system triggers a CRITICAL log when a component hits 10+ failures in a 5-minute window.

---

## Performance & Scalability

**Q: What's the expected response latency?**
Average response time is under 200ms for cached queries. For LLM-backed queries, latency depends on the OpenAI API (~1-3 seconds typical). We track P50 and P95 latency per endpoint via our built-in metrics system.

**Q: How does caching work?**
Three caching layers: (1) LLM response cache — stores agent outputs for 24 hours to avoid redundant LLM calls. (2) Query cache — caches full orchestrator responses for repeated queries. (3) Price cache — 1-hour TTL for pricing data. All use a dual-backend pattern: Redis primary with in-memory TTLCache fallback if Redis is unavailable.

**Q: Can it handle concurrent users?**
Yes. FastAPI is async by design, sessions are Redis-backed (stateless API layer), and Azure Container Apps auto-scales from 1 to 5 replicas based on HTTP concurrency. Each replica handles its own connections with a configurable connection pool (20 base, 10 overflow).

**Q: What about database performance?**
SQLAlchemy 2.0 with async sessions, connection pooling (20 pool + 10 overflow), and proper index design. We use Supabase-hosted PostgreSQL for the production deployment.

---

## Data & AI

**Q: What data does the product catalog contain?**
An electronics dataset with products including smartphones, laptops, tablets, and accessories. Each product has name, category, price, description, features, ratings, and review data.

**Q: Does it support real-time pricing?**
The Price Agent uses a MockPricingService for the demo. In production, this would be replaced with real pricing APIs. The price cache (1-hour TTL) ensures we don't hit pricing APIs excessively.

**Q: How is user privacy handled?**
Session data is stored in Redis with a 30-minute TTL and auto-expires. No user data is persisted long-term. The LLM receives only the current conversation context and product data — no PII is sent to OpenAI.

**Q: Which OpenAI model is used and why?**
GPT-4o-mini — it offers an excellent balance of cost, speed, and quality for our use case. It handles product recommendations, review summarization, and policy questions effectively at a fraction of GPT-4o's cost.

---

## Deployment & Operations

**Q: How is CI/CD configured?**
GitHub Actions with three workflows: (1) CI — triggers on PR and push to main, runs linting (ruff, black, mypy), all 430+ tests with PostgreSQL/Redis service containers, and Docker build. (2) CD Staging — auto-deploys on merge to main. (3) CD Production — manual trigger with environment approval gate.

**Q: What Azure services are used?**
Azure Container Apps (serverless containers), Azure Container Registry (Docker images), Azure Cache for Redis, Azure Key Vault (secrets), Azure Application Insights (monitoring), and Log Analytics (centralized logging). All defined as Bicep IaC templates.

**Q: How do you handle secrets?**
GitHub Secrets for CI/CD pipeline variables. Azure Key Vault for runtime secrets (DATABASE_URL, OPENAI_API_KEY, REDIS_URL). No secrets are stored in code or environment variables at rest.

**Q: What monitoring is in place?**
Built-in metrics system tracking P50/P95 latency per endpoint (rolling 200 samples). Alerting with a 5-minute rolling window that logs CRITICAL when a component exceeds 10 failures. Azure Application Insights for distributed tracing. Health endpoints at `/health`, `/health/metrics`, and `/health/alerts`.

---

## Testing

**Q: How many tests are there?**
430+ unit and integration tests. The test count grew steadily — 10 to 20 new tests per story across 21 stories.

**Q: What's the testing strategy?**
Unit tests for all agents (using pydantic-ai's `TestModel`), services, and API endpoints. Integration tests for end-to-end flows. Infrastructure validation tests for CI/CD configuration. Tests use `AsyncMock` for agent mocking and `autouse` fixtures for cache reset between tests.

**Q: How are AI agents tested without calling OpenAI?**
pydantic-ai provides `TestModel` — a deterministic mock that returns predictable outputs. For more detailed tests, we use `AsyncMock` on the agent's internal `_agent.run` method, with side effects that accept `**kwargs` for `usage_limits` compatibility.

---

## Future Plans

**Q: What's on the roadmap for v2.0?**
Key areas include: user authentication and personalized profiles, order tracking integration, multi-language support, advanced analytics dashboard, A/B testing framework for agent prompts, and mobile-responsive UI.

**Q: Can new agents be added easily?**
Yes. The architecture is designed for extensibility. A new agent needs: (1) an agent class extending `BaseAgent`, (2) a new intent in the classifier, (3) a new route in the orchestrator mapping, and (4) an API endpoint. The pattern is well-documented and consistent across all existing agents.
