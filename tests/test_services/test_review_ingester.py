"""Tests for review data ingester."""

import pytest
from decimal import Decimal
from datetime import date

from app.models.product import Product
from app.models.review import Review
from app.services.ingestion.review_ingester import ReviewIngester


@pytest.fixture
def products_in_db(db_session):
    """Insert products so reviews have valid foreign keys."""
    for i in range(1, 6):
        product = Product(
            id=f"SP{i:04d}",
            name=f"Product {i}",
            price=Decimal("10.00"),
            category="General",
        )
        db_session.add(product)
    db_session.commit()
    return db_session.query(Product).all()


class TestReviewIngester:
    """Tests for ReviewIngester."""

    def test_ingest_valid_csv(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text,sentiment\n"
            "SP0001,5,Great product!,positive\n"
            "SP0002,3,It is okay.,neutral\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 2
        assert result.successful == 2

        reviews = db_session.query(Review).all()
        assert len(reviews) == 2

    def test_sentiment_inferred_from_rating(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text\n"
            "SP0001,5,Love it\n"
            "SP0002,1,Hate it\n"
            "SP0003,3,Meh\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 3
        reviews = db_session.query(Review).order_by(Review.product_id).all()
        assert reviews[0].sentiment == "positive"
        assert reviews[1].sentiment == "negative"
        assert reviews[2].sentiment == "neutral"

    def test_invalid_product_id_rejected(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text\n"
            "INVALID999,5,No such product\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.failed == 1
        assert result.successful == 0

    def test_deduplication_by_product_and_text(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating,text\n"
            "SP0001,5,Great product!\n"
            "SP0001,4,Great product!\n"
            "SP0001,5,Different review\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2
        assert result.duplicates_skipped == 1

    def test_handles_missing_review_text(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,rating\n"
            "SP0001,4\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        review = db_session.query(Review).first()
        assert review.text is None

    def test_column_mapping(self, db_session, tmp_path, products_in_db):
        csv_file = tmp_path / "reviews.csv"
        csv_file.write_text(
            "product_id,star_rating,review_body\n"
            "SP0001,5,Amazing!\n"
        )

        ingester = ReviewIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        review = db_session.query(Review).first()
        assert review.rating == 5
        assert review.text == "Amazing!"
