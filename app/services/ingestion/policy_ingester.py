"""Policy/FAQ data ingestion pipeline."""

import hashlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd

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
