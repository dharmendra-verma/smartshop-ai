"""Tests for policy data ingester."""

import pytest
from datetime import date

from app.models.policy import Policy
from app.services.ingestion.policy_ingester import PolicyIngester


class TestPolicyIngester:
    """Tests for PolicyIngester."""

    def test_ingest_valid_csv(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "category,question,answer,effective_date\n"
            "shipping,How long?,3-5 days,2026-01-01\n"
            "returns,Can I return?,Yes within 30 days,2026-01-01\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 2
        assert result.successful == 2

        policies = db_session.query(Policy).all()
        assert len(policies) == 2

    def test_date_parsing(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "category,question,answer,effective_date\n"
            "shipping,When?,Soon,2026-06-15\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        policy = db_session.query(Policy).first()
        assert policy.effective_date == date(2026, 6, 15)

    def test_deduplication_by_category_and_question(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "category,question,answer,effective_date\n"
            "shipping,How long?,3-5 days,2026-01-01\n"
            "shipping,How long?,Updated: 2-4 days,2026-02-01\n"
            "returns,How long?,30 days,2026-01-01\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        assert result.duplicates_skipped == 1

    def test_missing_fields_rejected(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "category,question,answer,effective_date\n"
            "shipping,Valid question,Some answer,not-a-date\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.failed == 1
        assert result.successful == 0
