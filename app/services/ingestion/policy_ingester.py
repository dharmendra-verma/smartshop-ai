"""Policy data ingestion pipeline."""

import hashlib
import logging
from pathlib import Path

import pandas as pd

from app.models.policy import Policy
from app.schemas.ingestion import PolicyIngestionSchema
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)


class PolicyIngester(DataIngestionPipeline[PolicyIngestionSchema]):
    """Ingests store policy data from CSV files."""

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read policy CSV."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        return df

    def _validate_row(self, row: pd.Series) -> PolicyIngestionSchema:
        """Validate a policy row."""
        timeframe = row.get("timeframe", 0)
        timeframe = int(timeframe) if pd.notna(timeframe) else 0

        return PolicyIngestionSchema(
            policy_type=str(row.get("policy_type", "")).strip(),
            description=str(row.get("description", "")).strip(),
            conditions=str(row.get("conditions", "")).strip(),
            timeframe=timeframe,
        )

    def _get_dedup_key(self, record: PolicyIngestionSchema) -> str:
        """Deduplicate by policy_type + description hash."""
        desc_hash = hashlib.md5(record.description.lower().encode()).hexdigest()[:12]
        return f"{record.policy_type.lower()}|{desc_hash}"

    def _insert_record(self, record: PolicyIngestionSchema) -> None:
        """Insert validated policy into the database."""
        policy = Policy(
            policy_type=record.policy_type,
            description=record.description,
            conditions=record.conditions,
            timeframe=record.timeframe,
        )
        self.db.add(policy)
