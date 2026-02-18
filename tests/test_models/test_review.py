"""Tests for Review model."""

import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy.exc import IntegrityError

from app.models import Product, Review


def test_review_creation(db_session, sample_product):
    """Test creating a review with all fields."""
    review = Review(
        product_id=sample_product.id,
        rating=5.0,
        text="Excellent product!",
        sentiment="positive",
        review_date=date(2025, 1, 15),
    )
    db_session.add(review)
    db_session.commit()

    assert review.review_id is not None
    assert review.product_id == sample_product.id
    assert review.rating == 5.0
    assert review.sentiment == "positive"
    assert review.review_date == date(2025, 1, 15)


def test_review_minimal(db_session, sample_product):
    """Test creating a review with only required fields."""
    review = Review(
        product_id=sample_product.id,
        rating=3.0,
    )
    db_session.add(review)
    db_session.commit()

    assert review.review_id is not None
    assert review.text is None
    assert review.sentiment is None
    assert review.review_date is None


def test_review_product_relationship(db_session, sample_product):
    """Test the Review -> Product relationship."""
    review = Review(product_id=sample_product.id, rating=4.0, text="Good")
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    assert review.product is not None
    assert review.product.name == "Test Product"


def test_product_reviews_backref(db_session, sample_product):
    """Test the Product.reviews backref."""
    for i in range(3):
        db_session.add(Review(product_id=sample_product.id, rating=float(i + 3)))
    db_session.commit()
    db_session.refresh(sample_product)

    assert len(sample_product.reviews) == 3


def test_review_product_id_required(db_session):
    """Test that product_id is required (foreign key)."""
    review = Review(rating=3.0, text="No product")
    db_session.add(review)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_rating_required(db_session, sample_product):
    """Test that rating is required."""
    review = Review(product_id=sample_product.id, text="No rating")
    db_session.add(review)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_cascade_delete(db_session, sample_product):
    """Test that reviews are deleted when product is deleted."""
    for i in range(3):
        db_session.add(Review(product_id=sample_product.id, rating=4.0))
    db_session.commit()

    db_session.delete(sample_product)
    db_session.commit()

    reviews = db_session.query(Review).all()
    assert len(reviews) == 0


def test_review_to_dict(sample_review):
    """Test review to_dict method."""
    review_dict = sample_review.to_dict()

    assert review_dict["rating"] == 4.0
    assert review_dict["text"] == "Great product!"
    assert review_dict["sentiment"] == "positive"
    assert review_dict["review_date"] == "2025-01-15"
    assert "review_id" in review_dict
    assert "product_id" in review_dict


def test_review_repr(sample_review):
    """Test review string representation."""
    repr_str = repr(sample_review)
    assert "Review" in repr_str
    assert str(sample_review.review_id) in repr_str


def test_review_sentiment_values(db_session, sample_product):
    """Test different sentiment values."""
    sentiments = ["positive", "negative", "neutral"]
    for s in sentiments:
        db_session.add(Review(product_id=sample_product.id, rating=3.0, sentiment=s))
    db_session.commit()

    for s in sentiments:
        result = db_session.query(Review).filter(Review.sentiment == s).first()
        assert result is not None
        assert result.sentiment == s
