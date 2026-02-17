"""Tests for database core module."""

from sqlalchemy import create_engine, inspect

from app.core.database import Base, get_session_factory, create_tables, drop_tables
from app.models import Product, Review, Policy  # noqa: F401 - register models


def test_base_has_metadata():
    """Test that Base has metadata for table registration."""
    assert Base.metadata is not None
    table_names = list(Base.metadata.tables.keys())
    assert "products" in table_names
    assert "reviews" in table_names
    assert "policies" in table_names


def test_create_tables():
    """Test that create_tables creates all tables."""
    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "products" in tables
    assert "reviews" in tables
    assert "policies" in tables


def test_drop_tables():
    """Test that drop_tables removes all tables."""
    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)
    drop_tables(engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert len(tables) == 0


def test_get_session_factory():
    """Test that get_session_factory returns a working session factory."""
    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)

    factory = get_session_factory(engine)
    session = factory()
    assert session is not None

    # Verify session can query
    products = session.query(Product).all()
    assert products == []

    session.close()


def test_session_lifecycle():
    """Test that sessions can be created and closed properly."""
    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)
    factory = get_session_factory(engine)

    session = factory()
    session.add(Product(name="Test", price=10.00, category="Test"))
    session.commit()

    result = session.query(Product).first()
    assert result.name == "Test"

    session.close()
