"""Tests for verify_data script functionality."""

import pytest
from decimal import Decimal

from sqlalchemy import func

from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy


@pytest.fixture
def populated_db(db_session):
    """Populate database with test data for verification."""
    # Products
    for i in range(10):
        db_session.add(Product(
            id=f"SP{i:04d}",
            name=f"Product {i}",
            brand=f"Brand{i % 3}",
            category=["smartphone", "laptop", "speaker"][i % 3],
            price=Decimal(f"{50 + i * 100}.99"),
            description=f"Description for product {i}",
            stock=i * 10,
            rating=round(3.0 + (i % 5) * 0.4, 1),
        ))
    db_session.commit()

    # Reviews
    for i in range(20):
        db_session.add(Review(
            product_id=f"SP{i % 10:04d}",
            rating=float(3 + i % 3),
            text=f"Review text {i}",
            sentiment=["positive", "neutral", "negative"][i % 3],
        ))
    db_session.commit()

    # Policies
    for i, ptype in enumerate(["shipping", "returns", "warranty"]):
        db_session.add(Policy(
            policy_type=ptype,
            description=f"{ptype.title()} Policy",
            conditions=f"Condition A|Condition B",
            timeframe=i * 15,
        ))
    db_session.commit()

    return db_session


class TestVerifyData:
    """Tests for data verification logic."""

    def test_product_count(self, populated_db):
        count = populated_db.query(func.count(Product.id)).scalar()
        assert count == 10

    def test_review_count(self, populated_db):
        count = populated_db.query(func.count(Review.review_id)).scalar()
        assert count == 20

    def test_policy_count(self, populated_db):
        count = populated_db.query(func.count(Policy.policy_id)).scalar()
        assert count == 3

    def test_category_distribution(self, populated_db):
        categories = (
            populated_db.query(Product.category, func.count())
            .group_by(Product.category)
            .all()
        )
        cat_dict = {cat: count for cat, count in categories}
        assert len(cat_dict) >= 3
        assert all(count > 0 for count in cat_dict.values())

    def test_price_statistics(self, populated_db):
        stats = populated_db.query(
            func.min(Product.price),
            func.max(Product.price),
            func.avg(Product.price),
        ).first()
        assert float(stats[0]) > 0  # min > 0
        assert float(stats[1]) > float(stats[0])  # max > min
        assert float(stats[2]) > 0  # avg > 0

    def test_no_null_required_fields(self, populated_db):
        null_names = populated_db.query(func.count()).select_from(Product).filter(Product.name.is_(None)).scalar()
        null_prices = populated_db.query(func.count()).select_from(Product).filter(Product.price.is_(None)).scalar()
        null_categories = populated_db.query(func.count()).select_from(Product).filter(Product.category.is_(None)).scalar()
        assert null_names == 0
        assert null_prices == 0
        assert null_categories == 0

    def test_unique_brands(self, populated_db):
        brand_count = populated_db.query(func.count(func.distinct(Product.brand))).scalar()
        assert brand_count >= 3

    def test_reviews_linked_to_products(self, populated_db):
        """Verify all reviews reference valid products."""
        orphan_reviews = (
            populated_db.query(Review)
            .filter(~Review.product_id.in_(
                populated_db.query(Product.id)
            ))
            .count()
        )
        assert orphan_reviews == 0
