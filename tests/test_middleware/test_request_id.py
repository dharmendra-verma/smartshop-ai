"""Tests for RequestIdMiddleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.request_id import RequestIdMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo-id")
    async def echo_id(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return app


@pytest.fixture()
def client():
    return TestClient(_build_app())


class TestRequestId:
    def test_header_present(self, client):
        resp = client.get("/echo-id")
        assert "X-Request-Id" in resp.headers
        assert len(resp.headers["X-Request-Id"]) == 8

    def test_id_in_request_state(self, client):
        resp = client.get("/echo-id")
        body = resp.json()
        assert body["request_id"] is not None
        assert body["request_id"] == resp.headers["X-Request-Id"]

    def test_unique_per_request(self, client):
        ids = {client.get("/echo-id").headers["X-Request-Id"] for _ in range(5)}
        assert len(ids) == 5
