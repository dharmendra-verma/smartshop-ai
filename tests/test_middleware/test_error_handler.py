"""Tests for ErrorHandlerMiddleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.alerting import reset_alerts
from app.core.exceptions import (
    AgentRateLimitError,
    AgentTimeoutError,
    DatabaseError,
    SmartShopError,
)
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_id import RequestIdMiddleware


def _build_app(*routes):
    """Build a minimal FastAPI app with error handler middleware."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIdMiddleware)
    for path, exc in routes:
        _add_raising_route(app, path, exc)
    return app


def _add_raising_route(app: FastAPI, path: str, exc: Exception):
    @app.get(path, name=path.strip("/").replace("/", "_") or "root")
    async def _raise():
        raise exc


@pytest.fixture(autouse=True)
def _clean_alerts():
    reset_alerts()
    yield
    reset_alerts()


class TestRateLimitHandler:
    def test_returns_429(self):
        exc = AgentRateLimitError("limit hit", user_message="Too many requests.")
        app = _build_app(("/rate", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/rate")
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit"
        assert body["detail"] == "Too many requests."
        assert "request_id" in body


class TestTimeoutHandler:
    def test_returns_504(self):
        exc = AgentTimeoutError("timed out", user_message="Request timed out.")
        app = _build_app(("/timeout", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/timeout")
        assert resp.status_code == 504
        body = resp.json()
        assert body["error"] == "timeout"
        assert "request_id" in body


class TestDatabaseHandler:
    def test_returns_503(self):
        exc = DatabaseError("db down", user_message="Database unavailable.")
        app = _build_app(("/db", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/db")
        assert resp.status_code == 503
        assert resp.json()["error"] == "service_unavailable"


class TestSmartShopErrorHandler:
    def test_returns_500(self):
        exc = SmartShopError("oops", user_message="Something broke.")
        app = _build_app(("/err", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/err")
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Something broke."


class TestUnhandledExceptionHandler:
    def test_returns_500_generic(self):
        exc = RuntimeError("unexpected")
        app = _build_app(("/boom", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/boom")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "internal_error"
        assert "Please try again" in body["detail"]


class TestSQLAlchemyErrorHandler:
    def test_operational_error_returns_503(self):
        from sqlalchemy.exc import OperationalError

        exc = OperationalError("connection refused", None, Exception("orig"))
        app = _build_app(("/sa-op", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/sa-op")
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"] == "database_unavailable"
        assert "request_id" in body

    def test_interface_error_returns_503(self):
        from sqlalchemy.exc import InterfaceError

        exc = InterfaceError("interface error", None, Exception("orig"))
        app = _build_app(("/sa-iface", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/sa-iface")
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"] == "database_unavailable"
        assert "request_id" in body

    def test_sqlalchemy_error_records_database_component(self):
        from sqlalchemy.exc import OperationalError
        from app.core.alerting import get_alert_status

        exc = OperationalError("connection refused", None, Exception("orig"))
        app = _build_app(("/sa-alert", exc))
        TestClient(app, raise_server_exceptions=False).get("/sa-alert")
        assert get_alert_status().get("database", 0) >= 1
        assert get_alert_status().get("unhandled", 0) == 0

    def test_sqlalchemy_error_includes_request_id(self):
        from sqlalchemy.exc import OperationalError

        exc = OperationalError("connection refused", None, Exception("orig"))
        app = _build_app(("/sa-rid", exc))
        resp = TestClient(app, raise_server_exceptions=False).get("/sa-rid")
        assert "request_id" in resp.json()
