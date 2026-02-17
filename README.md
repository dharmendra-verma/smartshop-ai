# SmartShop AI

**AI-Driven Multi-Agent E-commerce Assistant**

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
│   ├── agents/                 # AI agent implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Base agent class
│   │   ├── orchestrator.py    # Intent router
│   │   ├── recommendation.py  # Product recommendation agent
│   │   ├── review.py          # Review summarization agent
│   │   ├── price.py           # Price comparison agent
│   │   └── policy.py          # FAQ/Policy agent (RAG)
│   ├── api/                   # FastAPI routes
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── products.py
│   │   ├── chat.py
│   │   └── agents.py
│   ├── core/                  # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection
│   │   └── cache.py           # Redis cache utilities
│   ├── models/                # Database models
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── review.py
│   │   └── policy.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── agent.py
│   │   └── response.py
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── product_service.py
│   │   ├── review_service.py
│   │   └── cache_service.py
│   ├── ui/                    # Frontend applications
│   │   ├── streamlit_app.py   # Main Streamlit interface
│   │   └── components/        # Reusable UI components
│   ├── utils/                 # Helper utilities
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── embeddings.py
│   └── main.py                # FastAPI application entry
├── data/                      # Data storage
│   ├── raw/                   # Raw datasets
│   ├── processed/             # Processed data
│   └── embeddings/            # Vector embeddings
├── scripts/                   # Utility scripts
│   ├── init_db.py            # Database initialization
│   ├── load_sample_data.py   # Sample data loader
│   └── ingest_data.py        # Data ingestion pipeline
├── tests/                     # Test suite
│   ├── test_agents/
│   ├── test_api/
│   └── test_services/
├── docs/                      # Documentation
│   ├── architecture.md
│   ├── agents.md
│   └── deployment.md
├── .env.example              # Environment template
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── LICENSE
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI & NLP** | OpenAI GPT-4o-mini | Language understanding & generation |
| **Agent Framework** | Pydantic AI | Multi-agent orchestration |
| **Backend API** | FastAPI | Async REST API with auto-docs |
| **Frontend** | Streamlit | Interactive chat interface |
| **Database** | PostgreSQL | Relational data storage |
| **Vector Store** | FAISS | Embeddings for RAG |
| **Cache** | Redis | Query result caching |
| **Deployment** | Docker | Containerized deployment |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_agents/test_recommendation.py
```

## 📊 Success Metrics

| Metric | Target (MVP) |
|--------|-------------|
| Recommendation Relevance | ≥70% |
| Query Resolution Rate | ≥80% |
| Response Latency (P95) | ≤3 seconds |
| Comparison Accuracy | ≥95% |
| User Retention (7-day) | ≥30% |

## 🗺️ Roadmap

### Phase 1: Foundation (Week 1) ✅
- Database schema & data pipeline
- FastAPI backend scaffolding
- Product catalog loaded

### Phase 2: Core Agents (Week 2) 🚧
- Product Recommendation Agent
- Review Summarization Agent
- Basic Streamlit UI

### Phase 3: Advanced Agents (Week 3)
- Price Comparison Agent
- FAQ/Policy Agent with RAG
- Multi-agent orchestration

### Phase 4: Polish & Demo (Week 4)
- UI/UX refinement
- Performance optimization
- Documentation & demo prep

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
