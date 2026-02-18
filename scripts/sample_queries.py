#!/usr/bin/env python3
"""Sample queries to demonstrate data access patterns.

Usage:
    python scripts/sample_queries.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, or_

from app.core.database import get_engine, get_session_factory
from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy


def timed_query(name, query_func):
    """Run a query and print results with timing."""
    start = time.time()
    result = query_func()
    elapsed = (time.time() - start) * 1000
    print(f"\n  [{name}] ({elapsed:.1f}ms)")
    return result


def run_sample_queries():
    engine = get_engine()
    session = get_session_factory(engine)()

    print(f"\n{'='*60}")
    print(f"  SAMPLE QUERIES")
    print(f"{'='*60}")

    try:
        # Query 1: Search products by name
        def q1():
            results = session.query(Product).filter(
                Product.name.ilike("%phone%")
            ).all()
            print(f"    Products matching 'phone': {len(results)}")
            for p in results[:3]:
                print(f"      - {p.name} (${float(p.price):.2f})")
            if len(results) > 3:
                print(f"      ... and {len(results) - 3} more")
            return results
        timed_query("Search by name: 'phone'", q1)

        # Query 2: Filter by category
        def q2():
            results = session.query(Product).filter(
                Product.category == "laptop"
            ).all()
            print(f"    Laptops: {len(results)}")
            return results
        timed_query("Filter by category: 'laptop'", q2)

        # Query 3: Filter by price range
        def q3():
            results = session.query(Product).filter(
                Product.price.between(100, 500)
            ).all()
            print(f"    Products $100-$500: {len(results)}")
            return results
        timed_query("Filter by price range: $100-$500", q3)

        # Query 4: Products by brand
        def q4():
            results = (
                session.query(Product.brand, func.count().label("count"))
                .group_by(Product.brand)
                .order_by(func.count().desc())
                .all()
            )
            print(f"    Top brands:")
            for brand, count in results[:5]:
                print(f"      {brand:<20s} {count:>4} products")
            return results
        timed_query("Products by brand", q4)

        # Query 5: Category summary (count + avg price)
        def q5():
            results = (
                session.query(
                    Product.category,
                    func.count().label("count"),
                    func.avg(Product.price).label("avg_price"),
                )
                .group_by(Product.category)
                .order_by(func.count().desc())
                .all()
            )
            print(f"    Category summary:")
            for cat, count, avg_price in results:
                print(f"      {cat:<20s} {count:>4} products, avg ${float(avg_price):.2f}")
            return results
        timed_query("Category summary", q5)

        # Query 6: Top-rated products (by review avg)
        def q6():
            results = (
                session.query(
                    Product.name,
                    Product.brand,
                    func.avg(Review.rating).label("avg_rating"),
                    func.count(Review.review_id).label("review_count"),
                )
                .join(Review, Product.id == Review.product_id)
                .group_by(Product.id)
                .having(func.count(Review.review_id) >= 3)
                .order_by(func.avg(Review.rating).desc())
                .limit(5)
                .all()
            )
            print(f"    Top-rated products (3+ reviews):")
            for name, brand, avg_r, count in results:
                print(f"      {name:<30s} {brand:<15s} {float(avg_r):.1f}/5 ({count} reviews)")
            return results
        timed_query("Top-rated products", q6)

        # Query 7: Products with most reviews
        def q7():
            results = (
                session.query(
                    Product.name,
                    func.count(Review.review_id).label("review_count"),
                )
                .join(Review, Product.id == Review.product_id)
                .group_by(Product.id)
                .order_by(func.count(Review.review_id).desc())
                .limit(5)
                .all()
            )
            print(f"    Most reviewed products:")
            for name, count in results:
                print(f"      {name:<35s} {count} reviews")
            return results
        timed_query("Most reviewed products", q7)

        # Query 8: Policy summary
        def q8():
            results = (
                session.query(
                    Policy.policy_type,
                    func.count().label("count"),
                )
                .group_by(Policy.policy_type)
                .all()
            )
            print(f"    Policy types:")
            for ptype, count in results:
                print(f"      {ptype:<20s} {count} policies")
            return results
        timed_query("Policy summary", q8)

    finally:
        session.close()

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    run_sample_queries()
