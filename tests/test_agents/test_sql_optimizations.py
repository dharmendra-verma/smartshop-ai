"""Tests for SCRUM-67 SQL optimizations: review tools, policy fallback, ingestion batch handling."""

import pytest
from unittest.mock import MagicMock, patch
from app.agents.dependencies import AgentDependencies
from app.core.config import get_settings


# ---- Policy DB Fallback Tests ----


class TestPolicyDbFallback:
    """Tests for the optimized _db_fallback that uses SQL WHERE instead of Python filtering."""

    def test_fallback_uses_sql_filter(self):
        from app.agents.policy.tools import _db_fallback

        db = MagicMock()
        mock_policy = MagicMock()
        mock_policy.policy_type = "return_policy"
        mock_policy.description = "30-day return window"
        mock_policy.conditions = "Original receipt required"
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            mock_policy
        ]

        result = _db_fallback(db, "return receipt")
        assert "return_policy" in result
        assert "30-day return window" in result
        # Verify filter was called (SQL WHERE) instead of loading all
        db.query.return_value.filter.assert_called_once()

    def test_fallback_empty_query(self):
        from app.agents.policy.tools import _db_fallback

        db = MagicMock()
        result = _db_fallback(db, "")
        assert result == "No matching policies found."
        # Should not query DB at all for empty query
        db.query.assert_not_called()

    def test_fallback_no_results(self):
        from app.agents.policy.tools import _db_fallback

        db = MagicMock()
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = (
            []
        )

        result = _db_fallback(db, "nonexistent policy")
        assert result == "No matching policies found."

    def test_fallback_multiple_results(self):
        from app.agents.policy.tools import _db_fallback

        db = MagicMock()
        p1 = MagicMock()
        p1.policy_type = "shipping"
        p1.description = "Free shipping over $50"
        p1.conditions = "Continental US only"
        p2 = MagicMock()
        p2.policy_type = "returns"
        p2.description = "30-day returns"
        p2.conditions = "Unused items only"
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            p1,
            p2,
        ]

        result = _db_fallback(db, "shipping returns")
        assert "shipping" in result
        assert "returns" in result

    def test_fallback_limits_to_3_results(self):
        from app.agents.policy.tools import _db_fallback

        db = MagicMock()
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = (
            []
        )

        _db_fallback(db, "return")
        # Verify .limit(3) is called
        db.query.return_value.filter.return_value.limit.assert_called_once_with(3)


# ---- Ingestion Batch Error Handling Tests ----


class TestIngestionBatchErrorHandling:
    """Tests for per-batch error handling with rollback in the ingestion pipeline."""

    def test_batch_failure_rolls_back_and_continues(self, db_session, tmp_path):
        from app.services.ingestion.base import DataIngestionPipeline
        from dataclasses import dataclass

        import pandas as pd
        from pathlib import Path

        @dataclass
        class FakeRecord:
            record_name: str

        class FailingBatchIngester(DataIngestionPipeline):
            batch_count = 0

            def _read_file(self, file_path: Path) -> pd.DataFrame:
                return pd.read_csv(file_path)

            def _validate_row(self, row: pd.Series):
                return FakeRecord(record_name=str(row.get("name", "")))

            def _get_dedup_key(self, record) -> str:
                return record.record_name

            def _insert_record(self, record) -> None:
                # Track which batch we're in
                pass

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nBob,2\nCharlie,3\nDave,4\n")

        ingester = FailingBatchIngester(db_session=db_session, batch_size=2)

        # Make commit fail on first call (first batch), succeed on second (second batch)
        original_commit = db_session.commit
        call_count = 0

        def commit_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("DB connection lost")
            return original_commit()

        db_session.commit = commit_side_effect
        result = ingester.run(csv_file)

        # First batch (2 records) failed, second batch (2 records) succeeded
        assert result.failed == 2  # batch-level failure for 2 records
        assert result.successful == 2
        assert len(result.errors) >= 1
        assert "Batch error" in result.errors[0]

    def test_successful_batches_commit_per_batch(self, db_session, tmp_path):
        from app.services.ingestion.base import DataIngestionPipeline
        from dataclasses import dataclass

        import pandas as pd
        from pathlib import Path

        @dataclass
        class FakeRecord:
            record_name: str

        class SimpleIngester(DataIngestionPipeline):
            def _read_file(self, file_path: Path) -> pd.DataFrame:
                return pd.read_csv(file_path)

            def _validate_row(self, row: pd.Series):
                return FakeRecord(record_name=str(row.get("name", "")))

            def _get_dedup_key(self, record) -> str:
                return record.record_name

            def _insert_record(self, record) -> None:
                pass

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\nBob,2\nCharlie,3\n")

        commit_count = 0
        original_commit = db_session.commit

        def counting_commit():
            nonlocal commit_count
            commit_count += 1
            return original_commit()

        db_session.commit = counting_commit
        ingester = SimpleIngester(db_session=db_session, batch_size=2)
        result = ingester.run(csv_file)

        assert result.successful == 3
        # 2 batches = 2 commits (batch of 2 + batch of 1)
        assert commit_count == 2

    def test_batch_rollback_called_on_failure(self, tmp_path):
        """Verify db.rollback() is called when a batch fails."""
        from app.services.ingestion.base import DataIngestionPipeline
        from dataclasses import dataclass

        import pandas as pd
        from pathlib import Path

        @dataclass
        class FakeRecord:
            record_name: str

        class SimpleIngester(DataIngestionPipeline):
            def _read_file(self, file_path: Path) -> pd.DataFrame:
                return pd.read_csv(file_path)

            def _validate_row(self, row: pd.Series):
                return FakeRecord(record_name=str(row.get("name", "")))

            def _get_dedup_key(self, record) -> str:
                return record.record_name

            def _insert_record(self, record) -> None:
                pass

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\nAlice,1\n")

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("commit failed")

        ingester = SimpleIngester(db_session=mock_db, batch_size=10)
        result = ingester.run(csv_file)

        mock_db.rollback.assert_called_once()
        assert result.failed >= 1
