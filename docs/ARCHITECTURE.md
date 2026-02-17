# SmartShop AI - System Architecture

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Multi-Agent Architecture](#multi-agent-architecture)
4. [Data Flow](#data-flow)
5. [Component Details](#component-details)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)

---

## Overview

SmartShop AI is built on a **microservices-oriented, multi-agent architecture** that separates concerns across presentation, orchestration, agent, and data layers. This modular design enables independent scaling, testing, and enhancement of each capability.

### Core Design Principles

1. **Separation of Concerns** - Each layer has a specific responsibility
2. **Modularity** - Agents operate independently and can be deployed separately
3. **Scalability** - Horizontal scaling at the API and agent layers
4. **Resilience** - Circuit breakers, fallbacks, and graceful degradation
5. **Observability** - Comprehensive logging, monitoring, and tracing

---

## System Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Streamlit UI]
        API[FastAPI REST API]
    end

    subgraph "Orchestration Layer"
        Router[Intent Router]
        SessionMgr[Session Manager]
        ContextMem[Context Memory]
    end

    subgraph "Agent Layer"
        RecAgent[Recommendation Agent]
        PriceAgent[Price Comparison Agent]
        ReviewAgent[Review Summarization Agent]
        PolicyAgent[FAQ/Policy Agent]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        Redis[(Redis Cache)]
        FAISS[(FAISS Vector DB)]
    end

    subgraph "External Services"
        OpenAI[OpenAI GPT-4o-mini]
        PricingAPI[Pricing APIs]
    end

    UI --> API
    API --> Router
    Router --> SessionMgr
    Router --> ContextMem

    Router --> RecAgent
    Router --> PriceAgent
    Router --> ReviewAgent
    Router --> PolicyAgent

    RecAgent --> PG
    RecAgent --> Redis
    RecAgent --> OpenAI

    PriceAgent --> PG
    PriceAgent --> PricingAPI
    PriceAgent --> Redis

    ReviewAgent --> PG
    ReviewAgent --> OpenAI
    ReviewAgent --> Redis

    PolicyAgent --> FAISS
    PolicyAgent --> OpenAI
    PolicyAgent --> Redis
```

---

## Multi-Agent Architecture

### Agent Communication Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant API as FastAPI
    participant Router as Intent Router
    participant Agent as Specialized Agent
    participant DB as Data Layer
    participant LLM as OpenAI

    User->>UI: Natural language query
    UI->>API: POST /chat
    API->>Router: Forward query
    Router->>LLM: Classify intent
    LLM-->>Router: Intent + Entities
    Router->>Agent: Delegate task
    Agent->>DB: Fetch data
    DB-->>Agent: Return data
    Agent->>LLM: Generate response
    LLM-->>Agent: AI response
    Agent-->>Router: Structured result
    Router-->>API: Format response
    API-->>UI: JSON response
    UI-->>User: Display result
```

### Agent Reasoning Loop (ReAct Pattern)

Each agent follows the **ReAct (Reason + Act)** paradigm:

```mermaid
graph LR
    A[Receive Task] --> B[Reason]
    B --> C[Select Tool]
    C --> D[Execute Tool]
    D --> E[Observe Result]
    E --> F{Task Complete?}
    F -->|No| B
    F -->|Yes| G[Return Result]
```

**Steps:**
1. **Reason** - Analyze task and determine next action
2. **Select Tool** - Choose appropriate tool (DB query, API call, LLM)
3. **Execute** - Run the selected tool
4. **Observe** - Analyze the results
5. **Repeat** - Continue until task is complete

---

## Data Flow

### Request Lifecycle

```mermaid
graph TB
    Start[User Query] --> Intent[Intent Classification]
    Intent --> Route{Route to Agent}

    Route -->|Recommendation| RecFlow[Product Recommendation Flow]
    Route -->|Comparison| PriceFlow[Price Comparison Flow]
    Route -->|Review| ReviewFlow[Review Summarization Flow]
    Route -->|Policy| PolicyFlow[FAQ/Policy Flow]

    RecFlow --> DB1[(Product DB)]
    RecFlow --> Cache1[(Cache Check)]
    RecFlow --> LLM1[LLM Processing]

    PriceFlow --> DB2[(Product DB)]
    PriceFlow --> API1[Pricing APIs]
    PriceFlow --> Cache2[(Cache)]

    ReviewFlow --> DB3[(Review DB)]
    ReviewFlow --> LLM2[Sentiment Analysis]
    ReviewFlow --> Cache3[(Cache)]

    PolicyFlow --> Vector[(Vector DB)]
    PolicyFlow --> RAG[RAG Retrieval]
    PolicyFlow --> LLM3[Answer Synthesis]

    LLM1 --> Respond[Format Response]
    LLM2 --> Respond
    LLM3 --> Respond
    Cache1 --> Respond
    Cache2 --> Respond
    Cache3 --> Respond

    Respond --> End[Return to User]
```

### Data Pipeline

```mermaid
graph LR
    subgraph "Ingestion"
        Raw[Raw Data] --> Validate[Validation]
        Validate --> Clean[Cleaning]
        Clean --> Transform[Transformation]
    end

    subgraph "Storage"
        Transform --> PG[(PostgreSQL)]
        Transform --> Embed[Generate Embeddings]
        Embed --> FAISS[(FAISS)]
    end

    subgraph "Processing"
        PG --> Sentiment[Sentiment Analysis]
        Sentiment --> PG
        PG --> Cache[(Redis Cache)]
    end
```

---

## Component Details

### 1. Presentation Layer

#### Streamlit UI
- **Purpose**: Interactive chat interface for end users
- **Features**:
  - Multi-module navigation (Chat, Comparison, Reviews, Pricing)
  - Real-time agent responses
  - Product visualization with images and ratings
  - Session persistence
- **Communication**: REST API calls to FastAPI backend

#### FastAPI Backend
- **Purpose**: RESTful API gateway
- **Endpoints**:
  - `POST /chat` - Main chat interface
  - `GET /products` - Product search
  - `POST /agents/{agent_name}` - Direct agent invocation
  - `GET /health` - Health check
- **Features**:
  - Auto-generated OpenAPI documentation
  - Request validation with Pydantic
  - Async request handling
  - Rate limiting

### 2. Orchestration Layer

#### Intent Router
- **Purpose**: Classify user intent and route to appropriate agent
- **Method**: LLM-based classification with GPT-4o-mini
- **Intent Categories**:
  - `recommendation` - Product discovery
  - `comparison` - Price/feature comparison
  - `review` - Review summarization
  - `policy` - Store policy queries
  - `general` - Fallback for misc queries
- **Accuracy Target**: ≥90%

#### Session Manager
- **Purpose**: Manage user sessions and state
- **Storage**: Redis with 30-minute TTL
- **Data Stored**:
  - Conversation history
  - User preferences
  - Previous query results (for context)

#### Context Memory
- **Purpose**: Maintain conversation context for follow-up queries
- **Strategy**: Sliding window of last 10 message pairs
- **Features**:
  - Context summarization for long conversations
  - Entity extraction and tracking
  - Reference resolution ("Which of these...", "The second one", etc.)

### 3. Agent Layer

#### Product Recommendation Agent
- **Data Sources**: Product catalog, user interaction logs
- **Process**:
  1. Extract user preferences (budget, category, features)
  2. Query database with filters
  3. Rank results by relevance score
  4. Generate personalized descriptions
- **Output**: Top 5-10 ranked products with scores

#### Price Comparison Agent
- **Data Sources**: Product catalog, pricing APIs
- **Process**:
  1. Identify products to compare
  2. Fetch real-time pricing from multiple sources
  3. Normalize data (handle currency, units, availability)
  4. Generate comparison table
- **Output**: Side-by-side comparison with best deal highlights

#### Review Summarization Agent
- **Data Sources**: Customer reviews database
- **Process**:
  1. Retrieve reviews for target product
  2. Pre-computed sentiment labels lookup (fast path)
  3. GPT-based theme extraction (top positive/negative)
  4. Calculate overall sentiment score
- **Output**: Concise summary with confidence scores

#### FAQ & Policy Agent
- **Data Sources**: Store policies vector database (FAISS)
- **Process** (RAG Pipeline):
  1. Convert query to embedding
  2. Semantic search in FAISS for relevant policy sections
  3. Retrieve top-K most relevant chunks
  4. GPT synthesis with citations
- **Output**: Contextual answer with source references

### 4. Data Layer

#### PostgreSQL
- **Schema**:
  ```
  products (id, name, description, price, brand, category, image_url, created_at)
  reviews (id, product_id, rating, review_text, sentiment, timestamp)
  policies (id, category, question, answer, effective_date)
  ```
- **Indexes**: On frequently queried columns (category, price, brand, product_id)
- **Connection Pooling**: Max 20 connections with overflow

#### Redis Cache
- **Use Cases**:
  - Query result caching (1-hour TTL)
  - Session storage (30-minute TTL)
  - Rate limiting counters
  - Frequent product lookups (24-hour TTL)
- **Eviction Policy**: LRU (Least Recently Used)

#### FAISS Vector Store
- **Purpose**: Semantic search for store policies
- **Embedding Model**: OpenAI text-embedding-3-small (1536 dimensions)
- **Index Type**: IndexFlatL2 (exact search for MVP, upgrade to IndexIVFFlat for scale)
- **Data**: ~500-1000 policy documents embedded

---

## Technology Stack

| Layer | Component | Technology | Version |
|-------|-----------|-----------|---------|
| **Frontend** | UI Framework | Streamlit | 1.30+ |
| **Backend** | API Framework | FastAPI | 0.109+ |
| | ASGI Server | Uvicorn | 0.27+ |
| | Validation | Pydantic | 2.5+ |
| **AI/ML** | LLM | OpenAI GPT-4o-mini | Latest |
| | Agent Framework | Pydantic AI | 0.0.13+ |
| | Embeddings | OpenAI Embeddings | text-embedding-3-small |
| **Data** | Database | PostgreSQL | 15+ |
| | ORM | SQLAlchemy | 2.0+ |
| | Vector Store | FAISS | 1.7+ |
| | Cache | Redis | 7+ |
| **DevOps** | Containerization | Docker | Latest |
| | Orchestration | Docker Compose | v3.8 |
| | Language | Python | 3.11+ |

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────┐
│          Developer Machine              │
│  ┌────────┐  ┌─────────┐  ┌─────────┐ │
│  │ FastAPI│  │Streamlit│  │PostgreSQL│ │
│  │:8000   │  │:8501    │  │:5432     │ │
│  └────────┘  └─────────┘  └─────────┘ │
│       │           │             │       │
│       └───────────┴─────────────┘       │
│              localhost                  │
└─────────────────────────────────────────┘
```

### Production Environment (AWS Example)

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            ALB[Application Load Balancer]

            subgraph "ECS Cluster"
                API1[FastAPI Service 1]
                API2[FastAPI Service 2]
                UI1[Streamlit Service 1]
                UI2[Streamlit Service 2]
            end

            subgraph "Data Services"
                RDS[(RDS PostgreSQL)]
                ElastiCache[(ElastiCache Redis)]
            end

            subgraph "Storage"
                S3[S3 - Model Artifacts]
            end
        end
    end

    Internet[Internet] --> ALB
    ALB --> API1
    ALB --> API2
    ALB --> UI1
    ALB --> UI2

    API1 --> RDS
    API2 --> RDS
    API1 --> ElastiCache
    API2 --> ElastiCache
    API1 --> S3
    API2 --> S3
```

### Scaling Strategy

1. **Horizontal Scaling**:
   - FastAPI: Scale to N instances behind load balancer
   - Agents: Stateless design allows independent scaling

2. **Vertical Scaling**:
   - PostgreSQL: Upgrade instance size as data grows
   - Redis: Increase memory for larger cache

3. **Caching Strategy**:
   - L1: Application-level cache (in-memory)
   - L2: Redis distributed cache
   - L3: Database query optimization

4. **Auto-scaling Triggers**:
   - CPU > 70% for 5 minutes
   - Request rate > 1000 req/min
   - Response latency P95 > 3 seconds

---

## Security Considerations

1. **API Security**:
   - API key authentication
   - Rate limiting (60 req/min per IP)
   - Input validation with Pydantic

2. **Data Security**:
   - Encrypted connections (SSL/TLS)
   - No PII storage without consent
   - Database access via IAM roles

3. **LLM Security**:
   - Prompt injection protection
   - Content filtering
   - Response validation

---

## Monitoring & Observability

1. **Metrics**:
   - Request latency (P50, P95, P99)
   - Error rates by endpoint
   - Cache hit/miss ratios
   - LLM token usage & cost

2. **Logging**:
   - Structured JSON logs
   - Request ID tracing
   - Agent decision logs

3. **Alerting**:
   - Error rate > 5%
   - Latency P95 > 3s
   - Database connection pool exhaustion

---

## Future Enhancements

1. **v2.0 Features**:
   - Event-driven architecture with message queues
   - GraphQL API for flexible queries
   - WebSocket support for real-time updates

2. **Performance**:
   - Model distillation for faster inference
   - Multi-tier caching with CDN
   - Database read replicas

3. **Capabilities**:
   - Voice interface with Whisper API
   - Visual search with CLIP embeddings
   - Multi-language support

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Author**: SmartShop AI Architecture Team
