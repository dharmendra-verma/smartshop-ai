"""Tests for model imports."""

from app.models import Base, Product, Review, Policy


def test_base_import():
    """Test that Base is importable from app.models."""
    assert Base is not None


def test_product_import():
    """Test that Product is importable."""
    assert Product.__tablename__ == "products"


def test_review_import():
    """Test that Review is importable."""
    assert Review.__tablename__ == "reviews"


def test_policy_import():
    """Test that Policy is importable."""
    assert Policy.__tablename__ == "policies"


def test_all_exports():
    """Test that __all__ contains expected models."""
    import app.models as models
    assert "Base" in models.__all__
    assert "Product" in models.__all__
    assert "Review" in models.__all__
    assert "Policy" in models.__all__
