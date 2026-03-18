# SCRUM-63 — Add optional file logging with rotation support

## Story Details
- **ID:** SCRUM-63
- **Type:** Task
- **Priority:** Medium
- **Status:** In Progress

## Summary
Add `LOG_FILE` environment variable to write logs to file alongside console output using `RotatingFileHandler` (10MB max, 5 backups).

## Acceptance Criteria
- [x] `LOG_FILE` env var enables file logging alongside console
- [x] Uses `RotatingFileHandler` with 10MB max size and 5 backups
- [x] When `LOG_FILE` not set: no behaviour change — console-only
- [x] `LOG_FILE` setting integrated into the `Settings` class (currently uses raw `os.getenv`)
- [x] Comprehensive tests for file logging functionality
- [x] Documentation updated (env vars reference)

## Current State Analysis

### Already Implemented
The core file logging is **already in place** at `app/core/logging.py`:
- `RotatingFileHandler` with 10MB max / 5 backups / UTF-8 encoding
- Directory auto-creation via `os.makedirs`
- Dual output (console + file) when `LOG_FILE` is set
- Confirmation log message when file logging is active

### Gaps to Address
1. **Settings integration** — `LOG_FILE` is read via `os.getenv()` directly instead of through the `Settings` pydantic model (inconsistent with `LOG_LEVEL`)
2. **No tests** — Zero test coverage for file logging; no `test_logging.py` file exists
3. **No `.env.example` documentation** — `LOG_FILE` not documented in env example

## Technical Approach

### 1. Add `LOG_FILE` to Settings class
**File:** `app/core/config.py`

```python
# Add to Settings class, after LOG_LEVEL
LOG_FILE: str | None = None  # Optional file path for rotating file logs
```

### 2. Update `setup_logging()` to use Settings
**File:** `app/core/logging.py`

```python
# Replace: log_file = os.getenv("LOG_FILE")
# With:    log_file = settings.LOG_FILE
```

Remove the `import os` if no longer needed (check for `os.makedirs` — still needed for directory creation).

### 3. Create test file
**File:** `tests/test_core/test_logging.py`

Tests to write (~10-12 tests):

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | `test_setup_logging_default_console_only` | No file handler when `LOG_FILE` not set |
| 2 | `test_setup_logging_sets_correct_level` | Log level matches `LOG_LEVEL` setting |
| 3 | `test_setup_logging_with_file_creates_handler` | `RotatingFileHandler` added when `LOG_FILE` is set |
| 4 | `test_setup_logging_file_handler_rotation_config` | maxBytes=10MB, backupCount=5, encoding=utf-8 |
| 5 | `test_setup_logging_creates_log_directory` | `os.makedirs` called for missing parent dirs |
| 6 | `test_setup_logging_file_receives_messages` | Log messages written to the file |
| 7 | `test_setup_logging_console_still_works_with_file` | Console handler present even with file logging |
| 8 | `test_setup_logging_quietens_sqlalchemy` | SQLAlchemy logger set to WARNING |
| 9 | `test_setup_logging_quietens_uvicorn` | Uvicorn access logger set to INFO |
| 10 | `test_setup_logging_log_format` | Format matches expected pattern |
| 11 | `test_setup_logging_info_message_on_file_enabled` | "Logging to file" info logged when active |
| 12 | `test_settings_log_file_default_none` | `Settings.LOG_FILE` defaults to `None` |

**Test approach:**
- Use `tmp_path` fixture for file handler tests
- Use `monkeypatch` to set/unset `LOG_FILE` env var
- Reset root logger handlers between tests (important for isolation)
- Mock `get_settings()` to control `LOG_LEVEL` and `LOG_FILE`

### 4. Update `.env.example`
Add:
```
# LOG_FILE=logs/smartshop.log    # Optional: enable file logging with rotation (10MB max, 5 backups)
```

## File Map

| File | Action | Description |
|------|--------|-------------|
| `app/core/config.py` | MODIFY | Add `LOG_FILE: str \| None = None` to Settings |
| `app/core/logging.py` | MODIFY | Use `settings.LOG_FILE` instead of `os.getenv("LOG_FILE")` |
| `tests/test_core/test_logging.py` | CREATE | ~12 tests for logging setup |
| `.env.example` | MODIFY | Add `LOG_FILE` documentation |

## Test Requirements
- **New tests:** ~12
- **Expected total after:** ~442 (430 + 12)
- **Testing tools:** `tmp_path`, `monkeypatch`, `caplog`, mock `get_settings()`

## Dependencies on Prior Stories
- SCRUM-19 (Error Handling & Resilience) — established middleware logging patterns
- SCRUM-64 (CI/CD Pipeline) — CI runs all tests; this story must pass CI

## Estimated Effort
~30-45 minutes — mostly test creation; the core implementation is already done.
