"""Tests for policy data ingester."""

import pytest

from app.models.policy import Policy
from app.services.ingestion.policy_ingester import PolicyIngester


class TestPolicyIngester:
    """Tests for PolicyIngester."""

    def test_ingest_valid_csv(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            "shipping,Standard Shipping Policy,Order subtotal must be at least $50|Eligible for contiguous U.S. only,5\n"
            "returns,Return Policy,Must be unused|Original packaging required,30\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 2
        assert result.successful == 2

        policies = db_session.query(Policy).all()
        assert len(policies) == 2

    def test_timeframe_parsing(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            "warranty,Extended Warranty,Covers manufacturing defects,365\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        policy = db_session.query(Policy).first()
        assert policy.timeframe == 365

    def test_deduplication_by_type_and_description(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            "shipping,Standard Shipping,3-5 business days,5\n"
            "shipping,Standard Shipping,Updated: 2-4 business days,3\n"
            "returns,Return Policy,30 day returns,30\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        assert result.duplicates_skipped == 1

    def test_missing_fields_rejected(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            ",,, \n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.failed == 1
        assert result.successful == 0
