# Troubleshooting Guide

---

## Startup Issues

### `ModuleNotFoundError: faiss`

FAISS is not installed. Install the CPU version:

```bash
pip install faiss-cpu
```

### `PolicyAgent not registered` / FAISS import warning

FAISS import failed silently. The PolicyAgent will be unavailable, but other agents work normally. Check:
1. `pip list | grep faiss`
2. System architecture compatibility (faiss-cpu requires x86_64 or ARM64)

### Application won't start

1. Check PostgreSQL is running: `pg_isready`
2. Check `DATABASE_URL` in `.env`
3. Run migrations: `alembic upgrade head`
4. Check port availability: `lsof -i :8000`

---

## Database Issues

### `Connection refused` / `could not connect to server`

PostgreSQL is not running.

```bash
# Docker
docker-compose up postgres

# Local
pg_ctl start -D /path/to/data
```

### `relation "products" does not exist`

Migrations haven't been applied:

```bash
alembic upgrade head
```

### `no results found` after startup

Data hasn't been loaded:

```bash
python -m scripts.load_data
```

---

## Redis Issues

### `Connection timed out` / `Error connecting to Redis`

Redis is not running. This is **non-fatal** — the system automatically falls back to in-memory TTLCache. To start Redis:

```bash
# Docker
docker-compose up redis

# Local
redis-server
```

### Cache not persisting across restarts

If using TTLCache fallback (no Redis), cache is in-memory and lost on restart. Use Redis for persistent caching.

---

## OpenAI / LLM Issues

### `RateLimitError` / HTTP 429

API quota exceeded. Options:
1. Wait for rate limit window to reset (usually 1 minute)
2. Increase your OpenAI API quota
3. The circuit breaker will temporarily disable the affected agent and fall back to the general agent

### `AuthenticationError` / `Invalid API key`

Check `OPENAI_API_KEY` in your `.env` file. Ensure it starts with `sk-`.

### `Timeout` / HTTP 504

LLM response took too long. The system will:
1. Raise `AgentTimeoutError`
2. Record a circuit breaker failure
3. After 3 failures, circuit opens for 30 seconds
4. Fall back to general agent or cached response

### Agent responses seem cached/stale

LLM cache has a 24-hour TTL. To clear:
1. Restart the application (clears TTLCache)
2. Or flush Redis: `redis-cli FLUSHDB`

---

## Agent Issues

### `AgentDependencies not in context`

The endpoint is not injecting dependencies correctly. Ensure:

```python
deps = AgentDependencies.from_db(db)
result = await agent.process(query, context={"deps": deps})
```

### Circuit breaker is OPEN

An agent had 3+ consecutive failures. It will automatically recover after 30 seconds (HALF_OPEN state). Check:
1. `GET /health/alerts` — see failure counts
2. Application logs for the root cause
3. OpenAI API status

### Intent classifier returns wrong intent

The IntentClassifier uses `gpt-4o-mini` for classification. If misclassifying:
1. Check the system prompt in `app/agents/orchestrator/intent_classifier.py`
2. Run eval tests: `RUN_EVALS=1 pytest tests/evals/test_eval_intent_classifier.py -v`
3. Review `score.explanation` for judge reasoning

---

## Streamlit UI Issues

### Blank page / connection error

FastAPI must be running before Streamlit:

```bash
# Start FastAPI first
uvicorn app.main:app --port 8000

# Then Streamlit
streamlit run app/ui/streamlit_app.py
```

### API calls failing from UI

Check the API URL configuration in `app/ui/api_client.py`. Default: `http://localhost:8000`.

---

## Eval Test Issues

### Eval tests not running (all skipped)

Both conditions must be met:

```bash
export OPENAI_API_KEY=sk-your-key
export RUN_EVALS=1
pytest tests/evals/ -v -m eval
```

### Judge scores unexpectedly low

1. Run calibration tests first: `RUN_EVALS=1 pytest tests/evals/test_eval_judge.py -v`
2. Check if agent prompts were recently changed
3. Review `score.explanation` for judge reasoning
4. Verify sample data in `tests/evals/conftest.py` matches expected schema

### `EvalScore` validation error

The judge returned an out-of-range float. Check:
1. `JUDGE_SYSTEM_PROMPT` in `tests/evals/judge.py`
2. OpenAI model behavior — try running with `-s` flag to see raw output

### Eval test assertion fails

Agent response quality may have degraded. Steps:
1. Check the specific `score.explanation`
2. Run the agent manually to inspect output
3. Check if agent system prompt changed
4. Verify mock data matches what the agent expects

---

## FAISS / Vector Store Issues

### `PolicyVectorStore` returns no results

1. Check that policies exist in the database
2. Delete `data/embeddings/faiss_index.bin` and restart to force rebuild
3. Check `OPENAI_API_KEY` — embeddings require a valid key

### Vector store rebuild on every startup

The policy count in the metadata file doesn't match the DB. This is normal after adding/removing policies. The rebuild takes a few seconds.

---

## Windows-Specific Issues

### Cannot delete files

Use truncation instead of deletion:

```bash
echo "" > file_to_clear
```

### Port already in use

```bash
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### Path length issues

Enable long paths in Windows or use shorter project paths.
