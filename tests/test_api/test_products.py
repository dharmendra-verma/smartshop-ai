"""Tests for product API endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime

from app.main import app
from app.core.database import get_db

# Sample product fixture
SAMPLE_PRODUCT = MagicMock()
SAMPLE_PRODUCT.id = "prod-001"
SAMPLE_PRODUCT.name = "Test Product"
SAMPLE_PRODUCT.description = "A test product"
SAMPLE_PRODUCT.price = Decimal("29.99")
SAMPLE_PRODUCT.brand = "TestBrand"
SAMPLE_PRODUCT.category = "electronics"
SAMPLE_PRODUCT.stock = 50
SAMPLE_PRODUCT.rating = 4.5
SAMPLE_PRODUCT.image_url = "https://example.com/image.png"
SAMPLE_PRODUCT.created_at = datetime(2026, 1, 1)


def mock_db():
    db = MagicMock()
    return db


app.dependency_overrides[get_db] = mock_db
client = TestClient(app)


def test_list_products_empty():
    """Returns empty list when no products in DB."""
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.count.return_value = 0
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_products_pagination():
    """Pagination fields are present and correct."""
    db = MagicMock()
    db.query.return_value.count.return_value = 50
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert data["pages"] == 5


def test_get_product_not_found():
    """Returns 404 for unknown product ID."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_product_found():
    """Returns product when ID exists."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SAMPLE_PRODUCT
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products/prod-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "prod-001"
    assert data["category"] == "electronics"


def test_list_products_response_includes_image_url_field():
    db = MagicMock()
    db.query.return_value.count.return_value = 1
    db.query.return_value.offset.return_value.limit.return_value.all.return_value = [SAMPLE_PRODUCT]
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert "image_url" in items[0]


def test_get_product_response_includes_image_url_field():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SAMPLE_PRODUCT
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products/prod-001")
    assert response.status_code == 200
    assert "image_url" in response.json()
