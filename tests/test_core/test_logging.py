"""Tests for logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import patch, MagicMock

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Reset root logger handlers between tests."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    # Clear handlers so basicConfig can re-apply
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    yield
    # Close any file handlers opened during the test
    for h in root.handlers:
        if isinstance(h, RotatingFileHandler):
            h.close()
    root.handlers = original_handlers
    root.level = original_level


@pytest.fixture
def _clear_settings_cache():
    """Clear the lru_cache on get_settings."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_settings(**overrides):
    """Create a mock Settings object with defaults."""
    defaults = {"LOG_LEVEL": "INFO", "LOG_FILE": None}
    defaults.update(overrides)
    s = MagicMock(spec=Settings)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


class TestSetupLoggingConsoleOnly:
    """Tests for console-only logging (no LOG_FILE)."""

    def test_no_file_handler_when_log_file_not_set(self):
        settings = _make_settings(LOG_FILE=None)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 0

    def test_sets_correct_log_level_info(self):
        settings = _make_settings(LOG_LEVEL="INFO")
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        assert logging.getLogger().level == logging.INFO

    def test_sets_correct_log_level_debug(self):
        settings = _make_settings(LOG_LEVEL="DEBUG")
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        assert logging.getLogger().level == logging.DEBUG

    def test_console_handler_present(self):
        settings = _make_settings(LOG_FILE=None)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1


class TestSetupLoggingWithFile:
    """Tests for file logging (LOG_FILE set)."""

    def test_file_handler_created(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_file_handler_rotation_config(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        root = logging.getLogger()
        file_handler = next(
            h for h in root.handlers if isinstance(h, RotatingFileHandler)
        )
        assert file_handler.maxBytes == 10 * 1024 * 1024
        assert file_handler.backupCount == 5
        assert file_handler.encoding == "utf-8"

    def test_creates_log_directory(self, tmp_path):
        log_dir = tmp_path / "subdir" / "nested"
        log_file = str(log_dir / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        assert log_dir.exists()

    def test_file_receives_messages(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        test_logger = logging.getLogger("test.file_write")
        test_logger.info("hello from test")

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        content = (tmp_path / "test.log").read_text(encoding="utf-8")
        assert "hello from test" in content

    def test_console_still_works_with_file(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        root = logging.getLogger()
        stream_handlers = [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, RotatingFileHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_info_message_on_file_enabled(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        settings = _make_settings(LOG_FILE=log_file)
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        content = (tmp_path / "test.log").read_text(encoding="utf-8")
        assert "Logging to file" in content


class TestSetupLoggingLibraryLevels:
    """Tests for third-party library log level overrides."""

    def test_quietens_sqlalchemy(self):
        settings = _make_settings()
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING

    def test_quietens_uvicorn_access(self):
        settings = _make_settings()
        with patch("app.core.logging.get_settings", return_value=settings):
            from app.core.logging import setup_logging

            setup_logging()

        assert logging.getLogger("uvicorn.access").level == logging.INFO


class TestSettingsLogFile:
    """Tests for LOG_FILE in Settings model."""

    def test_log_file_defaults_to_none(self, _clear_settings_cache):
        s = Settings(
            OPENAI_API_KEY="sk-test",
            DATABASE_URL="postgresql://localhost/test",
        )
        assert s.LOG_FILE is None

    def test_log_file_set_from_env(self, monkeypatch, _clear_settings_cache):
        monkeypatch.setenv("LOG_FILE", "/tmp/app.log")
        s = Settings(
            OPENAI_API_KEY="sk-test",
            DATABASE_URL="postgresql://localhost/test",
        )
        assert s.LOG_FILE == "/tmp/app.log"
