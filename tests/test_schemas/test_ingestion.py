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
            id="SP0001",
            name="Test Product",
            description="A test product",
            price=29.99,
            brand="TestBrand",
            category="electronics",
            stock=50,
            rating=4.5,
        )
        assert product.id == "SP0001"
        assert product.name == "Test Product"
        assert product.price == 29.99
        assert product.category == "Electronics"  # normalized to title case
        assert product.stock == 50
        assert product.rating == 4.5

    def test_minimal_product(self):
        product = ProductIngestionSchema(
            id="SP0002", name="Test", price=1.0, category="general"
        )
        assert product.description is None
        assert product.brand is None
        assert product.stock is None
        assert product.rating is None

    def test_invalid_price_zero(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0003", name="Test", price=0, category="General")

    def test_invalid_price_negative(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0004", name="Test", price=-10.0, category="General")

    def test_price_rounding(self):
        product = ProductIngestionSchema(
            id="SP0005", name="Test", price=29.999, category="General"
        )
        assert product.price == 30.0

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0006", name="", price=10.0, category="General")

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="", name="Test", price=10.0, category="General")

    def test_category_normalization(self):
        product = ProductIngestionSchema(
            id="SP0007", name="Test", price=10.0, category="  home & kitchen  "
        )
        assert product.category == "Home & Kitchen"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0008", name="Test")

    def test_invalid_rating_too_high(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0009", name="Test", price=10.0, category="General", rating=6.0)

    def test_invalid_stock_negative(self):
        with pytest.raises(ValidationError):
            ProductIngestionSchema(id="SP0010", name="Test", price=10.0, category="General", stock=-1)


class TestReviewIngestionSchema:
    """Tests for ReviewIngestionSchema."""

    def test_valid_review(self):
        review = ReviewIngestionSchema(
            product_id="SP0001",
            rating=5.0,
            text="Great product!",
            sentiment="positive",
        )
        assert review.product_id == "SP0001"
        assert review.rating == 5.0

    def test_rating_too_low(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(product_id="SP0001", rating=0.0)

    def test_rating_too_high(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(product_id="SP0001", rating=6.0)

    def test_valid_sentiments(self):
        for sentiment in ["positive", "negative", "neutral"]:
            review = ReviewIngestionSchema(
                product_id="SP0001", rating=3.0, sentiment=sentiment
            )
            assert review.sentiment == sentiment

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            ReviewIngestionSchema(
                product_id="SP0001", rating=3.0, sentiment="amazing"
            )

    def test_clean_text_whitespace(self):
        review = ReviewIngestionSchema(
            product_id="SP0001", rating=4.0, text="  hello world  "
        )
        assert review.text == "hello world"

    def test_clean_text_empty_to_none(self):
        review = ReviewIngestionSchema(
            product_id="SP0001", rating=4.0, text="   "
        )
        assert review.text is None

    def test_optional_fields(self):
        review = ReviewIngestionSchema(product_id="SP0001", rating=3.0)
        assert review.text is None
        assert review.sentiment is None
        assert review.review_date is None

    def test_review_date(self):
        review = ReviewIngestionSchema(
            product_id="SP0001", rating=4.0, review_date=date(2025, 1, 15)
        )
        assert review.review_date == date(2025, 1, 15)

    def test_float_rating(self):
        review = ReviewIngestionSchema(product_id="SP0001", rating=3.5)
        assert review.rating == 3.5


class TestPolicyIngestionSchema:
    """Tests for PolicyIngestionSchema."""

    def test_valid_policy(self):
        policy = PolicyIngestionSchema(
            policy_type="shipping",
            description="Standard Shipping Policy",
            conditions="Order subtotal must be at least $50|Eligible for contiguous U.S. only",
            timeframe=5,
        )
        assert policy.policy_type == "shipping"
        assert policy.timeframe == 5

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PolicyIngestionSchema(policy_type="shipping")

    def test_timeframe_zero_allowed(self):
        policy = PolicyIngestionSchema(
            policy_type="returns",
            description="Return Policy",
            conditions="Must be unused",
            timeframe=0,
        )
        assert policy.timeframe == 0

    def test_negative_timeframe_rejected(self):
        with pytest.raises(ValidationError):
            PolicyIngestionSchema(
                policy_type="returns",
                description="Return Policy",
                conditions="Must be unused",
                timeframe=-1,
            )

    def test_empty_policy_type_rejected(self):
        with pytest.raises(ValidationError):
            PolicyIngestionSchema(
                policy_type="",
                description="D",
                conditions="C",
                timeframe=0,
            )


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
