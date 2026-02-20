# SCRUM-15: Build FAQ & Policy Agent with RAG Implementation

## Status
Completed

## Technical Details
- Replaced stub methods with vector store based approach for retrieving policies.
- Built a FAISS-based vector store (`app/agents/policy/vector_store.py`) to chunk, embed, and efficiently index/query store policies.
- Introduced `PolicyAgent` running under `gpt-4o-mini` connected with the vector store tools to dynamically retrieve correct policies and form policy responses.
- `api/v1/policy.py` added with `POST /api/v1/policy/ask`, tied into `app/main.py` routing.
- FAISS vector database pre-indexing hook set on the FastAPI application startup event.
- Tested successfully by introducing unit and API tests under `tests/test_agents/test_policy_agent.py` and `tests/test_api/test_policy.py`.
- Final testing: test suite completed with 235 items passed.

## Time Spent
30 minutes
