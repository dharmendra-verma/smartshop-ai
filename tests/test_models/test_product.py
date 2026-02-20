"""Tests for Product model."""

import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models import Product


def test_product_creation(db_session):
    """Test creating a product with all fields."""
    product = Product(
        id="LP0001",
        name="Laptop",
        description="High-performance laptop",
        price=Decimal("1299.99"),
        brand="TechCorp",
        category="Computers",
        stock=25,
        rating=4.5,
    )
    db_session.add(product)
    db_session.commit()

    assert product.id == "LP0001"
    assert product.name == "Laptop"
    assert product.price == Decimal("1299.99")
    assert product.brand == "TechCorp"
    assert product.category == "Computers"
    assert product.stock == 25
    assert product.rating == 4.5


def test_product_creation_minimal(db_session):
    """Test creating a product with only required fields."""
    product = Product(
        id="SP0002",
        name="Basic Item",
        price=Decimal("9.99"),
        category="General",
    )
    db_session.add(product)
    db_session.commit()

    assert product.id == "SP0002"
    assert product.description is None
    assert product.brand is None
    assert product.rating is None


def test_product_name_required(db_session):
    """Test that name is required."""
    product = Product(id="SP0003", price=Decimal("10.00"), category="Test")
    db_session.add(product)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_product_price_required(db_session):
    """Test that price is required."""
    product = Product(id="SP0004", name="No Price", category="Test")
    db_session.add(product)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_product_category_required(db_session):
    """Test that category is required."""
    product = Product(id="SP0005", name="No Category", price=Decimal("10.00"))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_product_to_dict(sample_product):
    """Test product to_dict method."""
    product_dict = sample_product.to_dict()

    assert product_dict["name"] == "Test Product"
    assert product_dict["price"] == 99.99
    assert product_dict["brand"] == "TestBrand"
    assert product_dict["category"] == "Electronics"
    assert "id" in product_dict
    assert product_dict["stock"] == 50
    assert product_dict["rating"] == 4.2
    assert "created_at" in product_dict


def test_product_repr(sample_product):
    """Test product string representation."""
    repr_str = repr(sample_product)
    assert "Product" in repr_str
    assert "Test Product" in repr_str


def test_product_query_by_category(db_session):
    """Test querying products by category."""
    for i in range(3):
        db_session.add(Product(id=f"EL{i:04d}", name=f"Electronics {i}", price=Decimal("10.00"), category="Electronics"))
    for i in range(2):
        db_session.add(Product(id=f"CL{i:04d}", name=f"Clothing {i}", price=Decimal("20.00"), category="Clothing"))
    db_session.commit()

    electronics = db_session.query(Product).filter(Product.category == "Electronics").all()
    assert len(electronics) == 3

    clothing = db_session.query(Product).filter(Product.category == "Clothing").all()
    assert len(clothing) == 2


def test_product_query_by_brand(db_session):
    """Test querying products by brand."""
    db_session.add(Product(id="P001", name="P1", price=Decimal("10.00"), category="Test", brand="BrandA"))
    db_session.add(Product(id="P002", name="P2", price=Decimal("20.00"), category="Test", brand="BrandB"))
    db_session.add(Product(id="P003", name="P3", price=Decimal("30.00"), category="Test", brand="BrandA"))
    db_session.commit()

    brand_a = db_session.query(Product).filter(Product.brand == "BrandA").all()
    assert len(brand_a) == 2


def test_product_price_precision(db_session):
    """Test price handles decimal precision correctly."""
    product = Product(id="PR001", name="Precise", price=Decimal("19.95"), category="Test")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    assert product.price == Decimal("19.95")
    assert product.to_dict()["price"] == 19.95


def test_product_to_dict_includes_image_url():
    p = Product(
        id="TEST001", name="Widget", price=9.99, category="gadgets",
        image_url="https://picsum.photos/seed/42/400/300",
    )
    d = p.to_dict()
    assert "image_url" in d
    assert d["image_url"] == "https://picsum.photos/seed/42/400/300"


def test_product_to_dict_image_url_none_when_unset():
    p = Product(id="TEST002", name="Widget", price=9.99, category="gadgets")
    d = p.to_dict()
    assert d["image_url"] is None
