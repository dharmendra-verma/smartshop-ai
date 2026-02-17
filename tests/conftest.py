"""Pytest fixtures for testing."""

import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import Product, Review, Policy


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_product(db_session):
    """Create a sample product for testing."""
    product = Product(
        name="Test Product",
        description="Test Description",
        price=Decimal("99.99"),
        brand="TestBrand",
        category="Electronics",
        image_url="https://example.com/test.jpg",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_review(db_session, sample_product):
    """Create a sample review for testing."""
    review = Review(
        product_id=sample_product.product_id,
        rating=4,
        review_text="Great product!",
        sentiment="positive",
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


@pytest.fixture
def sample_policy(db_session):
    """Create a sample policy for testing."""
    policy = Policy(
        category="shipping",
        question="What is the shipping time?",
        answer="Standard shipping takes 3-5 business days.",
        effective_date=date(2026, 1, 1),
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy
