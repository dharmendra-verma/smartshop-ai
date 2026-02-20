# SCRUM-40 — Products Must Have Pictures in UI

## Story
All products should display a picture on the product listing and detail pages.
Product data already has a `picture` column (DB column `image_url`) with a picture URL.
Expose it through the product entity and API, then render it responsively in the UI.

## Acceptance Criteria
- [ ] `image_url` field surfaced from `Product` SQLAlchemy model
- [ ] `image_url` returned by `GET /api/v1/products` and `GET /api/v1/products/{id}`
- [ ] `image_url` included in recommendation agent responses
- [ ] All products that currently have NULL `image_url` seeded with deterministic placeholder URLs
- [ ] Product card UI renders the real image (or falls back to placehold.co gracefully)
- [ ] Images are responsive — fit card width, capped height, `object-fit: contain`
- [ ] Ingester forward-compatible: picks up `image_url` from CSV if the column is present

## Current Test Count
279 (after SCRUM-18). Target after this story: **287** (+8 new tests).

---

## Root Cause Analysis

| Layer | Current State | Gap |
|-------|--------------|-----|
| DB schema | `image_url VARCHAR(500)` created in migration `001` ✅ | Column may be missing if `create_all()` was used instead of Alembic |
| `Product` model | No `image_url` attribute | Must add `Column(String(500), nullable=True)` |
| `Product.to_dict()` | Does not include `image_url` | Must add key |
| `ProductIngestionSchema` | No `image_url` field | Must add `Optional[str]` |
| `ProductIngester` | Ignores `image_url` column | Must read from CSV row |
| `ProductResponse` schema | No `image_url` field | Must add `Optional[str]` |
| `ProductRecommendation` schema | No `image_url` field | Must add `Optional[str]` |
| DB data | All `image_url` values are NULL | Seed script needed |
| UI product card | Already reads `product.get("image_url")` with placehold.co fallback ✅ | No change needed |

---

## Architecture

```
CSV (optional image_url col)
         │
   ProductIngester._validate_row()
         │
   Product (SQLAlchemy model + image_url)
         │
   ┌─────┴──────────────────────────┐
   │                                │
GET /api/v1/products           RecommendationAgent.tools
   │   ProductResponse              │  to_dict() → ProductRecommendation
   │                                │
   └───────────────┬────────────────┘
                   │
         Streamlit product_card.py   ← already reads image_url ✅
```

---

## Tasks

### Task 1 — Alembic migration `002` (safety: add column if absent)

Create `alembic/versions/002_add_image_url_to_products.py`:

```python
"""add image_url to products (safe migration)

Revision ID: 002
Revises: 001
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" not in columns:
        op.add_column(
            "products",
            sa.Column("image_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" in columns:
        op.drop_column("products", "image_url")
```

> **Why:** The original migration `001` created `image_url` in its schema, but the
> running application may have used `Base.metadata.create_all()` instead of Alembic,
> meaning the column could be absent. This migration is idempotent — it checks before
> adding.

---

### Task 2 — Update `app/models/product.py`

Add `image_url` attribute to the SQLAlchemy model and `to_dict()`:

```python
# In column definitions, after `rating`:
image_url = Column(String(500), nullable=True)

# In to_dict():
"image_url": self.image_url,
```

Full updated `to_dict()`:
```python
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "name": self.name,
        "description": self.description,
        "price": float(self.price) if self.price is not None else None,
        "brand": self.brand,
        "category": self.category,
        "stock": self.stock,
        "rating": self.rating,
        "image_url": self.image_url,          # ← NEW
        "created_at": self.created_at.isoformat() if self.created_at else None,
        "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
```

---

### Task 3 — Update `app/schemas/product.py`

Add `image_url` to `ProductResponse`:

```python
class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    brand: Optional[str] = None
    category: str
    stock: Optional[int] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None          # ← NEW
    created_at: Optional[datetime] = None
```

---

### Task 4 — Update `app/schemas/recommendation.py`

Add `image_url` to `ProductRecommendation`:

```python
class ProductRecommendation(BaseModel):
    id: str
    name: str
    price: Decimal
    brand: Optional[str] = None
    category: str
    rating: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None          # ← NEW
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str
```

> **Note:** The recommendation agent builds `ProductRecommendation` from `to_dict()`
> output via the API endpoint in `app/api/v1/recommendations.py`. Since `to_dict()`
> will now include `image_url`, the endpoint must pass it through:
>
> ```python
> ProductRecommendation(
>     ...
>     image_url=r.get("image_url"),          # ← ADD
>     relevance_score=r["relevance_score"],
>     reason=r["reason"],
> )
> ```

---

### Task 5 — Update `app/schemas/ingestion.py`

Add `image_url` to `ProductIngestionSchema` (optional, forward-compatible):

```python
class ProductIngestionSchema(BaseModel):
    id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    stock: Optional[int] = Field(None, ge=0)
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    image_url: Optional[str] = Field(None, max_length=500)   # ← NEW
```

---

### Task 6 — Update `app/services/ingestion/product_ingester.py`

Two changes:

**6a — `_validate_row()`: read `image_url` from CSV row if present**
```python
image_url = row.get("image_url") or row.get("picture")
image_url = str(image_url).strip() if pd.notna(image_url) and image_url else None

return ProductIngestionSchema(
    ...
    image_url=image_url,    # ← NEW
)
```

**6b — `_insert_record()`: write `image_url` to the Product row**
```python
product = Product(
    id=record.id,
    name=record.name,
    description=record.description,
    price=record.price,
    brand=record.brand,
    category=record.category,
    stock=record.stock,
    rating=record.rating,
    image_url=record.image_url,    # ← NEW
)
```

---

### Task 7 — Seed script `scripts/seed_product_images.py`

Populate `image_url` for all products that currently have `NULL`, using
`picsum.photos` seeded URLs (deterministic per product ID, look like real photos):

```python
#!/usr/bin/env python3
"""
Seed image_url for products that have no picture yet.

Uses https://picsum.photos/seed/{n}/400/300 which returns a deterministic
real photograph based on the seed number (consistent across runs).
"""

import hashlib
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session_factory
from app.models.product import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _image_url_for(product_id: str) -> str:
    """
    Return a deterministic picsum.photos URL for a product.

    The seed is a 4-digit number derived from the product_id's MD5 hash,
    ensuring each product always gets the same image across re-runs.
    """
    digest = hashlib.md5(product_id.encode()).hexdigest()
    seed = int(digest[:4], 16) % 1000   # 0–999 picsum seeds
    return f"https://picsum.photos/seed/{seed}/400/300"


def seed_images(dry_run: bool = False) -> int:
    """
    Update products with NULL image_url.

    Returns:
        Number of rows updated.
    """
    Session = get_session_factory()
    updated = 0

    with Session() as session:
        products = session.query(Product).filter(Product.image_url.is_(None)).all()
        logger.info("Found %d products with no image_url", len(products))

        for product in products:
            url = _image_url_for(product.id)
            if not dry_run:
                product.image_url = url
            updated += 1
            logger.debug("  %s → %s", product.id, url)

        if not dry_run:
            session.commit()
            logger.info("Committed %d image_url updates", updated)
        else:
            logger.info("Dry-run: would update %d products", updated)

    return updated


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    count = seed_images(dry_run=dry)
    print(f"{'Would update' if dry else 'Updated'} {count} products.")
```

**Run after migration:**
```bash
python scripts/seed_product_images.py
# or dry-run first:
python scripts/seed_product_images.py --dry-run
```

---

### Task 8 — Update `app/api/v1/recommendations.py`

Pass `image_url` when constructing `ProductRecommendation` in the endpoint:

```python
recommendations = [
    ProductRecommendation(
        id=r["id"],
        name=r["name"],
        price=Decimal(str(r["price"])),
        brand=r.get("brand"),
        category=r["category"],
        rating=r.get("rating"),
        stock=r.get("stock"),
        image_url=r.get("image_url"),          # ← ADD
        relevance_score=r["relevance_score"],
        reason=r["reason"],
    )
    for r in data.get("recommendations", [])
]
```

---

### Task 9 — Tests (8 new tests, target 287)

#### `tests/test_models/test_product_model.py` — 2 tests (extend existing file)

```
test_product_to_dict_includes_image_url          # to_dict() has "image_url" key
test_product_to_dict_image_url_none_when_unset   # returns None when column not set
```

```python
def test_product_to_dict_includes_image_url():
    p = Product(
        id="TEST001", name="Widget", price=9.99, category="gadgets",
        image_url="https://picsum.photos/seed/42/400/300",
    )
    d = p.to_dict()
    assert "image_url" in d
    assert d["image_url"] == "https://picsum.photos/seed/42/400/300"

def test_product_to_dict_image_url_none_when_unset():
    p = Product(id="TEST002", name="Widget", price=9.99, category="gadgets")
    d = p.to_dict()
    assert d["image_url"] is None
```

#### `tests/test_api/test_products.py` — 2 tests (extend existing file)

```
test_list_products_response_includes_image_url_field   # field present in schema
test_get_product_response_includes_image_url_field     # field present in schema
```

```python
def test_list_products_response_includes_image_url_field(client, db_with_products):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    assert "image_url" in items[0]   # field always present (may be None)

def test_get_product_response_includes_image_url_field(client, db_with_products):
    resp = client.get("/api/v1/products/TEST001")
    assert resp.status_code == 200
    assert "image_url" in resp.json()
```

#### `tests/test_api/test_recommendations.py` — 2 tests (extend existing file)

```
test_recommendation_response_includes_image_url
test_recommendation_image_url_propagates_from_product
```

#### `tests/test_scripts/test_seed_product_images.py` — 2 tests

```
test_image_url_for_deterministic                # same product_id → same URL always
test_seed_images_dry_run_no_db_writes           # dry_run=True returns count, no commit
```

```python
from scripts.seed_product_images import _image_url_for

def test_image_url_for_deterministic():
    url1 = _image_url_for("SP0001")
    url2 = _image_url_for("SP0001")
    assert url1 == url2
    assert "picsum.photos" in url1
    assert "/400/300" in url1

def test_image_url_for_different_products_different_urls():
    assert _image_url_for("SP0001") != _image_url_for("SP0099")
```

---

## File Map

| File | Action |
|------|--------|
| `alembic/versions/002_add_image_url_to_products.py` | CREATE — safe migration |
| `app/models/product.py` | MODIFY — add `image_url` column + `to_dict()` |
| `app/schemas/product.py` | MODIFY — add `image_url` to `ProductResponse` |
| `app/schemas/recommendation.py` | MODIFY — add `image_url` to `ProductRecommendation` |
| `app/schemas/ingestion.py` | MODIFY — add `image_url` to `ProductIngestionSchema` |
| `app/services/ingestion/product_ingester.py` | MODIFY — read + write `image_url` |
| `app/api/v1/recommendations.py` | MODIFY — pass `image_url` to `ProductRecommendation` |
| `scripts/seed_product_images.py` | CREATE — populate NULL `image_url` rows |
| `tests/test_models/test_product_model.py` | MODIFY — 2 new tests |
| `tests/test_api/test_products.py` | MODIFY — 2 new tests |
| `tests/test_api/test_recommendations.py` | MODIFY — 2 new tests |
| `tests/test_scripts/test_seed_product_images.py` | CREATE — 2 new tests |
| `app/ui/components/product_card.py` | NO CHANGE — already handles `image_url` ✅ |

---

## Dependencies

- No new pip packages needed. `picsum.photos` is loaded client-side by browsers.
- SCRUM-18 already implemented the responsive image rendering in `product_card.py`.
- Migration `002` must run before the seed script.

## Complexity
**Low** — This is mostly a data plumbing task: expose an existing DB column through
all layers (model → schema → API → already-ready UI). The only non-trivial part is
the seed script for populating NULL `image_url` rows.

---

## Test Count Verification

| File | New Tests |
|------|----------|
| `test_product_model.py` | 2 |
| `test_products.py` | 2 |
| `test_recommendations.py` | 2 |
| `test_seed_product_images.py` | 2 |
| **Total new** | **8** |
| **Cumulative** | **287** |
