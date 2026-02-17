"""Tests for base data ingestion pipeline."""

import pytest
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from app.schemas.ingestion import IngestionResult
from app.services.ingestion.base import DataIngestionPipeline


@dataclass
class FakeRecord:
    record_name: str


class ConcreteIngester(DataIngestionPipeline):
    """Concrete implementation for testing the base class."""

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        return pd.read_csv(file_path)

    def _validate_row(self, row: pd.Series):
        if row.get("name", "") == "INVALID":
            raise ValueError("Invalid record")
        return FakeRecord(record_name=str(row.get("name", "")))

    def _get_dedup_key(self, record) -> str:
        return record.record_name

    def _insert_record(self, record) -> None:
        pass


class TestDataIngestionPipeline:
    """Tests for the base pipeline."""

    def test_file_not_found_raises_error(self, db_session):
        ingester = ConcreteIngester(db_session=db_session)
        with pytest.raises(FileNotFoundError):
            ingester.run("/nonexistent/file.csv")

    def test_successful_ingestion(self, db_session, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nBob,2\nCharlie,3\n")

        ingester = ConcreteIngester(db_session=db_session, batch_size=2)
        result = ingester.run(csv_file)

        assert result.total_records == 3
        assert result.successful == 3
        assert result.failed == 0

    def test_deduplication(self, db_session, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nAlice,2\nBob,3\n")

        ingester = ConcreteIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        assert result.duplicates_skipped == 1

    def test_error_handling(self, db_session, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nINVALID,2\nBob,3\n")

        ingester = ConcreteIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_batch_processing(self, db_session, tmp_path):
        csv_file = tmp_path / "test.csv"
        rows = "name,value\n" + "\n".join(
            f"Item{i},{i}" for i in range(10)
        )
        csv_file.write_text(rows)

        ingester = ConcreteIngester(db_session=db_session, batch_size=3)
        result = ingester.run(csv_file)

        assert result.total_records == 10
        assert result.successful == 10

    def test_result_tracking(self, db_session, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nAlice,2\nINVALID,3\nBob,4\n")

        ingester = ConcreteIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 4
        assert result.successful == 2
        assert result.failed == 1
        assert result.duplicates_skipped == 1
