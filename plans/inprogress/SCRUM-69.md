# SCRUM-69: Harden error handling — fix silent failures, add endpoint guards, improve resilience

## Acceptance Criteria
- [ ] GeneralResponseAgent returns success=False on exception
- [ ] All API endpoints have endpoint-level try-except with meaningful error responses
- [ ] Session parse failures logged with context and tracked in alerting
- [ ] Intent classifier returns classification_failed flag on errors
- [ ] Ingestion pipeline has per-batch error isolation (ALREADY DONE - SCRUM-67)
- [ ] All existing tests updated + new tests

## Items Already Done (SCRUM-67)
- Ingestion per-batch try-except with rollback ✓
