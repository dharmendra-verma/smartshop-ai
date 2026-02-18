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
    "policies": (PolicyIngester, "*policies*.csv"),
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
            if report["alerts"]:
                for alert in report["alerts"]:
                    print(f"  WARNING: {alert}")
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
