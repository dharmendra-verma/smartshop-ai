# Story: SCRUM-8 - Load initial product catalog dataset

## Story Overview
- **Epic**: SCRUM-2 (Phase 1: Foundation & Data Infrastructure)
- **Story Points**: 3
- **Priority**: Medium
- **Dependencies**: SCRUM-6 (Database schema - Done), SCRUM-7 (Data ingestion pipeline - Done), SCRUM-39 (Schema fix - Done)
- **Estimated Duration**: 1-2 hours
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-8

## Acceptance Criteria
- [ ] Load product catalog from CSV files in `data/raw/`
- [ ] Load reviews and policies from CSV files in `data/raw/`
- [ ] Load at least 1000+ products into database
- [ ] Verify data quality and completeness
- [ ] Create sample queries to test data access
- [ ] Document dataset sources and loading instructions

## Data Source

Pre-existing CSV files in `data/raw/`:

| File | Records | Columns |
|------|---------|---------|
| `products.csv` | 2000 | id, name, brand, category, price, description, stock, rating |
| `reviews.csv` | 4000 | product_id, rating, text, date |
| `store_policies.csv` | 22 | policy_type, description, conditions, timeframe |

No data generation or preprocessing scripts are needed — the data is already clean and ready for ingestion using the existing `scripts/ingest_data.py` pipeline from SCRUM-7.

## Implementation Plan

### Task 1: Load All Data into Database

**Purpose**: Use the existing ingestion pipeline (SCRUM-7) to load all CSV data from `data/raw/` into the database. Leverage `ProductIngester`, `ReviewIngester`, `PolicyIngester`, and `DataQualityMonitor`.

**Files to Create/Modify:**
- `scripts/load_catalog.py` (CREATE - orchestration script for full data load)

**Implementation Steps:**
1. Create `scripts/load_catalog.py` that orchestrates the full load process
2. Initialize database and create tables if needed
3. Use `ProductIngester` to load `data/raw/products.csv` (2000 products)
4. Use `ReviewIngester` to load `data/raw/reviews.csv` (4000 reviews)
5. Use `PolicyIngester` to load `data/raw/store_policies.csv` (22 policies)
6. Run `DataQualityMonitor` after each ingestion
7. Print detailed load summary (total loaded, categories breakdown, price distribution)
8. Support `--clean` flag to drop and recreate tables before loading

**Code Snippet Example:**
```python
#!/usr/bin/env python3
"""Load product catalog and related data into database."""

import argparse
import logging
import sys
from pathlib import Path
from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, get_session_factory, create_tables, drop_tables
from app.services.ingestion.product_ingester import ProductIngester
from app.services.ingestion.review_ingester import ReviewIngester
from app.services.ingestion.policy_ingester import PolicyIngester
from app.services.ingestion.quality_monitor import DataQualityMonitor
from app.models.product import Product

DATA_DIR = Path("data/raw")

def load_catalog(clean: bool = False, batch_size: int = 100):
    """Load the full product catalog into the database."""
    engine = get_engine()
    if clean:
        drop_tables(engine)
    create_tables(engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    monitor = DataQualityMonitor()

    # Load products
    ingester = ProductIngester(db_session=session, batch_size=batch_size)
    result = ingester.run(DATA_DIR / "products.csv")
    monitor.check(result, "products")

    # Load reviews
    ingester = ReviewIngester(db_session=session, batch_size=batch_size)
    result = ingester.run(DATA_DIR / "reviews.csv")
    monitor.check(result, "reviews")

    # Load policies
    ingester = PolicyIngester(db_session=session, batch_size=batch_size)
    result = ingester.run(DATA_DIR / "store_policies.csv")
    monitor.check(result, "policies")

    # Print category breakdown
    categories = session.query(Product.category, func.count()).group_by(Product.category).all()
    ...
```

**Dependencies:**
- All ingestion modules from SCRUM-7
- Database module from SCRUM-6
- CSV files in `data/raw/`

**Tests:**
- Database has 2000 products after load
- Database has 4000 reviews after load (minus any with invalid product_id)
- Database has 22 policies after load
- Quality report status is PASS for each
- No duplicate products in DB

**Validation Checklist:**
- [ ] 2000 products loaded into database
- [ ] Reviews loaded and linked to products
- [ ] Policies loaded
- [ ] Quality monitor reports PASS
- [ ] `--clean` flag works correctly
- [ ] Load script runs without errors

---

### Task 2: Verify Data Quality and Completeness

**Purpose**: Create a data verification script that queries the database and generates a comprehensive quality report — checking record counts, null rates, category distribution, price statistics, and data completeness.

**Files to Create/Modify:**
- `scripts/verify_data.py` (CREATE)

**Implementation Steps:**
1. Connect to the database
2. Query total record counts for products, reviews, policies tables
3. Check null rates for each column (should be 0% for required fields)
4. Generate category distribution (count per category)
5. Calculate price statistics (min, max, mean)
6. Check brand coverage (number of unique brands)
7. Print formatted verification report to stdout
8. Save report to `data/processed/data_quality_report.json`

**Code Snippet Example:**
```python
#!/usr/bin/env python3
"""Verify data quality and completeness in the database."""

import json
import sys
from pathlib import Path
from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, get_session_factory
from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy

def verify_data():
    """Run comprehensive data quality verification."""
    engine = get_engine()
    session = get_session_factory(engine)()

    report = {}
    report["products_count"] = session.query(func.count(Product.id)).scalar()
    report["reviews_count"] = session.query(func.count(Review.review_id)).scalar()
    report["policies_count"] = session.query(func.count(Policy.policy_id)).scalar()

    # Category distribution
    categories = session.query(
        Product.category, func.count()
    ).group_by(Product.category).all()
    report["categories"] = {cat: count for cat, count in categories}

    # Price statistics
    price_stats = session.query(
        func.min(Product.price),
        func.max(Product.price),
        func.avg(Product.price),
    ).first()
    report["price_stats"] = {
        "min": float(price_stats[0]),
        "max": float(price_stats[1]),
        "avg": round(float(price_stats[2]), 2),
    }

    session.close()
    return report
```

**Tests:**
- Products count == 2000
- Required fields have 0% null rate
- Multiple unique categories present
- Multiple unique brands present
- Price min > 0

**Validation Checklist:**
- [ ] Record counts verified (2000 products, reviews, policies)
- [ ] Null rates checked for all columns
- [ ] Category distribution is diverse
- [ ] Price statistics are reasonable
- [ ] Report saved to JSON

---

### Task 3: Create Sample Queries to Test Data Access

**Purpose**: Create a set of sample queries demonstrating that the loaded data can be accessed and queried effectively — including filtering, searching, aggregation, and joins.

**Files to Create/Modify:**
- `scripts/sample_queries.py` (CREATE)

**Implementation Steps:**
1. Create sample queries that exercise common data access patterns:
   - Search products by name (LIKE query)
   - Filter by category
   - Filter by price range
   - Get products with their reviews (JOIN)
   - Get average rating per product
   - Get top-rated products
   - Get products by brand
   - Get category summary (count, avg price per category)
2. Print formatted results for each query
3. Time each query to verify performance

**Code Snippet Example:**
```python
#!/usr/bin/env python3
"""Sample queries to demonstrate data access patterns."""

import time
import sys
from pathlib import Path
from sqlalchemy import func, or_

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, get_session_factory
from app.models.product import Product
from app.models.review import Review

def run_sample_queries():
    engine = get_engine()
    session = get_session_factory(engine)()

    # Query 1: Search products by name
    results = session.query(Product).filter(
        Product.name.ilike("%phone%")
    ).all()
    print(f"Products matching 'phone': {len(results)}")

    # Query 2: Filter by category and price range
    results = session.query(Product).filter(
        Product.category == "smartphone",
        Product.price.between(50, 500)
    ).all()
    print(f"Smartphones $50-$500: {len(results)}")

    # Query 3: Category summary
    summary = session.query(
        Product.category,
        func.count().label("count"),
        func.avg(Product.price).label("avg_price")
    ).group_by(Product.category).all()

    # Query 4: Top-rated products (with reviews)
    top_rated = session.query(
        Product.name,
        func.avg(Review.rating).label("avg_rating"),
        func.count(Review.review_id).label("review_count")
    ).join(Review, Product.id == Review.product_id).group_by(
        Product.id
    ).order_by(
        func.avg(Review.rating).desc()
    ).limit(10).all()

    session.close()
```

**Dependencies:**
- SQLAlchemy, database models
- Data must be loaded (Task 1)

**Tests:**
- Each query returns results (non-empty for expected matches)
- Join queries work correctly
- Aggregation queries return sensible values
- Queries complete within reasonable time (<1s each)

**Validation Checklist:**
- [ ] Search by name works
- [ ] Category filter works
- [ ] Price range filter works
- [ ] JOIN with reviews works
- [ ] Aggregation queries work
- [ ] All queries complete without errors

---

### Task 4: Document Dataset and Loading Instructions

**Purpose**: Create documentation for the dataset — data dictionary, file structure, and loading instructions.

**Files to Create/Modify:**
- `data/README.md` (CREATE)
- `docs/data-loading.md` (CREATE)

**Implementation Steps:**
1. Create `data/README.md` with:
   - Dataset overview (what data is included)
   - Data dictionary (column descriptions for each CSV)
   - File structure (`data/raw/`)
   - Record counts
2. Create `docs/data-loading.md` with:
   - Prerequisites (PostgreSQL running, .env configured)
   - Step-by-step loading instructions using `scripts/load_catalog.py`
   - Verification steps using `scripts/verify_data.py`
   - Troubleshooting guide

**Validation Checklist:**
- [ ] Data README created with dictionary
- [ ] Loading instructions documented
- [ ] File structure documented

---

### Task 5: Write Comprehensive Tests

**Purpose**: Write tests for the load, verify, and sample query scripts.

**Files to Create/Modify:**
- `tests/test_scripts/test_load_catalog.py` (CREATE)
- `tests/test_scripts/test_verify_data.py` (CREATE)
- `tests/test_scripts/__init__.py` (CREATE)

**Implementation Steps:**
1. Test catalog loading: products, reviews, policies all loaded correctly
2. Test data verification: report structure is correct, checks pass
3. Test sample queries: each query pattern returns expected result shapes
4. Integration test: load -> verify pipeline

**Dependencies:**
- `pytest`, `pytest-cov`
- Test fixtures for in-memory SQLite DB

**Validation Checklist:**
- [ ] Load tests pass
- [ ] Verification tests pass
- [ ] Integration test passes
- [ ] Coverage >85%

---

## Integration Testing

**Integration Test Scenarios:**

1. **Scenario 1: Full Pipeline - Load and Verify**
   - Setup: Clean database, no existing data
   - Steps:
     1. Run `python scripts/load_catalog.py --clean`
     2. Run `python scripts/verify_data.py`
     3. Run `python scripts/sample_queries.py`
   - Expected: 2000 products, 4000 reviews, 22 policies loaded; quality PASS; all queries return results

2. **Scenario 2: Idempotent Load (Deduplication)**
   - Setup: Database already has data loaded
   - Steps:
     1. Run `python scripts/load_catalog.py` again (without --clean)
     2. Check product count unchanged (all deduplicated)
   - Expected: No new records added, all marked as duplicates

**Manual Testing Steps:**
1. Ensure PostgreSQL is running and `.env` is configured
2. Run `python scripts/load_catalog.py --clean` — verify all data loaded
3. Run `python scripts/verify_data.py` — verify quality report
4. Run `python scripts/sample_queries.py` — verify all queries work

---

## Completion Checklist

### Code Quality
- [ ] All scripts created (load, verify, sample queries)
- [ ] Code follows project style guide
- [ ] Type hints added
- [ ] Docstrings for all functions
- [ ] No linting errors

### Testing
- [ ] Load tests passing
- [ ] Verification tests passing
- [ ] Integration test passing
- [ ] Test coverage >85%

### Acceptance Criteria
- [ ] Load product catalog from CSV files in `data/raw/`
- [ ] Load reviews and policies from CSV files in `data/raw/`
- [ ] Load at least 1000+ products into database
- [ ] Verify data quality and completeness
- [ ] Create sample queries to test data access
- [ ] Document dataset sources and loading instructions

### Deployment Readiness
- [ ] All dependencies already in requirements.txt
- [ ] Database migrations handled (create_tables)
- [ ] Scripts executable from project root

---

## Jira Status Update

**Current Status**: In Progress
**Target Status**: Done

**Completion Comment Template:**
```
Story SCRUM-8 completed successfully!

**Implemented:**
- Database loading script using SCRUM-7 ingestion pipeline
- Data quality verification with comprehensive report
- Sample query scripts demonstrating all access patterns
- Full documentation (data dictionary, loading guide)

**Data Source:** Pre-existing CSV files in data/raw/
- products.csv (2000 products)
- reviews.csv (4000 reviews)
- store_policies.csv (22 policies)

**Files Created:**
- scripts/load_catalog.py (DB loading orchestrator)
- scripts/verify_data.py (quality verification)
- scripts/sample_queries.py (query examples)
- data/README.md (data documentation)
- docs/data-loading.md (loading instructions)
- Test suite in tests/test_scripts/

**Data Loaded:**
- Products: 2000 records
- Reviews: 4000 records
- Policies: 22 records

**Testing:**
- Unit tests: all passing
- Integration test: full pipeline passing
- Data quality: PASS (>95% success rate)
- Coverage: >85%

**Next Steps:**
- Ready for SCRUM-9 (next story in Phase 1)
```

---

## Known Issues / Blockers

- PostgreSQL must be running and accessible for data loading
- `.env` file must have correct `DATABASE_URL` configured

---

## Time Tracking

- **Estimated Time**: 1-2 hours
- **Actual Time**: _[To be filled during execution]_
- **Variance**: _[To be calculated]_

---

## Notes & Learnings

- **Design Decision**: Use pre-existing CSV data in `data/raw/` instead of generating synthetic data — real data is already available with good volume (2000 products, 4000 reviews, 22 policies)
- **Reuse**: Leverages SCRUM-7 ingestion pipeline (ProductIngester, ReviewIngester, PolicyIngester, DataQualityMonitor) and existing `ingest_data.py` CLI
- **Simplification**: Removed generate/preprocess steps since raw data is already clean and correctly structured
