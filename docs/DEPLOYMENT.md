# Deployment Guide

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional — falls back to in-memory TTLCache)
- OpenAI API key
- Docker & Docker Compose (for containerized deployment)

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for agents + embeddings |
| `DATABASE_URL` | Yes | `postgresql://postgres:password@localhost:5432/smartshop_ai` | PostgreSQL connection |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis; falls back to TTLCache if absent |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | LLM model |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model (1536 dims) |
| `ENV` | No | `development` | `development` or `production` |
| `DEBUG` | No | `True` | Debug logging |
| `API_HOST` | No | `0.0.0.0` | FastAPI bind address |
| `API_PORT` | No | `8000` | FastAPI port |
| `DB_POOL_SIZE` | No | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Extra connections |
| `CACHE_TTL_SECONDS` | No | `3600` | Default cache TTL (1 hour) |
| `CACHE_MAX_SIZE` | No | `1000` | Max in-memory cache entries |
| `SESSION_EXPIRE_MINUTES` | No | `30` | Session timeout |
| `AGENT_TIMEOUT_SECONDS` | No | `30` | Agent call timeout |
| `LOG_LEVEL` | No | `INFO` | Logging level |

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartshop_ai
REDIS_URL=redis://localhost:6379/0
ENV=production
DEBUG=False
```

---

## Local Development (Without Docker)

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create database
createdb smartshop_ai

# Run migrations
alembic upgrade head

# Load sample data
python -m scripts.load_data
```

### 3. Start Services

```bash
# Terminal 1 — FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Streamlit
streamlit run app/ui/streamlit_app.py --server.port 8501
```

---

## Docker Compose

### Full Stack

```bash
# Set your OpenAI key
export OPENAI_API_KEY=sk-your-key-here

# Start all services
docker-compose up --build

# Or in detached mode
docker-compose up --build -d
```

### Services

| Service | Port | Image | Depends On |
|---------|------|-------|------------|
| `postgres` | 5432 | `postgres:15-alpine` | — |
| `redis` | 6379 | `redis:7-alpine` | — |
| `api` | 8000 | `Dockerfile` | postgres, redis |
| `ui` | 8501 | `Dockerfile.streamlit` | api |

### Volumes

- `postgres_data` — persistent database
- `redis_data` — persistent cache
- `./app:/app/app` — code hot-reload (dev)
- `./data:/app/data` — shared data directory

### Health Checks

All services have health checks (10s interval, 5 retries):
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- API: `curl http://localhost:8000/health`
- UI: `curl http://localhost:8501/_stcore/health`

---

## Azure Container Apps (Cloud Deployment)

SmartShop AI deploys to Azure Container Apps via GitHub Actions CI/CD. See [AZURE_SETUP.md](AZURE_SETUP.md) for full infrastructure setup and [CICD.md](CICD.md) for pipeline details.

### Infrastructure Setup (One-Time)

```bash
# Deploy staging infrastructure via Bicep
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/parameters.staging.json
```

### Deploy Manually

```bash
# Login to ACR and push images
az acr login --name acrsmartshopstaging

docker build -f Dockerfile -t acrsmartshopstaging.azurecr.io/smartshop-api:latest .
docker push acrsmartshopstaging.azurecr.io/smartshop-api:latest

docker build -f Dockerfile.streamlit -t acrsmartshopstaging.azurecr.io/smartshop-ui:latest .
docker push acrsmartshopstaging.azurecr.io/smartshop-ui:latest

# Update container apps
az containerapp update \
  --name smartshop-api-staging \
  --resource-group rg-smartshop-staging \
  --image acrsmartshopstaging.azurecr.io/smartshop-api:latest

az containerapp update \
  --name smartshop-ui-staging \
  --resource-group rg-smartshop-staging \
  --image acrsmartshopstaging.azurecr.io/smartshop-ui:latest
```

### Automated Deployment

- **Staging:** Automatically deploys on every push to `main` via `cd-staging.yml`
- **Production:** Manual trigger via GitHub Actions `cd-production.yml` with image tag input
- **Rollback:** Production auto-rolls back to previous revision if health check fails

### Azure Resources

| Resource | Staging | Production |
|----------|---------|------------|
| Resource Group | `rg-smartshop-staging` | `rg-smartshop-prod` |
| API Container App | `smartshop-api-staging` | `smartshop-api-prod` |
| UI Container App | `smartshop-ui-staging` | `smartshop-ui-prod` |
| Container Registry | `acrsmartshopstaging` | `acrsmartshopprod` |
| Redis | `smartshop-redis-staging` | `smartshop-redis-prod` |
| Key Vault | `kv-smartshop-staging` | `kv-smartshop-prod` |

---

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1
```

### Current Migrations

1. **001** — Initial schema (products, reviews, policies + indexes)
2. **002** — Add `image_url` to products (idempotent)
3. **003** — Performance indexes (rating, stock, product_id, review rating)

---

## Data Loading

After database setup, load the sample data:

```bash
python -m scripts.load_data
```

This ingests:
- `data/raw/products.csv` → Products table (~50 records)
- `data/raw/reviews.csv` → Reviews table (~1000 records)
- `data/raw/store_policies.csv` → Policies table (~20 records)

The FAISS vector index is built automatically on first API startup.

---

## Production Considerations

### Security

- Set a strong `SESSION_SECRET_KEY`
- Set `DEBUG=False` and `ENV=production`
- Restrict CORS origins (currently `["*"]`)
- Use environment variables or secrets manager for `OPENAI_API_KEY`

### Scaling

- Increase `DB_POOL_SIZE` for higher concurrency
- Use Redis (not TTLCache) for multi-instance deployments
- Consider read replicas for PostgreSQL under heavy load

### Monitoring

- `GET /health` — basic health check
- `GET /health/metrics` — P50/P95 latency per endpoint
- `GET /health/alerts` — failure counts (5-min rolling window)
- See [docs/MONITORING.md](MONITORING.md) for details

### FAISS Index

- Built at startup from Policy table
- Persisted to `data/embeddings/faiss_index.bin`
- Rebuilds automatically if policy count changes
