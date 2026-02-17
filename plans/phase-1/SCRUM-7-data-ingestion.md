# Story: SCRUM-7 - Build data ingestion pipeline for product catalogs and reviews

## 📋 Story Overview
- **Epic**: SCRUM-2 (Phase 1: Foundation & Data Infrastructure)
- **Story Points**: 5
- **Priority**: High
- **Dependencies**: SCRUM-6 (Database schema - ✅ Done)
- **Estimated Duration**: 3-4 hours
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-7

## 🎯 Acceptance Criteria
- [ ] CSV import functionality for product catalogs
- [ ] Review data ingestion from CSV datasets
- [ ] Data validation using Pydantic models
- [ ] Automated deduplication logic
- [ ] Error handling and logging
- [ ] Batch processing capability
- [ ] Data quality monitoring alerts

## 🛠️ Implementation Plan

### Task 1: Create Pydantic Validation Schemas for Ingestion

**Purpose**: Define strict data validation models that validate incoming CSV/raw data before database insertion, catching malformed records early.

**Files to Create/Modify:**
- `app/schemas/ingestion.py` (CREATE)
- `app/schemas/__init__.py` (MODIFY - add imports)

**Implementation Steps:**
1. Create `app/schemas/ingestion.py` with Pydantic v2 models
2. Define `ProductIngestionSchema` matching Product model fields with validators
3. Define `ReviewIngestionSchema` matching Review model fields with rating range validator
4. Define `PolicyIngestionSchema` matching Policy model fields
5. Add custom validators for price (positive), rating (1-5), URLs, dates
6. Add a `IngestionResult` schema to track success/failure counts

**Code Snippet Example:**
```python
"""Pydantic schemas for data ingestion validation."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl


class ProductIngestionSchema(BaseModel):
    """Validates incoming product data before DB insertion."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price is positive and has at most 2 decimal places."""
        if v <= 0:
            raise ValueError("Price must be positive")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        """Normalize category to title case."""
        return v.strip().title()


class ReviewIngestionSchema(BaseModel):
    """Validates incoming review data before DB insertion."""

    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern=r"^(positive|negative|neutral)$")

    @field_validator("review_text")
    @classmethod
    def clean_review_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if len(v) > 0 else None
        return v


class PolicyIngestionSchema(BaseModel):
    """Validates incoming policy data before DB insertion."""

    category: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    effective_date: date


class IngestionResult(BaseModel):
    """Tracks the outcome of a data ingestion run."""

    total_records: int = 0
    successful: int = 0
    failed: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.successful / self.total_records) * 100
```

**Dependencies:**
- `pydantic` (already in requirements.txt)

**Tests:**
- Unit test file: `tests/test_schemas/test_ingestion.py`
- Test cases to cover:
  - Valid product data passes validation
  - Invalid price (negative/zero) raises error
  - Rating out of range (0, 6) raises error
  - Missing required fields raise errors
  - Category normalization works
  - IngestionResult tracks counts correctly
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] All three schemas created (Product, Review, Policy)
- [ ] Custom validators working (price, rating, category)
- [ ] IngestionResult tracks success/failure
- [ ] Tests pass
- [ ] No linting errors

---

### Task 2: Create Base Data Ingestion Pipeline

**Purpose**: Build the abstract base pipeline class with common functionality: logging, error handling, batch processing, and deduplication hooks.

**Files to Create/Modify:**
- `app/services/ingestion/__init__.py` (CREATE)
- `app/services/ingestion/base.py` (CREATE)

**Implementation Steps:**
1. Create `app/services/ingestion/` package directory
2. Create base `DataIngestionPipeline` abstract class
3. Implement common methods: `run()`, `_process_batch()`, `_log_progress()`
4. Add deduplication hook (abstract method `_get_dedup_key()`)
5. Add error collection and reporting
6. Add configurable batch size
7. Integrate Python `logging` (loguru) for structured pipeline logs

**Code Snippet Example:**
```python
"""Base data ingestion pipeline with common functionality."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.schemas.ingestion import IngestionResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class DataIngestionPipeline(ABC, Generic[T]):
    """Abstract base class for data ingestion pipelines."""

    def __init__(self, db_session: Session, batch_size: int = 100):
        self.db = db_session
        self.batch_size = batch_size
        self.result = IngestionResult()
        self._seen_keys: set[str] = set()

    def run(self, file_path: str | Path) -> IngestionResult:
        """Execute the full ingestion pipeline."""
        file_path = Path(file_path)
        logger.info(f"Starting ingestion from {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        # Read raw data
        df = self._read_file(file_path)
        self.result.total_records = len(df)
        logger.info(f"Read {len(df)} records from {file_path.name}")

        # Process in batches
        for start in range(0, len(df), self.batch_size):
            batch = df.iloc[start : start + self.batch_size]
            self._process_batch(batch)
            logger.info(
                f"Progress: {min(start + self.batch_size, len(df))}/{len(df)} "
                f"(success={self.result.successful}, failed={self.result.failed})"
            )

        self.db.commit()
        self._log_summary()
        return self.result

    def _process_batch(self, batch: pd.DataFrame) -> None:
        """Process a batch of records."""
        for _, row in batch.iterrows():
            try:
                validated = self._validate_row(row)
                dedup_key = self._get_dedup_key(validated)

                if dedup_key in self._seen_keys:
                    self.result.duplicates_skipped += 1
                    continue

                self._seen_keys.add(dedup_key)
                self._insert_record(validated)
                self.result.successful += 1
            except ValidationError as e:
                self.result.failed += 1
                self.result.errors.append(f"Validation error: {e.errors()[0]['msg']}")
            except Exception as e:
                self.result.failed += 1
                self.result.errors.append(f"Insert error: {str(e)}")

    @abstractmethod
    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read and return raw data as a DataFrame."""
        ...

    @abstractmethod
    def _validate_row(self, row: pd.Series) -> T:
        """Validate a single row and return a Pydantic model."""
        ...

    @abstractmethod
    def _get_dedup_key(self, record: T) -> str:
        """Return a unique key for deduplication."""
        ...

    @abstractmethod
    def _insert_record(self, record: T) -> None:
        """Insert a validated record into the database."""
        ...

    def _log_summary(self) -> None:
        """Log the ingestion summary."""
        logger.info(
            f"Ingestion complete: "
            f"total={self.result.total_records}, "
            f"success={self.result.successful}, "
            f"failed={self.result.failed}, "
            f"duplicates={self.result.duplicates_skipped}, "
            f"success_rate={self.result.success_rate:.1f}%"
        )
        if self.result.errors:
            logger.warning(f"Errors encountered: {len(self.result.errors)}")
            for err in self.result.errors[:10]:  # Log first 10 errors
                logger.warning(f"  - {err}")
```

**Dependencies:**
- `pandas`, `pydantic`, `sqlalchemy`, `loguru` (all in requirements.txt)

**Tests:**
- Unit test file: `tests/test_services/test_ingestion_base.py`
- Test cases to cover:
  - Pipeline raises FileNotFoundError for missing files
  - Batch processing iterates correctly
  - Deduplication skips duplicate records
  - Error handling captures validation failures
  - IngestionResult tracks correct counts
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] Base class created with abstract methods
- [ ] Batch processing logic working
- [ ] Deduplication framework in place
- [ ] Logging integrated
- [ ] Error collection working
- [ ] Tests pass
- [ ] No linting errors

---

### Task 3: Create Product Catalog Ingester

**Purpose**: Implement the concrete product CSV ingestion pipeline that reads product catalogs, validates with Pydantic, deduplicates by name+brand, and inserts into the products table.

**Files to Create/Modify:**
- `app/services/ingestion/product_ingester.py` (CREATE)

**Implementation Steps:**
1. Extend `DataIngestionPipeline` with `ProductIngestionSchema`
2. Implement `_read_file()` for CSV with column mapping (handle various CSV formats)
3. Implement `_validate_row()` to convert DataFrame row → `ProductIngestionSchema`
4. Implement `_get_dedup_key()` using lowercase `name + brand` combination
5. Implement `_insert_record()` to create `Product` ORM instance and add to session
6. Add column name normalization (strip whitespace, lowercase)
7. Handle missing/null values gracefully

**Code Snippet Example:**
```python
"""Product catalog data ingestion pipeline."""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.ingestion import ProductIngestionSchema, IngestionResult
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)

# Common column name mappings for various CSV formats
COLUMN_MAPPINGS = {
    "product_name": "name",
    "product_title": "name",
    "title": "name",
    "desc": "description",
    "product_description": "description",
    "actual_price": "price",
    "selling_price": "price",
    "discounted_price": "price",
    "brand_name": "brand",
    "main_category": "category",
    "sub_category": "category",
    "product_category": "category",
    "img_link": "image_url",
    "image": "image_url",
    "product_image": "image_url",
}


class ProductIngester(DataIngestionPipeline[ProductIngestionSchema]):
    """Ingests product catalog data from CSV files."""

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read CSV and normalize column names."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")

        # Normalize column names: strip, lowercase
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        # Apply known column mappings
        rename_map = {
            old: new for old, new in COLUMN_MAPPINGS.items() if old in df.columns
        }
        df = df.rename(columns=rename_map)

        logger.info(f"Columns after normalization: {list(df.columns)}")
        return df

    def _validate_row(self, row: pd.Series) -> ProductIngestionSchema:
        """Validate a product row."""
        # Clean price: remove currency symbols and commas
        price = row.get("price", 0)
        if isinstance(price, str):
            price = price.replace("₹", "").replace("$", "").replace(",", "").strip()
            price = float(price) if price else 0

        return ProductIngestionSchema(
            name=str(row.get("name", "")).strip(),
            description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
            price=float(price),
            brand=str(row.get("brand", "")).strip() if pd.notna(row.get("brand")) else None,
            category=str(row.get("category", "General")).strip(),
            image_url=str(row.get("image_url", "")).strip() if pd.notna(row.get("image_url")) else None,
        )

    def _get_dedup_key(self, record: ProductIngestionSchema) -> str:
        """Deduplicate by lowercase name + brand."""
        brand = (record.brand or "").lower()
        return f"{record.name.lower()}|{brand}"

    def _insert_record(self, record: ProductIngestionSchema) -> None:
        """Insert validated product into the database."""
        product = Product(
            name=record.name,
            description=record.description,
            price=record.price,
            brand=record.brand,
            category=record.category,
            image_url=record.image_url,
        )
        self.db.add(product)
```

**Dependencies:**
- `pandas` for CSV reading
- `Product` model from SCRUM-6
- `ProductIngestionSchema` from Task 1
- `DataIngestionPipeline` from Task 2

**Tests:**
- Unit test file: `tests/test_services/test_product_ingester.py`
- Test cases to cover:
  - Ingest valid CSV with all fields
  - Handle CSV with missing optional columns
  - Column name mapping works (e.g., "product_name" → "name")
  - Price cleaning (currency symbols, commas removed)
  - Deduplication skips duplicate products (same name+brand)
  - Invalid rows are counted as failures
  - Batch processing works correctly
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] CSV reading with column normalization
- [ ] Column mapping for various CSV formats
- [ ] Price cleaning (symbols, commas)
- [ ] Deduplication by name+brand
- [ ] Graceful null handling
- [ ] Tests pass
- [ ] No linting errors

---

### Task 4: Create Review Data Ingester

**Purpose**: Implement the review data ingestion pipeline that reads review datasets, validates ratings and text, deduplicates, and inserts into the reviews table.

**Files to Create/Modify:**
- `app/services/ingestion/review_ingester.py` (CREATE)

**Implementation Steps:**
1. Extend `DataIngestionPipeline` with `ReviewIngestionSchema`
2. Implement `_read_file()` for CSV with review-specific column mapping
3. Implement `_validate_row()` with rating coercion and sentiment inference
4. Implement `_get_dedup_key()` using `product_id + review_text hash`
5. Implement `_insert_record()` to create `Review` ORM instance
6. Add basic sentiment inference: rating >= 4 → positive, <= 2 → negative, else neutral
7. Verify that `product_id` references an existing product

**Code Snippet Example:**
```python
"""Review data ingestion pipeline."""

import hashlib
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.product import Product
from app.schemas.ingestion import ReviewIngestionSchema, IngestionResult
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)

REVIEW_COLUMN_MAPPINGS = {
    "user_rating": "rating",
    "star_rating": "rating",
    "stars": "rating",
    "review_body": "review_text",
    "comment": "review_text",
    "review_content": "review_text",
    "review_description": "review_text",
}


class ReviewIngester(DataIngestionPipeline[ReviewIngestionSchema]):
    """Ingests review data from CSV files."""

    def __init__(self, db_session: Session, batch_size: int = 100):
        super().__init__(db_session, batch_size)
        self._valid_product_ids: set[int] | None = None

    def _get_valid_product_ids(self) -> set[int]:
        """Cache and return all valid product IDs from DB."""
        if self._valid_product_ids is None:
            products = self.db.query(Product.product_id).all()
            self._valid_product_ids = {p.product_id for p in products}
            logger.info(f"Loaded {len(self._valid_product_ids)} valid product IDs")
        return self._valid_product_ids

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read review CSV and normalize columns."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        rename_map = {
            old: new for old, new in REVIEW_COLUMN_MAPPINGS.items() if old in df.columns
        }
        df = df.rename(columns=rename_map)
        return df

    def _validate_row(self, row: pd.Series) -> ReviewIngestionSchema:
        """Validate a review row with sentiment inference."""
        product_id = int(row.get("product_id", 0))

        # Verify product exists
        valid_ids = self._get_valid_product_ids()
        if product_id not in valid_ids:
            raise ValueError(f"Product ID {product_id} does not exist")

        rating = int(float(row.get("rating", 0)))

        # Infer sentiment from rating if not provided
        sentiment = row.get("sentiment")
        if pd.isna(sentiment) or sentiment is None:
            if rating >= 4:
                sentiment = "positive"
            elif rating <= 2:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        review_text = row.get("review_text")
        if pd.notna(review_text):
            review_text = str(review_text).strip()
        else:
            review_text = None

        return ReviewIngestionSchema(
            product_id=product_id,
            rating=rating,
            review_text=review_text,
            sentiment=str(sentiment).lower(),
        )

    def _get_dedup_key(self, record: ReviewIngestionSchema) -> str:
        """Deduplicate by product_id + review_text hash."""
        text = (record.review_text or "").lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{record.product_id}|{text_hash}"

    def _insert_record(self, record: ReviewIngestionSchema) -> None:
        """Insert validated review into the database."""
        review = Review(
            product_id=record.product_id,
            rating=record.rating,
            review_text=record.review_text,
            sentiment=record.sentiment,
        )
        self.db.add(review)
```

**Dependencies:**
- `Review` and `Product` models from SCRUM-6
- `ReviewIngestionSchema` from Task 1
- `DataIngestionPipeline` from Task 2

**Tests:**
- Unit test file: `tests/test_services/test_review_ingester.py`
- Test cases to cover:
  - Ingest valid review CSV
  - Sentiment auto-inferred from rating (4-5=positive, 1-2=negative, 3=neutral)
  - Invalid product_id raises error
  - Rating out of range rejected
  - Deduplication by product_id + text hash
  - Handles missing review_text gracefully
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] CSV reading with review column mapping
- [ ] Sentiment inference from rating
- [ ] Product ID validation (FK check)
- [ ] Deduplication by product_id + text hash
- [ ] Graceful null handling
- [ ] Tests pass
- [ ] No linting errors

---

### Task 5: Create Policy Data Ingester

**Purpose**: Implement the policy/FAQ data ingestion pipeline that reads store policy documents from CSV and inserts into the policies table.

**Files to Create/Modify:**
- `app/services/ingestion/policy_ingester.py` (CREATE)

**Implementation Steps:**
1. Extend `DataIngestionPipeline` with `PolicyIngestionSchema`
2. Implement `_read_file()` for CSV with policy column mapping
3. Implement `_validate_row()` with date parsing
4. Implement `_get_dedup_key()` using `category + question hash`
5. Implement `_insert_record()` to create `Policy` ORM instance

**Code Snippet Example:**
```python
"""Policy/FAQ data ingestion pipeline."""

import hashlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.schemas.ingestion import PolicyIngestionSchema
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)


class PolicyIngester(DataIngestionPipeline[PolicyIngestionSchema]):
    """Ingests store policy/FAQ data from CSV files."""

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read policy CSV."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        return df

    def _validate_row(self, row: pd.Series) -> PolicyIngestionSchema:
        """Validate a policy row."""
        effective_date = row.get("effective_date", date.today().isoformat())
        if isinstance(effective_date, str):
            effective_date = date.fromisoformat(effective_date.strip())

        return PolicyIngestionSchema(
            category=str(row.get("category", "")).strip(),
            question=str(row.get("question", "")).strip(),
            answer=str(row.get("answer", "")).strip(),
            effective_date=effective_date,
        )

    def _get_dedup_key(self, record: PolicyIngestionSchema) -> str:
        """Deduplicate by category + question hash."""
        q_hash = hashlib.md5(record.question.lower().encode()).hexdigest()[:12]
        return f"{record.category.lower()}|{q_hash}"

    def _insert_record(self, record: PolicyIngestionSchema) -> None:
        """Insert validated policy into the database."""
        policy = Policy(
            category=record.category,
            question=record.question,
            answer=record.answer,
            effective_date=record.effective_date,
        )
        self.db.add(policy)
```

**Dependencies:**
- `Policy` model from SCRUM-6
- `PolicyIngestionSchema` from Task 1
- `DataIngestionPipeline` from Task 2

**Tests:**
- Unit test file: `tests/test_services/test_policy_ingester.py`
- Test cases to cover:
  - Ingest valid policy CSV
  - Date parsing from various formats
  - Deduplication by category+question
  - Missing fields raise errors
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] CSV reading for policy data
- [ ] Date parsing working
- [ ] Deduplication logic
- [ ] Tests pass
- [ ] No linting errors

---

### Task 6: Create Data Quality Monitor

**Purpose**: Build a data quality monitoring module that validates ingestion results, generates quality reports, and logs alerts when data quality drops below thresholds.

**Files to Create/Modify:**
- `app/services/ingestion/quality_monitor.py` (CREATE)

**Implementation Steps:**
1. Create `DataQualityMonitor` class
2. Accept `IngestionResult` and validate against configurable thresholds
3. Check: minimum success rate (default 80%), max error count, null field rates
4. Generate quality report as dict/JSON
5. Log warnings when thresholds are breached
6. Save quality reports to `data/processed/quality_reports/`

**Code Snippet Example:**
```python
"""Data quality monitoring for ingestion pipelines."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.schemas.ingestion import IngestionResult

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """Monitors and reports on data ingestion quality."""

    def __init__(
        self,
        min_success_rate: float = 80.0,
        max_error_count: int = 100,
        report_dir: str = "data/processed/quality_reports",
    ):
        self.min_success_rate = min_success_rate
        self.max_error_count = max_error_count
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def check(self, result: IngestionResult, source_name: str) -> dict[str, Any]:
        """Run quality checks and return a report."""
        alerts: list[str] = []

        if result.success_rate < self.min_success_rate:
            alerts.append(
                f"ALERT: Success rate {result.success_rate:.1f}% "
                f"below threshold {self.min_success_rate}%"
            )

        if result.failed > self.max_error_count:
            alerts.append(
                f"ALERT: Error count {result.failed} "
                f"exceeds max threshold {self.max_error_count}"
            )

        report = {
            "source": source_name,
            "timestamp": datetime.utcnow().isoformat(),
            "total_records": result.total_records,
            "successful": result.successful,
            "failed": result.failed,
            "duplicates_skipped": result.duplicates_skipped,
            "success_rate": round(result.success_rate, 2),
            "alerts": alerts,
            "status": "PASS" if len(alerts) == 0 else "FAIL",
            "sample_errors": result.errors[:5],
        }

        # Log alerts
        for alert in alerts:
            logger.warning(alert)

        if not alerts:
            logger.info(f"Data quality check PASSED for {source_name}")

        # Save report
        self._save_report(report, source_name)

        return report

    def _save_report(self, report: dict, source_name: str) -> Path:
        """Save quality report to disk."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{timestamp}.json"
        filepath = self.report_dir / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Quality report saved: {filepath}")
        return filepath
```

**Dependencies:**
- `IngestionResult` from Task 1

**Tests:**
- Unit test file: `tests/test_services/test_quality_monitor.py`
- Test cases to cover:
  - PASS when success rate above threshold
  - FAIL when success rate below threshold
  - FAIL when error count exceeds max
  - Report saved to correct directory
  - Alerts logged correctly
- Expected outcome: All tests pass

**Validation Checklist:**
- [ ] Quality checks against configurable thresholds
- [ ] Report generation as JSON
- [ ] Reports saved to disk
- [ ] Alerts logged for failures
- [ ] Tests pass
- [ ] No linting errors

---

### Task 7: Create Ingestion CLI Script

**Purpose**: Build the main command-line script that orchestrates the full ingestion pipeline — reads CSVs from `data/raw/`, runs the appropriate ingester, and outputs quality reports.

**Files to Create/Modify:**
- `scripts/ingest_data.py` (CREATE or REPLACE)
- `app/services/ingestion/__init__.py` (MODIFY - export all ingesters)

**Implementation Steps:**
1. Create CLI script with argparse for specifying data type and file path
2. Support `--type` flag: `products`, `reviews`, `policies`, `all`
3. Support `--file` flag for specific file, or auto-detect from `data/raw/`
4. Support `--batch-size` flag (default 100)
5. Wire up DB session, ingester, and quality monitor
6. Print summary report to stdout
7. Update `app/services/ingestion/__init__.py` to export all ingesters

**Code Snippet Example:**
```python
#!/usr/bin/env python3
"""Data ingestion CLI for SmartShop AI.

Usage:
    python scripts/ingest_data.py --type products --file data/raw/products.csv
    python scripts/ingest_data.py --type reviews --file data/raw/reviews.csv
    python scripts/ingest_data.py --type policies --file data/raw/policies.csv
    python scripts/ingest_data.py --type all  # Ingest all data from data/raw/
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, get_session_factory, create_tables
from app.services.ingestion.product_ingester import ProductIngester
from app.services.ingestion.review_ingester import ReviewIngester
from app.services.ingestion.policy_ingester import PolicyIngester
from app.services.ingestion.quality_monitor import DataQualityMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/raw")

INGESTERS = {
    "products": (ProductIngester, "products*.csv"),
    "reviews": (ReviewIngester, "reviews*.csv"),
    "policies": (PolicyIngester, "policies*.csv"),
}


def run_ingestion(data_type: str, file_path: str | None, batch_size: int) -> None:
    """Run ingestion for a specific data type."""
    engine = get_engine()
    create_tables(engine)
    session_factory = get_session_factory(engine)
    session = session_factory()
    monitor = DataQualityMonitor()

    try:
        ingester_class, pattern = INGESTERS[data_type]

        if file_path:
            files = [Path(file_path)]
        else:
            files = sorted(DATA_DIR.glob(pattern))

        if not files:
            logger.warning(f"No {data_type} files found matching {pattern} in {DATA_DIR}")
            return

        for f in files:
            logger.info(f"=== Ingesting {data_type} from {f.name} ===")
            ingester = ingester_class(db_session=session, batch_size=batch_size)
            result = ingester.run(f)
            report = monitor.check(result, source_name=f"{data_type}_{f.stem}")

            print(f"\n{'='*50}")
            print(f"Ingestion Report: {f.name}")
            print(f"{'='*50}")
            print(f"  Total Records : {result.total_records}")
            print(f"  Successful    : {result.successful}")
            print(f"  Failed        : {result.failed}")
            print(f"  Duplicates    : {result.duplicates_skipped}")
            print(f"  Success Rate  : {result.success_rate:.1f}%")
            print(f"  Quality Status: {report['status']}")
            if report['alerts']:
                for alert in report['alerts']:
                    print(f"  ⚠️  {alert}")
            print(f"{'='*50}\n")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="SmartShop AI Data Ingestion")
    parser.add_argument(
        "--type",
        choices=["products", "reviews", "policies", "all"],
        required=True,
        help="Type of data to ingest",
    )
    parser.add_argument("--file", help="Specific file path (optional)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")

    args = parser.parse_args()

    if args.type == "all":
        for dtype in ["products", "reviews", "policies"]:
            run_ingestion(dtype, None, args.batch_size)
    else:
        run_ingestion(args.type, args.file, args.batch_size)


if __name__ == "__main__":
    main()
```

**Dependencies:**
- All ingester classes from Tasks 3-5
- Quality monitor from Task 6
- Database module from SCRUM-6

**Tests:**
- Manual test: `python scripts/ingest_data.py --type products --file data/raw/sample_products.csv`
- Expected outcome: Products ingested with quality report printed

**Validation Checklist:**
- [ ] CLI script accepts --type and --file arguments
- [ ] All three data types supported
- [ ] --type all ingests everything
- [ ] Quality reports generated
- [ ] Summary printed to stdout
- [ ] Script runs without errors

---

### Task 8: Create Sample Data Files and Write Comprehensive Tests

**Purpose**: Create sample CSV files for testing and write comprehensive unit + integration tests for the entire ingestion pipeline.

**Files to Create/Modify:**
- `data/raw/sample_products.csv` (CREATE)
- `data/raw/sample_reviews.csv` (CREATE)
- `data/raw/sample_policies.csv` (CREATE)
- `tests/test_schemas/test_ingestion.py` (CREATE)
- `tests/test_schemas/__init__.py` (CREATE)
- `tests/test_services/test_product_ingester.py` (CREATE)
- `tests/test_services/test_review_ingester.py` (CREATE)
- `tests/test_services/test_policy_ingester.py` (CREATE)
- `tests/test_services/test_quality_monitor.py` (CREATE)
- `tests/test_services/__init__.py` (CREATE)
- `tests/conftest.py` (MODIFY - add ingestion fixtures)

**Implementation Steps:**
1. Create sample CSV files with realistic data (10-20 rows each) including edge cases
2. Create test fixtures: temp CSV files, in-memory DB session, sample data
3. Write schema validation tests (valid/invalid data)
4. Write ingester tests (happy path, error handling, deduplication)
5. Write quality monitor tests (PASS/FAIL scenarios)
6. Write integration test: full pipeline from CSV → DB → quality report
7. Ensure >90% test coverage for all new modules

**Sample CSV Example (data/raw/sample_products.csv):**
```csv
name,description,price,brand,category,image_url
Wireless Bluetooth Headphones,Premium noise-cancelling over-ear headphones,79.99,SoundMax,Electronics,https://example.com/headphones.jpg
Smart Fitness Watch,Track heart rate and steps with GPS,149.99,FitTech,Electronics,https://example.com/watch.jpg
Organic Cotton T-Shirt,100% organic cotton casual tee,24.99,EcoWear,Fashion,https://example.com/tshirt.jpg
Stainless Steel Water Bottle,Insulated 750ml bottle,19.99,HydroLife,Home & Kitchen,https://example.com/bottle.jpg
Python Programming Book,Comprehensive guide to Python 3.11+,39.99,TechBooks,Books,https://example.com/pybook.jpg
```

**Dependencies:**
- `pytest`, `pytest-cov` (in requirements.txt)
- All ingestion modules from Tasks 1-7
- `tmp_path` pytest fixture for temp files

**Tests:**
- Run: `pytest tests/test_schemas/ tests/test_services/ -v --cov=app/schemas --cov=app/services/ingestion`
- Expected outcome: All tests pass, coverage >90%

**Validation Checklist:**
- [ ] Sample CSVs created with realistic data
- [ ] Schema validation tests complete
- [ ] Product ingester tests pass
- [ ] Review ingester tests pass
- [ ] Policy ingester tests pass
- [ ] Quality monitor tests pass
- [ ] Integration test (full pipeline) passes
- [ ] Test coverage >90%
- [ ] No linting errors

---

## 🧪 Integration Testing

**Integration Test Scenarios:**

1. **Scenario 1: Full Product Ingestion Pipeline**
   - Setup: Clean DB, sample_products.csv in data/raw/
   - Steps:
     1. Run `python scripts/ingest_data.py --type products --file data/raw/sample_products.csv`
     2. Query DB for inserted products
     3. Check quality report
   - Expected: All valid products inserted, quality report PASS

2. **Scenario 2: Review Ingestion with FK Validation**
   - Setup: DB with products loaded, sample_reviews.csv
   - Steps:
     1. Ingest products first
     2. Ingest reviews referencing valid product IDs
     3. Verify reviews linked to correct products
   - Expected: Reviews with valid product_ids inserted, invalid ones rejected

3. **Scenario 3: Deduplication Across Multiple Runs**
   - Setup: Run product ingestion twice with same CSV
   - Steps:
     1. First run: all products inserted
     2. Second run: all products skipped as duplicates
   - Expected: No duplicate records in DB, dedup count matches

4. **Scenario 4: Data Quality Alert**
   - Setup: CSV with >50% invalid records
   - Steps:
     1. Run ingestion
     2. Check quality monitor report
   - Expected: Quality status = FAIL, alert for low success rate

**Manual Testing Steps:**
1. Place sample CSVs in `data/raw/`
2. Run `python scripts/ingest_data.py --type all`
3. Verify products, reviews, policies in DB
4. Check `data/processed/quality_reports/` for reports
5. Verify no duplicate records

---

## 📝 Documentation Updates

**Files to Update:**
- [ ] `README.md` - Add data ingestion section with usage instructions
- [ ] `docs/ARCHITECTURE.md` - Add data pipeline architecture section
- [ ] `QUICKSTART.md` - Add data loading steps

**Documentation Content:**
- How to prepare CSV files
- Column mapping reference
- CLI usage examples
- Quality monitoring thresholds
- Troubleshooting ingestion errors

---

## ✅ Completion Checklist

### Code Quality
- [ ] All ingestion files created (schemas, base, 3 ingesters, monitor, CLI)
- [ ] Code follows project style guide (black, ruff)
- [ ] All functions/classes have docstrings
- [ ] Type hints added throughout
- [ ] No unused imports or variables
- [ ] Code linted with ruff (no errors)
- [ ] Code formatted with black

### Testing
- [ ] Schema validation tests passing
- [ ] Product ingester tests passing
- [ ] Review ingester tests passing
- [ ] Policy ingester tests passing
- [ ] Quality monitor tests passing
- [ ] Integration test passing (full pipeline)
- [ ] Test coverage >90% for new modules

### Documentation
- [ ] Code comments added for complex logic
- [ ] README updated with data ingestion section
- [ ] Architecture docs updated
- [ ] Sample CSV files documented

### Acceptance Criteria
- [ ] CSV import functionality for product catalogs ✅
- [ ] Review data ingestion from CSV datasets ✅
- [ ] Data validation using Pydantic models ✅
- [ ] Automated deduplication logic ✅
- [ ] Error handling and logging ✅
- [ ] Batch processing capability ✅
- [ ] Data quality monitoring alerts ✅

### Deployment Readiness
- [ ] All new dependencies already in requirements.txt
- [ ] Sample data files included
- [ ] CLI script executable
- [ ] Data directories created (data/raw, data/processed/quality_reports)

---

## 🔗 Jira Status Update

**Current Status**: In Progress
**Target Status**: Done

**Completion Comment Template:**
```
✅ SCRUM-7 completed successfully!

**Implemented:**
- Complete data ingestion pipeline with 3 specialized ingesters (Product, Review, Policy)
- Pydantic v2 validation schemas with custom validators
- Abstract base pipeline with batch processing and deduplication
- Data quality monitoring with configurable thresholds and alerts
- CLI script for command-line ingestion (supports --type and --file)
- Sample CSV datasets for testing

**Files Created:**
- app/schemas/ingestion.py (Pydantic validation schemas)
- app/services/ingestion/base.py (Abstract base pipeline)
- app/services/ingestion/product_ingester.py (Product CSV ingester)
- app/services/ingestion/review_ingester.py (Review CSV ingester)
- app/services/ingestion/policy_ingester.py (Policy CSV ingester)
- app/services/ingestion/quality_monitor.py (Data quality monitoring)
- scripts/ingest_data.py (CLI ingestion script)
- data/raw/sample_products.csv, sample_reviews.csv, sample_policies.csv
- Complete test suite in tests/test_schemas/ and tests/test_services/

**Architecture:**
- Base pipeline pattern (abstract class with batch processing)
- Pydantic validation layer before DB insertion
- Deduplication by content hash
- Quality monitoring with configurable thresholds
- CLI interface for easy execution

**Testing:**
- Unit tests: [count] tests, all passing ✅
- Integration tests: 4 scenarios, all passing ✅
- Coverage: >90%

**Next Steps:**
- Ready for SCRUM-8 (Load initial product catalog dataset)
- Pipeline ready to ingest real Kaggle datasets
```

---

## 🚨 Known Issues / Blockers

- None anticipated. All dependencies (pandas, pydantic, sqlalchemy) are already in requirements.txt
- Database schema from SCRUM-6 is complete and ready

---

## 📊 Time Tracking

- **Estimated Time**: 3-4 hours
- **Actual Time**: _[To be filled during execution]_
- **Variance**: _[To be calculated]_

---

## 💡 Notes & Learnings

- **Design Decision**: Used abstract base class pattern for ingesters to maximize code reuse
- **Design Decision**: Deduplication uses in-memory set (fine for datasets under 1M records)
- **Design Decision**: Sentiment inferred from rating when not explicitly provided
- **Performance**: Batch processing (default 100 rows) balances memory usage and DB round-trips
- **Extensibility**: New data sources only need a new ingester subclass

**Technical Debt Identified:**
- For very large datasets (>1M rows), consider chunked CSV reading with `pd.read_csv(chunksize=)`
- Deduplication could use DB-level UPSERT for better scalability
- Consider async ingestion for parallel processing in future
- Sentiment analysis could use NLP model instead of simple rating-based inference (Phase 2)

**Optimization Opportunities:**
- Use `COPY` for bulk PostgreSQL inserts instead of row-by-row ORM inserts
- Add progress bars (tqdm) for CLI feedback
- Implement retry logic for transient DB errors
