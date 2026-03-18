# SmartShop AI — Demo Script

## Pre-Demo Checklist

- [ ] Application running: FastAPI on port 8000, Streamlit on port 8501
- [ ] Database seeded with product catalog (electronics dataset)
- [ ] Redis running for session and cache support
- [ ] Browser open to Streamlit UI at `http://localhost:8501`
- [ ] Presentation slides loaded and ready
- [ ] Backup demo video ready (optional)

---

## Demo Flow (10 Minutes)

### 1. Introduction (2 minutes)

**[Slide 1 — Title]**

> "Good morning/afternoon everyone. Today I'm going to walk you through SmartShop AI — an AI-powered multi-agent e-commerce assistant."

**[Slide 2 — The Problem]**

> "Let's start with the problem. 73% of online shoppers abandon purchases due to choice overload. They're opening 5+ browser tabs to compare products, read reviews across different sites, and check prices — all while getting generic search results with zero personalization."

**[Slide 3 — Our Solution]**

> "SmartShop AI solves this with one conversational AI that understands what you need. It routes your query to the right specialized agent and delivers expert answers in real time. It remembers context across the conversation, and it's built for production with CI/CD, Azure deployment, and over 430 tests."

---

### 2. Live Demo (5 minutes)

**[Slide 5 — Live Demo]**

> "Let me show you how this works. I'll walk through five scenarios that demonstrate each of our specialized agents."

**Switch to the Streamlit UI in the browser.**

#### Use Case 1: Product Discovery (1 min)

**Type:** `Find budget smartphones under $500`

> "First, product discovery. I'm asking for budget smartphones under $500. The intent classifier recognizes this as a recommendation query and routes it to our Recommendation Agent. Notice how it returns relevant products with details, not just a list of links."

**Talking points:**
- Highlight that the agent understands budget constraints
- Point out product details returned (name, price, features, ratings)
- Mention the response time

#### Use Case 2: Review Summarization (1 min)

**Type:** `Summarize reviews for iPhone 15`

> "Next, I want to know what people think about the iPhone 15. This goes to our Review Agent, which summarizes customer reviews and provides sentiment analysis. It extracts the key themes — what people love and what they don't."

**Talking points:**
- Show how the summary captures positive and negative themes
- Highlight sentiment analysis
- Note that this would normally require reading dozens of reviews

#### Use Case 3: Price Comparison (1 min)

**Type:** `Compare Samsung S24 and Google Pixel 8`

> "Now a head-to-head comparison. The Price Agent handles this — it compares specs, pricing, and value propositions side by side."

**Talking points:**
- Point out the structured comparison format
- Highlight key differentiators surfaced by the agent
- Mention the pricing data integration

#### Use Case 4: Policy Query (1 min)

**Type:** `What's the return policy?`

> "Here's something unique — policy questions. This uses our FAISS-powered RAG pipeline. The Policy Agent searches our vector store of store policies and returns the exact relevant information."

**Talking points:**
- Explain RAG: Retrieval Augmented Generation
- The answer comes from actual store policy documents, not hallucination
- FAISS enables fast similarity search over policy embeddings

#### Use Case 5: Multi-Turn Conversation (1 min)

**Type:** `Which one has better battery life?` (follow-up without naming products)

> "And this is where session memory shines. I'm asking a follow-up question without naming any products. The system remembers we were just comparing Samsung S24 and Pixel 8, and it answers in that context."

**Talking points:**
- No need to repeat context — session memory preserves it
- 30-minute session TTL with Redis-backed persistence
- This is what makes it a true conversational assistant

---

### 3. Architecture Overview (2 minutes)

**[Slide 6 — Architecture]**

> "Under the hood, we have five clean layers. The Streamlit frontend with our floating chat widget. FastAPI handling REST endpoints with middleware for request tracking and error handling. The AI layer — powered by pydantic-ai — with an orchestrator that classifies intent and routes to 5 specialized agents. PostgreSQL and Redis for data persistence and caching. And GitHub Actions CI/CD deploying to Azure Container Apps."

**[Slide 7 — Technology Stack]**

> "Our tech stack: FastAPI for the async API, pydantic-ai for type-safe agents, GPT-4o-mini as the LLM, FAISS for vector search, PostgreSQL and Redis for data, and Azure Container Apps for production hosting."

---

### 4. Success Metrics & Roadmap (1 minute)

**[Slide 8 — Success Metrics]**

> "Some key numbers. 430+ unit tests with comprehensive coverage. 21 user stories shipped across 4 sprints. 5 specialized agents. And sub-200ms average response latency. You can see our test count growing steadily — we added 10-20 tests with every story."

**[Slide 9 — Roadmap]**

> "We executed across 4 phases: Foundation, Intelligence, Polish, and now Production. We're currently wrapping up CI/CD and monitoring capabilities."

**[Slide 10 — Risk Mitigation]**

> "We've proactively addressed key risks. Circuit breaker patterns for LLM reliability. Dual-backend caching for performance. Azure Key Vault for security. And auto-scaling Container Apps for scalability."

---

### 5. Closing

**[Slide 11 — Thank You]**

> "Thank you for your time. I'm happy to take any questions about the architecture, the AI agents, our deployment strategy, or anything else about SmartShop AI."

---

## Backup Talking Points

### If asked about LLM costs:
> "We use GPT-4o-mini which offers an excellent cost-to-performance ratio. Our LLM cache with 24-hour TTL means repeated queries are served from cache, significantly reducing API costs."

### If asked about accuracy:
> "For policy questions, we use RAG with FAISS — so answers are grounded in actual store documents, not hallucinated. For recommendations and reviews, the agents work with real product data from our database."

### If asked about scaling:
> "Azure Container Apps auto-scales from 1 to 5 replicas based on HTTP concurrency. Redis handles session and cache persistence across replicas. The architecture is stateless at the API layer."

### If the live demo fails:
> "Switch to backup video. Have pre-captured screenshots ready showing each demo scenario's output."

---

## Demo Environment URLs

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Metrics | http://localhost:8000/health/metrics |
| Alerts | http://localhost:8000/health/alerts |
