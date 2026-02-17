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

        for alert in alerts:
            logger.warning(alert)

        if not alerts:
            logger.info(f"Data quality check PASSED for {source_name}")

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
