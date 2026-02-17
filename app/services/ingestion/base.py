"""Base data ingestion pipeline with common functionality."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

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

        df = self._read_file(file_path)
        self.result.total_records = len(df)
        logger.info(f"Read {len(df)} records from {file_path.name}")

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
            for err in self.result.errors[:10]:
                logger.warning(f"  - {err}")
