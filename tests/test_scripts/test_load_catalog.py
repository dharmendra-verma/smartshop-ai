"""Tests for load_catalog script functionality."""

import pytest
from decimal import Decimal
from pathlib import Path

from app.models.product import Product
from app.models.review import Review
from app.models.policy import Policy
from app.services.ingestion.product_ingester import ProductIngester
from app.services.ingestion.review_ingester import ReviewIngester
from app.services.ingestion.policy_ingester import PolicyIngester
from app.services.ingestion.quality_monitor import DataQualityMonitor


class TestLoadProducts:
    """Tests for product loading."""

    def test_load_products_from_csv(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,brand,category,price,description,stock,rating\n"
            "SP0001,Phone X,TechCo,smartphone,699.99,A great phone,50,4.5\n"
            "LP0002,Laptop Y,CompBrand,laptop,1299.99,Fast laptop,25,4.2\n"
            "TV0003,TV Z,ViewTech,smart_tv,999.99,Big screen,10,3.8\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 3
        assert result.successful == 3
        assert result.failed == 0

        products = db_session.query(Product).all()
        assert len(products) == 3

    def test_load_products_quality_check(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,brand,category,price,description,stock,rating\n"
            "SP0001,Phone,TechCo,smartphone,699.99,Desc,50,4.5\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)
        monitor = DataQualityMonitor(report_dir=str(tmp_path))
        report = monitor.check(result, "test_products")

        assert report["status"] == "PASS"
        assert report["successful"] == 1

    def test_load_products_deduplication(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,brand,category,price,description,stock,rating\n"
            "SP0001,Phone,TechCo,smartphone,699.99,Desc,50,4.5\n"
            "SP0001,Phone Dup,TechCo,smartphone,799.99,Dup,30,4.0\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        assert result.duplicates_skipped == 1


class TestLoadReviews:
    """Tests for review loading (requires products first)."""

    def test_load_reviews_with_products(self, db_session, tmp_path):
        # Create products first
        db_session.add(Product(id="SP0001", name="Phone", price=Decimal("699.99"), category="smartphone"))
        db_session.add(Product(id="SP0002", name="Laptop", price=Decimal("999.99"), category="laptop"))
        db_session.commit()

        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text,date\n"
            "SP0001,5,Great phone!,1/15/2025\n"
            "SP0002,4,Good laptop,2/20/2025\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        reviews = db_session.query(Review).all()
        assert len(reviews) == 2

    def test_reviews_with_invalid_product_id_rejected(self, db_session, tmp_path):
        db_session.add(Product(id="SP0001", name="Phone", price=Decimal("699.99"), category="smartphone"))
        db_session.commit()

        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text,date\n"
            "SP0001,5,Good,1/15/2025\n"
            "INVALID,3,Bad ID,1/16/2025\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        assert result.failed == 1

    def test_sentiment_auto_inferred(self, db_session, tmp_path):
        db_session.add(Product(id="SP0001", name="Phone", price=Decimal("699.99"), category="smartphone"))
        db_session.commit()

        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text\n"
            "SP0001,5,Love it\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        ingester.run(csv_file)

        review = db_session.query(Review).first()
        assert review.sentiment == "positive"


class TestLoadPolicies:
    """Tests for policy loading."""

    def test_load_policies_from_csv(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            "returns,Return Policy,Must be unused|Original packaging,30\n"
            "shipping,Shipping Policy,Free over $50|US only,5\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        policies = db_session.query(Policy).all()
        assert len(policies) == 2

    def test_policy_conditions_stored_correctly(self, db_session, tmp_path):
        csv_file = tmp_path / "policies.csv"
        csv_file.write_text(
            "policy_type,description,conditions,timeframe\n"
            "warranty,Warranty Policy,Covers defects|1 year parts,365\n"
        )

        ingester = PolicyIngester(db_session=db_session)
        ingester.run(csv_file)

        policy = db_session.query(Policy).first()
        assert "|" in policy.conditions
        assert policy.timeframe == 365
