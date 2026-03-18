# CI/CD Pipeline Documentation

## Overview

SmartShop AI uses GitHub Actions for continuous integration and deployment to Azure Container Apps.

## Pipeline Architecture

```
PR opened/updated
    └─> CI Workflow (ci.yml)
         ├─ Lint (ruff + black --check + mypy)
         ├─ Test (pytest with PostgreSQL + Redis services)
         └─ Build (Docker image build verification)

Push to main (merge)
    └─> CD Staging Workflow (cd-staging.yml)
         ├─ Build + push images to ACR
         ├─ Deploy to Azure Container Apps (staging)
         └─ Run smoke tests

Manual trigger (after staging verified)
    └─> CD Production Workflow (cd-production.yml)
         ├─ Require environment approval
         ├─ Deploy to Azure Container Apps (production)
         └─ Health check + rollback on failure
```

## Workflows

### CI Pipeline (`ci.yml`)
- **Triggers:** Push to `main`, PR to `main`
- **Jobs:**
  - `lint` — ruff, black --check, mypy
  - `test` — pytest with PostgreSQL 15 + Redis 7 service containers
  - `build` — Docker image build verification (API + UI)
  - `evals` (manual only) — real OpenAI eval tests (requires `OPENAI_API_KEY` secret)
- **Artifacts:** `results.xml` (JUnit), `coverage.xml`, `eval-results.xml` (manual runs)

### CD Staging (`cd-staging.yml`)
- **Triggers:** Push to `main` (after merge)
- **Jobs:**
  - `build-and-push` — Build + push images to ACR (tagged with git SHA + latest)
  - `deploy-staging` — Update Container Apps with new images
  - `smoke-test` — Validate health endpoints

### CD Production (`cd-production.yml`)
- **Triggers:** `workflow_dispatch` (manual) with image tag input
- **Environment:** `production` (requires GitHub Environment approval)
- **Rollback:** Automatically activates previous revision on health check failure

### Infrastructure (`infra.yml`)
- **Triggers:** Changes to `infra/**`, or manual dispatch
- **Actions:** Validates Bicep, runs what-if preview, deploys infrastructure

## Docker Images

| Image | Dockerfile | Port | Description |
|-------|-----------|------|-------------|
| `smartshop-api` | `Dockerfile` | 8000 | FastAPI backend |
| `smartshop-ui` | `Dockerfile.streamlit` | 8501 | Streamlit frontend |

Images are tagged with `GIT_SHA` for traceability and `latest` for convenience.

## Smoke Tests

The `scripts/smoke_test.sh` script validates deployments by checking:
- `GET /health` — Application health
- `GET /health/metrics` — Performance metrics
- `GET /health/alerts` — Alert status

Retries 10 times with 15-second delays before failing. Runs as `continue-on-error` in CD Staging.

## Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON for Azure CLI login |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key for agents + embeddings |
| `REDIS_URL` | Azure Cache for Redis connection string |

## GitHub Environments

| Environment | Protection Rules |
|-------------|-----------------|
| `staging` | None (auto-deploy on merge) |
| `production` | Required reviewers (1+) |
