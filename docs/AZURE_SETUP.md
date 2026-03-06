# Azure Setup Guide

## Prerequisites

- Azure CLI installed and authenticated
- Azure subscription with Contributor access
- GitHub repository with Actions enabled

## Infrastructure Overview

SmartShop AI deploys to Azure Container Apps with the following resources:

| Resource | Service | Purpose |
|----------|---------|---------|
| Container Registry | ACR | Docker image storage |
| Container Apps Environment | CAE | Shared hosting environment |
| Container App: API | CA | FastAPI backend (port 8000) |
| Container App: UI | CA | Streamlit frontend (port 8501) |
| PostgreSQL Flexible Server | PG | Application database |
| Azure Cache for Redis | Redis | Caching + sessions |
| Key Vault | KV | Secret management |
| Log Analytics | LA | Container logs |
| Application Insights | AI | APM + telemetry |

## Deployment

### 1. Create Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "smartshop-github-actions" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth
```

Save the JSON output as the `AZURE_CREDENTIALS` GitHub secret.

### 2. Deploy Infrastructure

```bash
# Staging
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/parameters.staging.json

# Production
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/parameters.prod.json
```

### 3. Configure Key Vault Secrets

```bash
ENV=staging  # or prod
az keyvault secret set --vault-name kv-smartshop-$ENV --name OPENAI-API-KEY --value "<key>"
az keyvault secret set --vault-name kv-smartshop-$ENV --name DATABASE-URL --value "<conn_string>"
az keyvault secret set --vault-name kv-smartshop-$ENV --name REDIS-URL --value "<redis_url>"
az keyvault secret set --vault-name kv-smartshop-$ENV --name SESSION-SECRET-KEY --value "<secret>"
```

### 4. Configure GitHub Secrets

In your GitHub repo settings, add:
- `AZURE_CREDENTIALS` — Service principal JSON from step 1

### 5. Configure GitHub Environments

- Create `staging` environment (no protection rules)
- Create `production` environment with required reviewers

## Environment Parameters

### Staging (`parameters.staging.json`)
- ACR: Basic SKU
- DB: Standard_B1ms (burstable)
- Redis: Basic C0 (256MB)
- API: 1-3 replicas
- UI: 1-2 replicas

### Production (`parameters.prod.json`)
- ACR: Standard SKU
- DB: Standard_B2s (burstable)
- Redis: Basic C0
- API: 2-5 replicas
- UI: 1-3 replicas

## Scaling

Container Apps auto-scale based on HTTP concurrent requests:
- API: scales at 10 concurrent requests per replica
- UI: scales at 20 concurrent requests per replica

## Health Probes

| App | Liveness | Readiness |
|-----|----------|-----------|
| API | `GET /health` (30s interval) | `GET /health` (10s interval) |
| UI | `GET /_stcore/health` (30s interval) | — |
