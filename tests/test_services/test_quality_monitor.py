"""Tests for data quality monitor."""

import json
import pytest

from app.schemas.ingestion import IngestionResult
from app.services.ingestion.quality_monitor import DataQualityMonitor


class TestDataQualityMonitor:
    """Tests for DataQualityMonitor."""

    def test_pass_when_above_threshold(self, tmp_path):
        monitor = DataQualityMonitor(report_dir=str(tmp_path))
        result = IngestionResult(total_records=100, successful=95, failed=5)

        report = monitor.check(result, "test_source")

        assert report["status"] == "PASS"
        assert report["alerts"] == []
        assert report["success_rate"] == 95.0

    def test_fail_when_below_success_rate(self, tmp_path):
        monitor = DataQualityMonitor(min_success_rate=80.0, report_dir=str(tmp_path))
        result = IngestionResult(total_records=100, successful=50, failed=50)

        report = monitor.check(result, "test_source")

        assert report["status"] == "FAIL"
        assert len(report["alerts"]) == 1
        assert "Success rate" in report["alerts"][0]

    def test_fail_when_error_count_exceeds_max(self, tmp_path):
        monitor = DataQualityMonitor(max_error_count=10, report_dir=str(tmp_path))
        result = IngestionResult(total_records=100, successful=80, failed=20)

        report = monitor.check(result, "test_source")

        assert report["status"] == "FAIL"
        assert any("Error count" in a for a in report["alerts"])

    def test_report_saved_to_disk(self, tmp_path):
        monitor = DataQualityMonitor(report_dir=str(tmp_path))
        result = IngestionResult(total_records=10, successful=10)

        monitor.check(result, "test_source")

        report_files = list(tmp_path.glob("*.json"))
        assert len(report_files) == 1

        with open(report_files[0]) as f:
            saved_report = json.load(f)
        assert saved_report["source"] == "test_source"
        assert saved_report["status"] == "PASS"

    def test_sample_errors_included(self, tmp_path):
        monitor = DataQualityMonitor(report_dir=str(tmp_path))
        errors = [f"Error {i}" for i in range(10)]
        result = IngestionResult(
            total_records=100, successful=90, failed=10, errors=errors
        )

        report = monitor.check(result, "test_source")

        assert len(report["sample_errors"]) == 5  # max 5 sample errors

    def test_multiple_alerts(self, tmp_path):
        monitor = DataQualityMonitor(
            min_success_rate=90.0, max_error_count=5, report_dir=str(tmp_path)
        )
        result = IngestionResult(total_records=100, successful=50, failed=50)

        report = monitor.check(result, "test_source")

        assert report["status"] == "FAIL"
        assert len(report["alerts"]) == 2
