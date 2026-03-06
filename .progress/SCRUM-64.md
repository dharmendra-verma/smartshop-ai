# SCRUM-64 — DevOps: CI/CD Pipeline with GitHub Actions & Azure Container Apps

## Status: Completed

## Summary

Implemented complete CI/CD pipeline with GitHub Actions workflows, Azure Container Apps infrastructure (Bicep IaC), Docker optimizations, smoke test script, and comprehensive documentation.

## Time Spent

~20 minutes total implementation time

## Files Created (16 new files)

| File | Description |
|------|-------------|
| `.github/workflows/ci.yml` | CI pipeline — lint, test (PostgreSQL + Redis services), Docker build |
| `.github/workflows/cd-staging.yml` | CD staging — build/push ACR, deploy Container Apps, smoke tests |
| `.github/workflows/cd-production.yml` | CD production — manual trigger, environment approval, rollback |
| `.github/workflows/infra.yml` | Infrastructure deployment — Bicep validate, what-if, deploy |
| `.dockerignore` | Exclude non-essential files from Docker builds |
| `infra/main.bicep` | Main Bicep template — subscription-level deployment |
| `infra/modules/resources.bicep` | Resource module — ACR, Container Apps, PostgreSQL, Redis, Key Vault, Log Analytics, App Insights |
| `infra/parameters.staging.json` | Staging environment parameters |
| `infra/parameters.prod.json` | Production environment parameters |
| `scripts/smoke_test.sh` | Post-deployment health validation (retry logic) |
| `requirements-ui.txt` | Slim dependencies for Streamlit container |
| `docs/CICD.md` | CI/CD pipeline documentation |
| `docs/AZURE_SETUP.md` | Azure infrastructure setup guide |
| `tests/test_core/test_cicd_infrastructure.py` | 31 tests for CI/CD infrastructure validation |
| `plans/inprogress/SCRUM-64.md` | Plan file (moved from plan/) |

## Files Modified (4)

| File | Change |
|------|--------|
| `Dockerfile` | Added GIT_SHA label, alembic copy, data dir copy |
| `Dockerfile.streamlit` | GIT_SHA label, switched to requirements-ui.txt |
| `README.md` | Added CI badge, CI/CD + Azure docs to index |
| `docker-compose.yml` | (no changes needed — already functional) |

## Tests

| File | New Tests |
|------|-----------|
| `tests/test_core/test_cicd_infrastructure.py` | 31 tests across 5 test classes |

### Test Classes
- `TestDockerfiles` (8 tests) — Dockerfile existence, labels, content
- `TestGitHubWorkflows` (9 tests) — Workflow existence, triggers, configuration
- `TestInfrastructure` (9 tests) — Bicep files, Azure resources
- `TestSmokeTestScript` (3 tests) — Script existence, endpoints, retry logic
- `TestDocumentation` (2 tests) — CI/CD and Azure docs

## Test Results

- **Before:** 399 unit tests
- **After:** 430 unit tests (399 + 31 new)
- **All new tests passing**
- **1 pre-existing flaky test** (`test_policy_dependencies_constructed`) — singleton state leak, not caused by this story
- **97 eval tests** skipped as expected (opt-in only)

## Acceptance Criteria

- [x] Dockerization — optimized multi-stage Dockerfiles with GIT_SHA labels, .dockerignore
- [x] GitHub Actions CI — lint (ruff, black, mypy), test (399+ tests with service containers), build
- [x] Azure Infrastructure (IaC) — Container Apps, ACR, PostgreSQL, Redis via Bicep
- [x] GitHub Actions CD — auto-deploy staging on merge, manual approval for production, rolling updates
- [x] Environment Configuration — secrets via GitHub Secrets, health probes, auto-scaling
- [x] Monitoring & Observability — Application Insights, Log Analytics, revision management
