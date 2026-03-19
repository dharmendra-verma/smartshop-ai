"""Tests for health check endpoints."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, InterfaceError
from app.main import app

client = TestClient(app)


def _mock_engine_ok():
    """Return a mock engine whose connect() succeeds."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return engine


def _mock_engine_fail(exc):
    """Return a mock engine whose connect() raises exc."""
    engine = MagicMock()
    engine.connect.side_effect = exc
    return engine


def test_health_check():
    with patch("app.api.health.get_engine", return_value=_mock_engine_ok()):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "timestamp" in data


def test_health_db_connected():
    with patch("app.api.health.get_engine", return_value=_mock_engine_ok()):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


def test_health_db_operational_error():
    exc = OperationalError("connection refused", None, Exception("orig"))
    with patch("app.api.health.get_engine", return_value=_mock_engine_fail(exc)):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unreachable"


def test_health_db_interface_error():
    exc = InterfaceError("interface error", None, Exception("orig"))
    with patch("app.api.health.get_engine", return_value=_mock_engine_fail(exc)):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unreachable"


def test_health_always_returns_200_when_db_down():
    exc = OperationalError("db down", None, Exception("orig"))
    with patch("app.api.health.get_engine", return_value=_mock_engine_fail(exc)):
        response = client.get("/health")
    assert response.status_code == 200


def test_health_response_fields():
    with patch("app.api.health.get_engine", return_value=_mock_engine_ok()):
        response = client.get("/health")
    data = response.json()
    for key in ("status", "service", "version", "timestamp", "database"):
        assert key in data


def test_health_alerts_still_works():
    response = client.get("/health/alerts")
    assert response.status_code == 200
    assert "alerts" in response.json()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_available():
    response = client.get("/redoc")
    assert response.status_code == 200
