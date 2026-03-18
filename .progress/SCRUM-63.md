# SCRUM-63 — Add optional file logging with rotation support

## Status: Completed

## Summary

Integrated `LOG_FILE` into the Settings pydantic model, updated `setup_logging()` to use it instead of raw `os.getenv()`, added `force=True` to `basicConfig` for reliable reconfiguration, created 14 comprehensive tests, and documented the env var in `.env.example`.

## Time Spent

~15 minutes

## Files Modified

| File | Change |
|------|--------|
| `app/core/config.py` | Added `LOG_FILE: str \| None = None` to Settings class |
| `app/core/logging.py` | Use `settings.LOG_FILE` instead of `os.getenv("LOG_FILE")`; added `force=True` to `basicConfig` |
| `.env.example` | Added `LOG_FILE` documentation |
| `tests/test_core/test_logging.py` | **Created** — 14 tests |
| `plans/inprogress/SCRUM-63.md` | Moved from `plans/plan/` |

## Tests

- **Before:** 430 tests
- **New:** 14 tests
- **Expected total:** 444

## Acceptance Criteria

- [x] `LOG_FILE` env var enables file logging alongside console
- [x] Uses `RotatingFileHandler` with 10MB max size and 5 backups
- [x] When `LOG_FILE` not set: no behaviour change — console-only
- [x] `LOG_FILE` setting integrated into the `Settings` class
- [x] Comprehensive tests for file logging functionality (14 tests)
- [x] Documentation updated (`.env.example`)
