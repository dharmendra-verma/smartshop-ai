# SmartShop AI

**AI-Driven Multi-Agent E-commerce Assistant**

[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Vision Statement

To become the most intuitive AI shopping companion that understands customer intent, orchestrates specialized agents, and fulfills requests efficiently across discovery, ordering, support, and post-purchase workflows.

## ✨ Key Features

- **🎯 Hyper-Personalized Discovery** - AI models analyze user interactions and preferences to surface highly relevant product recommendations
- **💰 Intelligent Price Optimization** - Real-time cross-platform price comparison ensures customers always find the best deal
- **📊 Effortless Review Insights** - Sentiment-based summarization distills thousands of reviews into actionable buying signals
- **💬 Conversational Support** - Natural language interface handles FAQs, return policies, and store-specific queries
- **🤖 Scalable Multi-Agent Architecture** - Modular agent design allows independent scaling and enhancement

## 🏗️ Architecture Overview

SmartShop AI operates as a **multi-agent orchestration system** where a central LLM-based router receives user queries in natural language, classifies intent, and delegates tasks to specialized agents.

### Agent System

| Agent | Responsibility | Output |
|-------|---------------|--------|
| **Intent Router** | Classifies user intent and delegates to appropriate agent | Routed task with parameters |
| **Product Recommendation** | Generates personalized product suggestions | Ranked product list with scores |
| **Price Comparison** | Compares pricing across multiple retailers | Structured comparison table |
| **Review Summarization** | Extracts sentiment themes from customer reviews | Concise sentiment summary |
| **FAQ & Policy** | Handles store policy queries using RAG | Contextual answer with sources |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/smartshop-ai.git
cd smartshop-ai
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Initialize database**
```bash
python scripts/init_db.py
```

6. **Load sample data**
```bash
python scripts/load_sample_data.py
```

### Running the Application

**Option 1: Local Development**

```bash
# Start the FastAPI backend
uvicorn app.main:app --reload --port 8000

# In a new terminal, start the Streamlit UI
streamlit run app/ui/streamlit_app.py
```

**Option 2: Docker Compose**

```bash
docker-compose up --build
```

Access the application:
- **Streamlit UI**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📁 Project Structure

```
smartshop-ai/
├── app/
│   ├── agents/                 # pydantic-ai agents
│   │   ├── base.py            # BaseAgent + AgentResponse
│   │   ├── dependencies.py    # AgentDependencies(db, settings)
│   │   ├── recommendation/    # Product recommendation agent
│   │   ├── review/            # Review summarization agent
│   │   ├── price/             # Price comparison agent
│   │   ├── policy/            # FAQ/Policy agent (FAISS RAG)
│   │   └── orchestrator/      # Intent classifier, circuit breaker, general agent
│   ├── api/
│   │   ├── health.py          # GET /health
│   │   └── v1/                # Versioned API routers
│   │       ├── products.py    # GET /api/v1/products
│   │       ├── recommendations.py
│   │       ├── reviews.py
│   │       ├── price.py
│   │       ├── policy.py
│   │       └── chat.py        # POST /api/v1/chat (unified orchestrator)
│   ├── core/                  # config, database, cache, logging
│   ├── models/                # SQLAlchemy models (Product, Review, Policy)
│   ├── schemas/               # Pydantic request/response schemas
│   ├── services/
│   │   ├── pricing/           # MockPricingService + PriceCache
│   │   ├── session/           # SessionManager + SessionStore
│   │   └── ingestion/         # CSV data ingesters
│   ├── middleware/             # Error handler, request logging
│   ├── ui/
│   │   ├── streamlit_app.py   # Main Streamlit interface
│   │   ├── api_client.py      # HTTP client for FastAPI backend
│   │   ├── components/        # product_card, review_display, review_panel, chat_helpers, star_rating, floating_chat
│   │   └── design_tokens.py   # CSS and styling
│   └── main.py                # FastAPI application entry
├── alembic/                   # Database migrations
├── data/                      # CSV datasets
├── tests/                     # 511+ unit tests + 97 eval tests
│   ├── test_agents/
│   ├── test_api/
│   ├── test_services/
│   └── evals/                 # LLM-as-judge evaluation framework
├── docs/                      # Comprehensive documentation
├── plans/                     # Story plans (plan/, inprogress/, completed/)
└── requirements.txt
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI & NLP** | OpenAI GPT-4o-mini | Language understanding & generation |
| **Agent Framework** | Pydantic AI 1.61.0 | Multi-agent orchestration |
| **Backend API** | FastAPI | Async REST API with auto-docs |
| **Frontend** | Streamlit | Interactive chat interface |
| **Database** | PostgreSQL | Relational data storage |
| **Vector Store** | FAISS | Embeddings for RAG |
| **Cache** | Redis | Query result caching |
| **Deployment** | Docker | Containerized deployment |

## 🧪 Testing

```bash
# Run all unit/integration tests (no API cost)
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_agents/test_recommendation.py -v

# Run LLM-as-judge eval tests (makes real OpenAI API calls)
RUN_EVALS=1 pytest tests/evals/ -v -m eval
```

**Test counts:** ~511 unit/integration tests + 97 eval tests = ~608 total.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, component details |
| [API Reference](docs/API_REFERENCE.md) | All endpoints with request/response examples |
| [Agents](docs/AGENTS.md) | Agent design, tools, output schemas, caching |
| [Testing](docs/TESTING.md) | Test patterns, mocking, how to run tests |
| [Evals](docs/EVALS.md) | LLM-as-judge evaluation framework |
| [Deployment](docs/DEPLOYMENT.md) | Docker, env vars, production checklist |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | How to add agents, extend the system |
| [Data Pipeline](docs/DATA_PIPELINE.md) | CSV ingestion, FAISS index, data schemas |
| [Monitoring](docs/MONITORING.md) | Metrics, alerting, health endpoints |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [Database](docs/DATABASE.md) | Schema, migrations, entity relationships |
| [CI/CD](docs/CICD.md) | GitHub Actions pipelines, deployment flow |
| [Azure Setup](docs/AZURE_SETUP.md) | Azure infrastructure, Container Apps setup |

## 📊 Success Metrics

| Metric | Target (MVP) |
|--------|-------------|
| Recommendation Relevance | ≥70% |
| Query Resolution Rate | ≥80% |
| Response Latency (P95) | ≤3 seconds |
| Comparison Accuracy | ≥95% |
| User Retention (7-day) | ≥30% |

## 🗺️ Roadmap

### Phase 1: Foundation ✅
- Database schema & data pipeline
- FastAPI backend scaffolding
- Product catalog loaded

### Phase 2: Core Agents ✅
- Product Recommendation Agent
- Review Summarization Agent
- Basic Streamlit UI
- E2E integration

### Phase 3: Advanced Agents ✅
- Price Comparison Agent
- FAQ/Policy Agent with RAG (FAISS)
- Multi-agent orchestration with intent router
- Session memory (Redis/TTLCache)

### Phase 4: Polish ✅
- UI/UX refinement & visual polish
- Product images
- Agent loop prevention (UsageLimits)
- 286+ tests

### Phase 5: Hardening ✅
- File logging with rotation (SCRUM-63)
- DB health checks & connectivity monitoring (SCRUM-65)
- DRY code refactor — cache factory, shared error handling (SCRUM-66)
- SQL query optimization — 3→1 query consolidation (SCRUM-67)
- AI routing accuracy — confidence gating, hallucination tracking (SCRUM-68)
- Error handling hardening — honest failure reporting, 503 boundaries (SCRUM-69)
- 511+ tests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Product Management** - Requirements & Strategy
- **ML/AI Engineering** - Agent Development
- **Data Engineering** - Data Pipeline
- **Full-Stack Development** - Backend & Frontend
- **DevOps** - Infrastructure & Deployment

## 📞 Contact

For questions or support, please open an issue or contact the team at: [support@smartshop-ai.com](mailto:support@smartshop-ai.com)

---

**Built with ❤️ by the SmartShop AI Team**

🤖 *Powered by Claude Sonnet 4.5*
