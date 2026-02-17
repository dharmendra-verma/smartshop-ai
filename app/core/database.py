"""Database configuration and session management."""

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_engine() -> Engine:
    """Create and return the database engine."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    """Create a session factory bound to the given engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def create_tables(engine: Engine | None = None) -> None:
    """Create all tables in the database."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Engine | None = None) -> None:
    """Drop all tables in the database."""
    if engine is None:
        engine = get_engine()
    Base.metadata.drop_all(bind=engine)
