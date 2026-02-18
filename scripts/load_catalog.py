#!/usr/bin/env python3
"""Load product catalog, reviews, and policies into the database.

Usage:
    python scripts/load_catalog.py              # Load all data
    python scripts/load_catalog.py --clean      # Drop tables first, then load
    python scripts/load_catalog.py --type products  # Load only products
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func

from app.core.database import get_engine, get_session_factory, create_tables, drop_tables
from app.services.ingestion.product_ingester import ProductIngester
from app.services.ingestion.review_ingester import ReviewIngester
from app.services.ingestion.policy_ingester import PolicyIngester
from app.services.ingestion.quality_monitor import DataQualityMonitor
from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/raw")

DATA_FILES = {
    "products": ("products.csv", ProductIngester),
    "reviews": ("reviews.csv", ReviewIngester),
    "policies": ("store_policies.csv", PolicyIngester),
}


def print_summary(session):
    """Print a summary of loaded data."""
    product_count = session.query(func.count(Product.id)).scalar()
    review_count = session.query(func.count(Review.review_id)).scalar()
    policy_count = session.query(func.count(Policy.policy_id)).scalar()

    print(f"\n{'='*60}")
    print(f"  DATABASE LOAD SUMMARY")
    print(f"{'='*60}")
    print(f"  Products : {product_count:,}")
    print(f"  Reviews  : {review_count:,}")
    print(f"  Policies : {policy_count:,}")

    if product_count > 0:
        # Category breakdown
        categories = (
            session.query(Product.category, func.count())
            .group_by(Product.category)
            .order_by(func.count().desc())
            .all()
        )
        print(f"\n  Categories ({len(categories)}):")
        for cat, count in categories:
            print(f"    {cat:<20s} {count:>5,}")

        # Price stats
        price_stats = session.query(
            func.min(Product.price),
            func.max(Product.price),
            func.avg(Product.price),
        ).first()
        print(f"\n  Price Range: ${float(price_stats[0]):.2f} - ${float(price_stats[1]):.2f}")
        print(f"  Avg Price  : ${float(price_stats[2]):.2f}")

        # Unique brands
        brand_count = session.query(func.count(func.distinct(Product.brand))).scalar()
        print(f"  Brands     : {brand_count}")

    print(f"{'='*60}\n")


def load_data(data_type: str, session, monitor, batch_size: int):
    """Load a specific data type."""
    filename, ingester_class = DATA_FILES[data_type]
    file_path = DATA_DIR / filename

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None

    logger.info(f"Loading {data_type} from {file_path}...")
    ingester = ingester_class(db_session=session, batch_size=batch_size)
    result = ingester.run(file_path)
    report = monitor.check(result, data_type)

    print(f"\n  {data_type.upper()}: {result.successful:,} loaded, "
          f"{result.failed} failed, {result.duplicates_skipped} duplicates "
          f"[{report['status']}]")

    return report


def main():
    parser = argparse.ArgumentParser(description="Load product catalog into database")
    parser.add_argument("--clean", action="store_true", help="Drop and recreate tables before loading")
    parser.add_argument("--type", choices=["products", "reviews", "policies"], help="Load only a specific type")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for ingestion")
    args = parser.parse_args()

    engine = get_engine()

    if args.clean:
        logger.info("Dropping existing tables...")
        drop_tables(engine)

    logger.info("Creating tables...")
    create_tables(engine)

    session = get_session_factory(engine)()
    monitor = DataQualityMonitor()

    try:
        if args.type:
            load_data(args.type, session, monitor, args.batch_size)
        else:
            # Load in order: products first (reviews depend on products)
            for dtype in ["products", "reviews", "policies"]:
                load_data(dtype, session, monitor, args.batch_size)

        print_summary(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
