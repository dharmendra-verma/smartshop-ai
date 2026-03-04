"""Tests for database core module."""

import pytest
from sqlalchemy import create_engine, inspect
from unittest.mock import patch

from app.core.database import Base, get_engine, get_session_factory, create_tables, drop_tables, reset_engine
from app.models import Product, Review, Policy  # noqa: F401 - register models


@pytest.fixture(autouse=True)
def _reset_db_singletons():
    reset_engine()
    yield
    reset_engine()


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
    session.add(Product(id="TEST001", name="Test", price=10.00, category="Test"))
    session.commit()

    result = session.query(Product).first()
    assert result.name == "Test"

    session.close()


def test_get_engine_returns_singleton():
    """Test that get_engine() returns the same instance on repeated calls."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.DATABASE_URL = "sqlite:///test_singleton.db"
        mock_settings.return_value.DB_ECHO = False
        mock_settings.return_value.DB_POOL_SIZE = 5
        mock_settings.return_value.DB_MAX_OVERFLOW = 10
        with patch("app.core.database.create_engine") as mock_ce:
            mock_ce.return_value = create_engine("sqlite:///:memory:")
            e1 = get_engine()
            e2 = get_engine()
            assert e1 is e2
            assert mock_ce.call_count == 1


def test_reset_engine_clears_singleton():
    """Test that reset_engine() clears cached engine and session factory."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.DATABASE_URL = "sqlite:///test_singleton.db"
        mock_settings.return_value.DB_ECHO = False
        mock_settings.return_value.DB_POOL_SIZE = 5
        mock_settings.return_value.DB_MAX_OVERFLOW = 10
        with patch("app.core.database.create_engine") as mock_ce:
            mock_ce.return_value = create_engine("sqlite:///:memory:")
            e1 = get_engine()
            reset_engine()
            mock_ce.return_value = create_engine("sqlite:///:memory:")
            e2 = get_engine()
            assert e1 is not e2
            assert mock_ce.call_count == 2


def test_get_session_factory_returns_singleton():
    """Test that get_session_factory() returns the same factory when no engine given."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.DATABASE_URL = "sqlite:///test_singleton.db"
        mock_settings.return_value.DB_ECHO = False
        mock_settings.return_value.DB_POOL_SIZE = 5
        mock_settings.return_value.DB_MAX_OVERFLOW = 10
        with patch("app.core.database.create_engine") as mock_ce:
            mock_ce.return_value = create_engine("sqlite:///:memory:")
            f1 = get_session_factory()
            f2 = get_session_factory()
            assert f1 is f2
