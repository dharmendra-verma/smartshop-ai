# Story: SCRUM-9 — Set up FastAPI backend scaffolding with basic endpoints

## Story Overview
- **Epic**: SCRUM-2 (Phase 1: Foundation & Data Infrastructure)
- **Story Points**: 5
- **Priority**: Medium
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-9
- **Complexity**: Medium
- **Estimated Duration**: 2–3 hours

## Dependencies
- SCRUM-6 ✅ — Database schema (Product, Review, Policy models in `app/models/`)
- SCRUM-7 ✅ — Ingestion pipeline (data available in DB)
- SCRUM-8 ✅ — Product catalog loaded (data/raw CSVs ingested)
- SCRUM-39 ✅ — Schema fixes applied

## What Already Exists (Do NOT recreate)
| File | Status | Notes |
|------|--------|-------|
| `app/main.py` | ✅ Exists | FastAPI app, CORS, health router |
| `app/api/health.py` | ✅ Exists | `GET /health`, `GET /` |
| `app/core/config.py` | ✅ Exists | pydantic-settings, all env vars |
| `app/core/database.py` | ✅ Exists | `get_engine()`, `get_db()` FastAPI dependency |
| `app/models/product.py` | ✅ Exists | Product SQLAlchemy model |
| `app/models/review.py` | ✅ Exists | Review SQLAlchemy model |
| `app/models/policy.py` | ✅ Exists | Policy SQLAlchemy model |

## Acceptance Criteria
- [ ] FastAPI project structure created (v1 API router layer added)
- [ ] Health check endpoint working (`GET /health`) — already exists, verify
- [ ] Database connection pooling configured — already in `database.py`, verify
- [ ] Environment variable management via `.env` — already in `config.py`, verify
- [ ] CORS configuration for frontend — already in `main.py`, verify
- [ ] API documentation auto-generated (Swagger at `/docs`, ReDoc at `/redoc`)
- [ ] Basic error handling middleware added
- [ ] Logging configuration added
- [ ] `GET /api/v1/products` — List products with pagination, filter by category/brand
- [ ] `GET /api/v1/products/{id}` — Get product by ID with 404 handling

---

## Technical Approach

The scaffold already has a working FastAPI app. This story adds:
1. **Versioned API layer** — `app/api/v1/` package with a products router
2. **Pydantic response schemas** — `app/schemas/product.py` for clean API contracts
3. **Error handling middleware** — catches unhandled exceptions, returns JSON errors
4. **Structured logging** — replaces `print()` with proper logging using Python `logging`
5. **Wire everything into `main.py`** — include v1 router, add middleware, init logging

---

## File Structure Needed

```
app/
├── api/
│   ├── __init__.py          ✅ exists
│   ├── health.py            ✅ exists
│   └── v1/
│       ├── __init__.py      ← CREATE (router aggregator)
│       └── products.py      ← CREATE (product endpoints)
├── core/
│   ├── config.py            ✅ exists
│   ├── database.py          ✅ exists
│   └── logging.py           ← CREATE (logging setup)
├── middleware/
│   ├── __init__.py          ← CREATE
│   └── error_handler.py     ← CREATE (global error handler)
├── schemas/
│   ├── __init__.py          ✅ exists (ingestion schemas)
│   └── product.py           ← CREATE (API response schemas)
└── main.py                  ← MODIFY (add v1 router, middleware, logging)

tests/
└── test_api/
    ├── __init__.py          ← CREATE
    ├── test_health.py       ← CREATE
    └── test_products.py     ← CREATE
```

---

## Implementation Tasks

### Task 1: Create Pydantic API Response Schemas

**File**: `app/schemas/product.py`

**Purpose**: Define clean Pydantic v2 response models for the API layer (separate from DB models and ingestion schemas).

```python
"""Pydantic schemas for Product API responses."""

from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional


class ProductResponse(BaseModel):
    """Single product API response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    brand: Optional[str] = None
    category: str
    stock: Optional[int] = None
    rating: Optional[float] = None
    created_at: Optional[datetime] = None


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int
```

**Validation checklist**:
- [ ] `ProductResponse` maps correctly from SQLAlchemy `Product` model using `from_attributes=True`
- [ ] `ProductListResponse` includes pagination metadata
- [ ] All optional fields handle `None` gracefully

---

### Task 2: Create v1 Products Router

**File**: `app/api/v1/products.py`

**Purpose**: Implement `GET /api/v1/products` (list with filters + pagination) and `GET /api/v1/products/{id}` (single product with 404).

```python
"""Product API endpoints — v1."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse, ProductListResponse

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    db: Session = Depends(get_db),
):
    """List products with optional filtering and pagination."""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    total = query.count()
    pages = (total + page_size - 1) // page_size
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product
```

**File**: `app/api/v1/__init__.py`

```python
"""API v1 router — aggregates all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import products

router = APIRouter()
router.include_router(products.router)
```

**Validation checklist**:
- [ ] `GET /api/v1/products` returns paginated list
- [ ] `?category=` and `?brand=` filters work (case-insensitive)
- [ ] `?page=` and `?page_size=` pagination works
- [ ] `GET /api/v1/products/{id}` returns product or 404
- [ ] Response matches `ProductResponse` schema

---

### Task 3: Create Error Handling Middleware

**File**: `app/middleware/__init__.py` — empty init

**File**: `app/middleware/error_handler.py`

**Purpose**: Catch unhandled exceptions and return consistent JSON error responses instead of HTML tracebacks.

```python
"""Global error handling middleware."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware for unhandled exceptions."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled exception: %s %s — %s",
                request.method,
                request.url.path,
                str(exc),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred. Please try again.",
                    "path": str(request.url.path),
                },
            )
```

**Validation checklist**:
- [ ] Unhandled exceptions return JSON (not HTML)
- [ ] Error is logged with full traceback
- [ ] 404 from `HTTPException` still passes through correctly (middleware only catches unhandled)

---

### Task 4: Create Logging Configuration

**File**: `app/core/logging.py`

**Purpose**: Configure structured logging for the application — replaces bare `print()` calls.

```python
"""Logging configuration for SmartShop AI."""

import logging
import sys
from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging."""
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quieten noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured at level: %s", settings.LOG_LEVEL)
```

**Validation checklist**:
- [ ] `setup_logging()` can be called at startup without errors
- [ ] Log level is read from `settings.LOG_LEVEL`
- [ ] SQLAlchemy engine logs are suppressed at WARNING level

---

### Task 5: Update `app/main.py`

**Purpose**: Wire in the v1 router, error handler middleware, and logging. Replace bare `print()` with `logger`.

**Modifications**:

```python
"""SmartShop AI - Main FastAPI Application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api import health
from app.api.v1 import router as v1_router
from app.middleware.error_handler import ErrorHandlerMiddleware

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Driven Multi-Agent E-commerce Assistant",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (order matters — error handler wraps everything)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(v1_router)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Docs: http://%s:%s/docs", settings.API_HOST, settings.API_PORT)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down %s", settings.APP_NAME)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
```

**Validation checklist**:
- [ ] App starts without import errors
- [ ] `GET /docs` renders Swagger UI
- [ ] `GET /redoc` renders ReDoc UI
- [ ] `GET /health` still works
- [ ] `GET /api/v1/products` accessible
- [ ] CORS origins use `settings.CORS_ORIGINS` (not wildcard `"*"`)

---

### Task 6: Write Tests

**File**: `tests/test_api/__init__.py` — empty

**File**: `tests/test_api/test_health.py`

```python
"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


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
```

**File**: `tests/test_api/test_products.py`

```python
"""Tests for product API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
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
    assert data["name"] == "Test Product"
    assert data["category"] == "electronics"
```

**Validation checklist**:
- [ ] All health tests pass
- [ ] Product list returns 200 with correct structure
- [ ] Pagination fields (`page`, `page_size`, `pages`, `total`) present
- [ ] 404 returned for unknown product ID
- [ ] 200 returned with correct fields for known product

---

## Integration Testing

**Manual steps** (after implementation):
```bash
# Start the server
cd smartshop-ai
uvicorn app.main:app --reload --port 8080

# Test health
curl http://localhost:8080/health

# List products (first page)
curl "http://localhost:8080/api/v1/products?page=1&page_size=5"

# Filter by category
curl "http://localhost:8080/api/v1/products?category=electronics"

# Get single product (use a real ID from the DB)
curl http://localhost:8080/api/v1/products/PROD001

# Check Swagger docs
open http://localhost:8080/docs
```

---

## Completion Checklist

### Code
- [ ] `app/schemas/product.py` created with `ProductResponse` and `ProductListResponse`
- [ ] `app/api/v1/__init__.py` created
- [ ] `app/api/v1/products.py` created with both endpoints
- [ ] `app/middleware/__init__.py` created
- [ ] `app/middleware/error_handler.py` created
- [ ] `app/core/logging.py` created
- [ ] `app/main.py` updated (v1 router, middleware, logging)
- [ ] No linting errors (flake8/ruff)
- [ ] Type hints on all functions

### Testing
- [ ] `tests/test_api/__init__.py` created
- [ ] `tests/test_api/test_health.py` — all tests passing
- [ ] `tests/test_api/test_products.py` — all tests passing
- [ ] Coverage > 85% for new modules

### Acceptance Criteria (from Jira)
- [ ] FastAPI project structure created (v1 layer)
- [ ] Health check endpoint working
- [ ] Database connection pooling configured
- [ ] Environment variable management working
- [ ] CORS configured
- [ ] API docs auto-generated (`/docs`, `/redoc`)
- [ ] Error handling middleware added
- [ ] Logging configured
- [ ] `GET /api/v1/products` works with pagination and filters
- [ ] `GET /api/v1/products/{id}` works with 404

---

## Jira Completion Comment Template
```
Story SCRUM-9 completed successfully!

**Implemented:**
- Versioned API layer (app/api/v1/) with product endpoints
- Pydantic v2 response schemas for clean API contracts
- Global error handling middleware (JSON errors, not HTML tracebacks)
- Structured logging configuration (replaces print statements)
- Updated main.py to wire all new components

**Endpoints:**
- GET /health — health check ✅
- GET /api/v1/products — list with pagination + category/brand filters ✅
- GET /api/v1/products/{id} — single product with 404 handling ✅
- GET /docs — Swagger UI ✅
- GET /redoc — ReDoc UI ✅

**Files Created:**
- app/schemas/product.py
- app/api/v1/__init__.py
- app/api/v1/products.py
- app/middleware/__init__.py
- app/middleware/error_handler.py
- app/core/logging.py
- tests/test_api/__init__.py
- tests/test_api/test_health.py
- tests/test_api/test_products.py

**Files Modified:**
- app/main.py (v1 router, middleware, logging wired in)

**Testing:** All tests passing, coverage > 85%

**Next Steps:** Ready for SCRUM-10 (Product Recommendation Agent)
```

---

## Time Tracking
- **Estimated**: 2–3 hours
- **Actual**: _[To be filled during execution]_
