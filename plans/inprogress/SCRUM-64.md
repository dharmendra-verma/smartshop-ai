# SCRUM-64 — DevOps: CI/CD Pipeline with GitHub Actions & Azure Container Apps

## Story Details
- **ID:** SCRUM-64
- **Title:** DevOps: CI/CD Pipeline with GitHub Actions & Azure Container Apps
- **Type:** Story (8 points)
- **Status:** In Progress

## Acceptance Criteria
1. Dockerization — optimized multi-stage Dockerfiles for API and UI, tagged with git SHA + `latest`
2. GitHub Actions CI — lint, test (399+ tests), build on PR and push to `main`
3. Azure Infrastructure (IaC) — Container Apps, ACR, PostgreSQL, Redis via Bicep
4. GitHub Actions CD — auto-deploy staging on merge, manual approval for production, rolling updates
5. Environment Configuration — secrets via GitHub Secrets + Azure Key Vault, health probes, auto-scaling
6. Monitoring & Observability — Application Insights, deployment notifications, revision management

---

## Technical Approach

### Current State Assessment
- **Dockerfiles exist:** `Dockerfile` (multi-stage FastAPI) and `Dockerfile.streamlit` (Streamlit UI) — both functional
- **docker-compose.yml exists:** 4 services (postgres, redis, api, ui) with health checks
- **No CI/CD:** `.github/workflows/` does not exist — greenfield
- **Test suite:** 399 tests via pytest with coverage (`pytest.ini` configured)
- **Linting tools:** ruff 0.1.14, black 24.1.1, mypy 1.8.0 (all in requirements.txt)
- **Alembic migrations:** 3 migration files in `alembic/versions/`
- **Health endpoints:** `GET /health`, `GET /health/alerts`, `GET /health/metrics`
- **Config:** pydantic-settings `BaseSettings` with `.env` support, `ENV` var for environment switching

### Pipeline Architecture
```
PR opened/updated
    └─→ CI Workflow (ci.yml)
         ├─ Lint (ruff + black --check + mypy)
         ├─ Test (pytest with PostgreSQL + Redis services)
         └─ Build (Docker image build verification)

Push to main (merge)
    └─→ CD Staging Workflow (cd-staging.yml)
         ├─ Build + push images to ACR (tagged SHA + latest)
         ├─ Run Alembic migrations against staging DB
         ├─ Deploy to Azure Container Apps (staging)
         └─ Run smoke tests against staging health endpoint

Manual trigger (after staging verified)
    └─→ CD Production Workflow (cd-production.yml)
         ├─ Require environment approval (GitHub Environments)
         ├─ Build + push images to ACR (tagged SHA + prod)
         ├─ Run Alembic migrations against production DB
         ├─ Deploy to Azure Container Apps (production)
         └─ Validate health + rollback on failure
```

---

## Implementation Plan

### Phase 1: GitHub Actions CI Pipeline
**Files to create:**

#### `.github/workflows/ci.yml`
```yaml
# Triggers: push to main, PR to main
# Jobs:
#   lint:
#     - ruff check app/ tests/
#     - black --check app/ tests/
#     - mypy app/ --ignore-missing-imports
#   test:
#     services:
#       postgres:15 (smartshop_ai DB)
#       redis:7
#     steps:
#       - pip install -r requirements.txt
#       - alembic upgrade head
#       - pytest tests/ -v --tb=short --cov=app --cov-report=xml
#       - Upload coverage artifact
#   build:
#     steps:
#       - docker build -f Dockerfile -t smartshop-api:test .
#       - docker build -f Dockerfile.streamlit -t smartshop-ui:test .
```

**Key decisions:**
- Use GitHub-hosted `ubuntu-latest` runners
- PostgreSQL 15 + Redis 7 as service containers for tests
- Cache pip dependencies with `actions/cache` (hash of requirements.txt)
- Cache Docker layers with `docker/build-push-action` + GitHub Actions cache
- Upload test results as artifacts (`pytest --junitxml=results.xml`)
- Fail-fast on lint errors before running expensive test + build jobs

### Phase 2: Dockerfiles Optimization
**Files to modify:**

#### `Dockerfile` (API) — Minor optimizations
- Add `.dockerignore` to exclude `venv/`, `.git/`, `tests/`, `docs/`, `plans/`, `.progress/`
- Add build arg for git SHA tag: `ARG GIT_SHA=latest` → `LABEL git.sha=${GIT_SHA}`
- Copy `alembic/` and `alembic.ini` for migration support in container
- Add `data/` directory with embeddings for FAISS

#### `Dockerfile.streamlit` (UI) — Minor optimizations
- Create slim requirements-ui.txt (only Streamlit + deps, not full ML stack)
- Add `.dockerignore` entries

#### `.dockerignore` (new file)
```
.git/
venv/
__pycache__/
*.pyc
tests/
docs/
plans/
.progress/
.claude/
*.md
!requirements.txt
!requirements-ui.txt
```

### Phase 3: Azure Infrastructure (Bicep IaC)
**Files to create:**

#### `infra/main.bicep`
Resources to provision:
- **Resource Group** — `rg-smartshop-{env}`
- **Azure Container Registry** — `acrsmartshop{env}` (Basic SKU for prototype)
- **Container Apps Environment** — shared between API + UI
- **Container App: API** — FastAPI on port 8000
  - Min replicas: 1, Max: 5
  - Scale rule: HTTP concurrency (10 concurrent requests per replica)
  - Health probe: `/health` (liveness + readiness)
  - Ingress: external, port 8000
  - Managed Identity for ACR pull + Key Vault access
- **Container App: UI** — Streamlit on port 8501
  - Min replicas: 1, Max: 3
  - Health probe: `/_stcore/health`
  - Ingress: external, port 8501
  - Env var: `API_URL` → API container app FQDN
- **Azure Database for PostgreSQL Flexible Server** — `smartshop-db-{env}`
  - SKU: `Standard_B1ms` (burstable, prototype-friendly)
  - Version: 15
  - Database: `smartshop_ai`
  - Firewall: allow Container Apps subnet
- **Azure Cache for Redis** — `smartshop-redis-{env}`
  - SKU: Basic C0 (256MB, prototype)
- **Azure Key Vault** — `kv-smartshop-{env}`
  - Secrets: `OPENAI-API-KEY`, `DATABASE-URL`, `REDIS-URL`, `SESSION-SECRET-KEY`
  - Access policy: Container App managed identity
- **Log Analytics Workspace** — for Container Apps logs
- **Application Insights** — connected to Log Analytics

#### `infra/parameters.staging.json`
```json
{
  "environmentName": "staging",
  "location": "eastus",
  "acrSku": "Basic",
  "dbSkuName": "Standard_B1ms",
  "redisSku": "Basic",
  "apiMinReplicas": 1,
  "apiMaxReplicas": 3,
  "uiMinReplicas": 1,
  "uiMaxReplicas": 2
}
```

#### `infra/parameters.prod.json`
```json
{
  "environmentName": "prod",
  "location": "eastus",
  "acrSku": "Standard",
  "dbSkuName": "Standard_B2s",
  "redisSku": "Basic",
  "apiMinReplicas": 2,
  "apiMaxReplicas": 5,
  "uiMinReplicas": 1,
  "uiMaxReplicas": 3
}
```

### Phase 4: GitHub Actions CD Pipeline
**Files to create:**

#### `.github/workflows/cd-staging.yml`
```yaml
# Trigger: push to main (after PR merge)
# Jobs:
#   build-and-push:
#     - Login to ACR (az acr login)
#     - Build + tag images: $ACR/smartshop-api:$SHA, $ACR/smartshop-ui:$SHA
#     - Push to ACR
#   deploy-staging:
#     needs: build-and-push
#     environment: staging
#     steps:
#       - az containerapp update (API) with new image tag
#       - az containerapp update (UI) with new image tag
#       - Wait for revision to be active
#   smoke-test:
#     needs: deploy-staging
#     steps:
#       - curl staging health endpoint (retry 5x with 10s delay)
#       - curl staging /health/metrics
#       - Verify HTTP 200 responses
```

#### `.github/workflows/cd-production.yml`
```yaml
# Trigger: workflow_dispatch (manual) OR after staging smoke tests pass
# Jobs:
#   deploy-production:
#     environment: production  # Requires GitHub Environment approval
#     steps:
#       - Pull staging-verified image tag
#       - az containerapp update (API) with verified tag
#       - az containerapp update (UI) with verified tag
#       - Health check validation
#       - On failure: az containerapp revision activate (previous revision)
```

#### `.github/workflows/infra.yml` (optional — IaC deployment)
```yaml
# Trigger: push to main (changes in infra/*) OR workflow_dispatch
# Jobs:
#   deploy-infra:
#     environment: staging OR production
#     steps:
#       - az deployment group create --template-file infra/main.bicep
```

### Phase 5: Environment Configuration & Secrets
**Setup required:**

#### GitHub Repository Secrets
| Secret | Purpose |
|--------|---------|
| `AZURE_CREDENTIALS` | Service principal JSON for Azure login |
| `ACR_LOGIN_SERVER` | e.g., `acrsmartshopstaging.azurecr.io` |
| `OPENAI_API_KEY` | For smoke tests if needed |

#### GitHub Environments
| Environment | Protection Rules |
|-------------|-----------------|
| `staging` | None (auto-deploy) |
| `production` | Required reviewers (1+), wait timer (optional) |

#### Azure Key Vault Secrets (per environment)
| Secret | Value |
|--------|-------|
| `OPENAI-API-KEY` | OpenAI API key |
| `DATABASE-URL` | PostgreSQL connection string |
| `REDIS-URL` | Redis connection string |
| `SESSION-SECRET-KEY` | Session encryption key |

### Phase 6: Smoke Tests & Monitoring
**Files to create:**

#### `scripts/smoke_test.sh`
```bash
#!/bin/bash
# Validates deployment by hitting health endpoints
# Args: $1 = base URL
# Checks: /health (200), /health/metrics (200), / (200)
# Retries: 5 attempts with 10s delay
# Exit 1 on failure (triggers rollback in CD)
```

#### Monitoring Setup
- Application Insights auto-instrumented via Container Apps
- Log Analytics workspace receives container logs
- Azure Monitor alerts for:
  - Container restart count > 3 in 5 min
  - HTTP 5xx rate > 5% in 5 min
  - Response latency P95 > 5s

---

## File Map Summary

### New Files (12)
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline (lint, test, build) |
| `.github/workflows/cd-staging.yml` | CD to staging (auto on merge) |
| `.github/workflows/cd-production.yml` | CD to production (manual approval) |
| `.github/workflows/infra.yml` | Infrastructure deployment |
| `.dockerignore` | Exclude non-essential files from Docker builds |
| `infra/main.bicep` | Azure infrastructure as code |
| `infra/parameters.staging.json` | Staging environment parameters |
| `infra/parameters.prod.json` | Production environment parameters |
| `scripts/smoke_test.sh` | Post-deployment health validation |
| `requirements-ui.txt` | Slim deps for Streamlit container |
| `docs/CICD.md` | CI/CD documentation |
| `docs/AZURE_SETUP.md` | Azure setup guide |

### Modified Files (4)
| File | Change |
|------|--------|
| `Dockerfile` | Add alembic copy, git SHA label, data dir |
| `Dockerfile.streamlit` | Use slim requirements-ui.txt |
| `README.md` | Add CI/CD badge, deployment section |
| `docker-compose.yml` | Add image tag vars for consistency |

---

## Test Requirements
- **CI pipeline tests:** Validate all 399+ existing tests pass in GitHub Actions with service containers
- **Smoke test script:** Integration test for deployed endpoints
- **Infrastructure validation:** Bicep what-if dry run in CI
- **Expected new tests:** ~10–15 tests for smoke test validation, config changes
  - Test smoke_test.sh exit codes
  - Test Dockerfile builds succeed
  - Test environment variable injection
  - Test health endpoint responses

---

## Dependencies on Prior Stories
- **SCRUM-21** (Documentation) — Completed. Provides existing docs structure to extend
- **SCRUM-19** (Error Handling) — Health endpoints `/health`, `/health/alerts`, `/health/metrics` already exist
- **SCRUM-20** (Performance Optimization) — Cache and metrics infrastructure in place
- All 20 completed stories — stable codebase with 399 passing tests

---

## Implementation Order
1. `.dockerignore` + Dockerfile optimizations (quick wins)
2. `ci.yml` — get CI running first (most value, fastest feedback)
3. `infra/main.bicep` + parameter files (infrastructure foundation)
4. `cd-staging.yml` — staging deployment
5. `cd-production.yml` — production with approval gates
6. `smoke_test.sh` — post-deploy validation
7. Documentation updates
8. Verify end-to-end flow
