#!/usr/bin/env python3
"""Verify data quality and completeness in the database.

Usage:
    python scripts/verify_data.py
    python scripts/verify_data.py --save  # Save report to JSON
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func

from app.core.database import get_engine, get_session_factory
from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy


def verify_data(session) -> dict:
    """Run comprehensive data quality verification."""
    report = {}

    # Record counts
    report["products_count"] = session.query(func.count(Product.id)).scalar()
    report["reviews_count"] = session.query(func.count(Review.review_id)).scalar()
    report["policies_count"] = session.query(func.count(Policy.policy_id)).scalar()

    # Category distribution
    categories = (
        session.query(Product.category, func.count())
        .group_by(Product.category)
        .order_by(func.count().desc())
        .all()
    )
    report["categories"] = {cat: count for cat, count in categories}

    # Price statistics
    price_stats = session.query(
        func.min(Product.price),
        func.max(Product.price),
        func.avg(Product.price),
    ).first()

    if price_stats[0] is not None:
        report["price_stats"] = {
            "min": float(price_stats[0]),
            "max": float(price_stats[1]),
            "avg": round(float(price_stats[2]), 2),
        }
    else:
        report["price_stats"] = {"min": 0, "max": 0, "avg": 0}

    # Null rate checks for products
    total = report["products_count"]
    if total > 0:
        null_checks = {
            "name": session.query(func.count()).select_from(Product).filter(Product.name.is_(None)).scalar(),
            "price": session.query(func.count()).select_from(Product).filter(Product.price.is_(None)).scalar(),
            "category": session.query(func.count()).select_from(Product).filter(Product.category.is_(None)).scalar(),
            "description": session.query(func.count()).select_from(Product).filter(Product.description.is_(None)).scalar(),
            "brand": session.query(func.count()).select_from(Product).filter(Product.brand.is_(None)).scalar(),
        }
        report["null_rates"] = {
            f"{k}_nulls": f"{(v / total) * 100:.1f}%" for k, v in null_checks.items()
        }
    else:
        report["null_rates"] = {}

    # Unique brands
    report["unique_brands"] = session.query(func.count(func.distinct(Product.brand))).scalar()

    # Quality checks
    checks = []
    checks.append(("Products >= 1000", report["products_count"] >= 1000))
    checks.append(("Reviews loaded", report["reviews_count"] > 0))
    checks.append(("Policies loaded", report["policies_count"] > 0))
    checks.append(("Multiple categories", len(report["categories"]) >= 3))
    checks.append(("Multiple brands", report["unique_brands"] >= 5))
    checks.append(("Price min > 0", report["price_stats"]["min"] > 0))

    report["checks"] = {name: passed for name, passed in checks}
    report["all_passed"] = all(passed for _, passed in checks)

    return report


def print_report(report: dict):
    """Print formatted verification report."""
    print(f"\n{'='*60}")
    print(f"  DATA QUALITY VERIFICATION REPORT")
    print(f"{'='*60}")

    print(f"\n  Record Counts:")
    print(f"    Products : {report['products_count']:,}")
    print(f"    Reviews  : {report['reviews_count']:,}")
    print(f"    Policies : {report['policies_count']:,}")

    print(f"\n  Category Distribution:")
    for cat, count in report["categories"].items():
        print(f"    {cat:<20s} {count:>5,}")

    print(f"\n  Price Statistics:")
    ps = report["price_stats"]
    print(f"    Min : ${ps['min']:.2f}")
    print(f"    Max : ${ps['max']:.2f}")
    print(f"    Avg : ${ps['avg']:.2f}")

    print(f"\n  Null Rates:")
    for field, rate in report["null_rates"].items():
        print(f"    {field:<20s} {rate}")

    print(f"\n  Unique Brands: {report['unique_brands']}")

    print(f"\n  Quality Checks:")
    for name, passed in report["checks"].items():
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {name}")

    overall = "ALL PASSED" if report["all_passed"] else "SOME FAILED"
    print(f"\n  Overall: {overall}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Verify data quality")
    parser.add_argument("--save", action="store_true", help="Save report to JSON")
    args = parser.parse_args()

    engine = get_engine()
    session = get_session_factory(engine)()

    try:
        report = verify_data(session)
        print_report(report)

        if args.save:
            output_dir = Path("data/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "data_quality_report.json"
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"  Report saved to {output_path}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
