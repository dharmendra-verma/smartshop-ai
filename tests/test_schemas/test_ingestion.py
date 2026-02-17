"""Tests for ingestion validation schemas."""

import pytest
from datetime import date
from pydantic import ValidationError

from app.schemas.ingestion import (
    ProductIngestionSchema,
    ReviewIngestionSchema,
    PolicyIngestionSchema,
    IngestionResult,
)


class TestProductIngestionSchema:
    """Tests for ProductIngestionSchema."""

    def test_valid_product(self):
        product = ProductIngestionSchema(
            name="Test Product",
            description="A test product",
            price=29.99,
            brand="TestBrand",
            category="electronics",
            image_url="https://example.com/img.jpg",
        )
        assert product.name == "Test Product"
        assert product.price == 29.99
        assert product.category == "Electronics"  # normalized to title case

    def test_minimal_product(self):
        product = ProductIngestionSchema(
            name="Test", price=1.0, category="general"
        )
        assert product.description is None
        assert product.brand is None
        assert product.image_url is None

    def test_invalid_price_zero(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(name="Test", price=0, category="General")

    def test_invalid_price_negative(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(name="Test", price=-10.0, category="General")

    def test_price_rounding(self):
        product = ProductIngestionSchema(
            name="Test", price=29.999, category="General"
        )
        assert product.price == 30.0

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(name="", price=10.0, category="General")

    def test_category_normalization(self):
        product = ProductIngestionSchema(
            name="Test", price=10.0, category="  home & kitchen  "
        )
        assert product.category == "Home & Kitchen"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(name="Test")


class TestReviewIngestionSchema:
    """Tests for ReviewIngestionSchema."""

    def test_valid_review(self):
        review = ReviewIngestionSchema(
            product_id=1,
            rating=5,
            review_text="Great product!",
            sentiment="positive",
        )
        assert review.product_id == 1
        assert review.rating == 5

    def test_rating_too_low(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(product_id=1, rating=0)

    def test_rating_too_high(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(product_id=1, rating=6)

    def test_valid_sentiments(self):
        for sentiment in ["positive", "negative", "neutral"]:
            review = ReviewIngestionSchema(
                product_id=1, rating=3, sentiment=sentiment
            )
            assert review.sentiment == sentiment

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(
                product_id=1, rating=3, sentiment="amazing"
            )

    def test_clean_review_text_whitespace(self):
        review = ReviewIngestionSchema(
            product_id=1, rating=4, review_text="  hello world  "
        )
        assert review.review_text == "hello world"

    def test_clean_review_text_empty_to_none(self):
        review = ReviewIngestionSchema(
            product_id=1, rating=4, review_text="   "
        )
        assert review.review_text is None

    def test_optional_fields(self):
        review = ReviewIngestionSchema(product_id=1, rating=3)
        assert review.review_text is None
        assert review.sentiment is None


class TestPolicyIngestionSchema:
    """Tests for PolicyIngestionSchema."""

    def test_valid_policy(self):
        policy = PolicyIngestionSchema(
            category="shipping",
            question="How long?",
            answer="3-5 days",
            effective_date=date(2026, 1, 1),
        )
        assert policy.category == "shipping"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PolicyIngestionSchema(category="shipping")

    def test_date_from_string(self):
        policy = PolicyIngestionSchema(
            category="returns",
            question="Can I return?",
            answer="Yes within 30 days",
            effective_date="2026-01-15",
        )
        assert policy.effective_date == date(2026, 1, 15)


class TestIngestionResult:
    """Tests for IngestionResult."""

    def test_default_values(self):
        result = IngestionResult()
        assert result.total_records == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.duplicates_skipped == 0
        assert result.errors == []

    def test_success_rate_calculation(self):
        result = IngestionResult(total_records=100, successful=80)
        assert result.success_rate == 80.0

    def test_success_rate_zero_records(self):
        result = IngestionResult()
        assert result.success_rate == 0.0

    def test_success_rate_all_successful(self):
        result = IngestionResult(total_records=50, successful=50)
        assert result.success_rate == 100.0

    def test_error_tracking(self):
        result = IngestionResult(
            total_records=10,
            successful=7,
            failed=3,
            errors=["err1", "err2", "err3"],
        )
        assert len(result.errors) == 3
        assert result.success_rate == 70.0
