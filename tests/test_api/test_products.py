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


def _setup_list_products_mock(db, products_with_counts=None, total=None):
    """Helper: set up mock DB for the list_products endpoint.

    products_with_counts is a list of (product_mock, review_count) tuples.
    The endpoint does: db.query(Product, count).outerjoin().group_by()
    then filters, counts, offsets, limits.
    """
    if products_with_counts is None:
        products_with_counts = []
    if total is None:
        total = len(products_with_counts)

    # The join/group query chain — returns (product, count) tuples
    join_query = db.query.return_value.outerjoin.return_value.group_by.return_value
    join_query.filter.return_value = join_query  # filter returns self
    join_query.offset.return_value.limit.return_value.all.return_value = (
        products_with_counts
    )

    # The count query chain — separate db.query(Product)
    # Since db.query is called twice, we need side_effect
    count_query = MagicMock()
    count_query.filter.return_value = count_query
    count_query.count.return_value = total

    # First call: db.query(Product, review_count_col) -> join chain
    # Second call: db.query(Product) -> count chain
    original_query = db.query
    call_count = {"n": 0}

    def query_side_effect(*args):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return original_query.return_value
        return count_query

    db.query.side_effect = query_side_effect


def test_list_products_empty():
    """Returns empty list when no products in DB."""
    db = MagicMock()
    _setup_list_products_mock(db, products_with_counts=[], total=0)
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_products_pagination():
    """Pagination fields are present and correct."""
    db = MagicMock()
    _setup_list_products_mock(db, products_with_counts=[], total=50)
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
    SAMPLE_PRODUCT.review_count = 5
    _setup_list_products_mock(db, products_with_counts=[(SAMPLE_PRODUCT, 5)], total=1)
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert "image_url" in items[0]


def test_list_products_includes_review_count():
    """review_count is populated from the reviews join."""
    db = MagicMock()
    product = MagicMock()
    product.id = "prod-002"
    product.name = "Reviewed Product"
    product.description = None
    product.price = Decimal("19.99")
    product.brand = "Brand"
    product.category = "electronics"
    product.stock = 10
    product.rating = 4.0
    product.image_url = None
    product.created_at = datetime(2026, 1, 1)
    _setup_list_products_mock(db, products_with_counts=[(product, 42)], total=1)
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["review_count"] == 42


def test_get_product_response_includes_image_url_field():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SAMPLE_PRODUCT
    app.dependency_overrides[get_db] = lambda: db

    response = client.get("/api/v1/products/prod-001")
    assert response.status_code == 200
    assert "image_url" in response.json()
