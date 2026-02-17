"""Initialize database with schema and optionally seed data."""

import sys
import logging
from pathlib import Path
from datetime import date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, get_engine, get_session_factory
from app.models import Product, Review, Policy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database(use_alembic: bool = True, seed_data: bool = False) -> None:
    """Initialize database with schema.

    Args:
        use_alembic: If True, use Alembic migrations; else use create_tables().
        seed_data: If True, populate with sample data.
    """
    try:
        if use_alembic:
            logger.info("Running Alembic migrations...")
            from alembic.config import Config
            from alembic import command

            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations completed successfully!")
        else:
            logger.info("Creating tables directly...")
            engine = get_engine()
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created successfully!")

        if seed_data:
            logger.info("Seeding sample data...")
            seed_sample_data()
            logger.info("Sample data seeded!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def seed_sample_data() -> None:
    """Seed database with sample data for testing."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()

    try:
        sample_products = [
            Product(
                name="Wireless Bluetooth Headphones",
                description="Premium noise-cancelling headphones with 30hr battery",
                price=Decimal("79.99"),
                brand="AudioTech",
                category="Electronics",
                image_url="https://example.com/headphones.jpg",
            ),
            Product(
                name="Organic Cotton T-Shirt",
                description="Comfortable and sustainable everyday wear",
                price=Decimal("24.99"),
                brand="EcoWear",
                category="Clothing",
                image_url="https://example.com/tshirt.jpg",
            ),
            Product(
                name="Stainless Steel Water Bottle",
                description="Double-walled insulated bottle, keeps drinks cold 24hrs",
                price=Decimal("29.99"),
                brand="HydroLife",
                category="Home & Kitchen",
                image_url="https://example.com/bottle.jpg",
            ),
        ]
        db.add_all(sample_products)
        db.flush()

        sample_reviews = [
            Review(product_id=sample_products[0].product_id, rating=5, review_text="Amazing sound quality!", sentiment="positive"),
            Review(product_id=sample_products[0].product_id, rating=4, review_text="Good but a bit heavy.", sentiment="positive"),
            Review(product_id=sample_products[1].product_id, rating=3, review_text="Decent quality for the price.", sentiment="neutral"),
        ]
        db.add_all(sample_reviews)

        sample_policies = [
            Policy(category="shipping", question="What is the shipping time?", answer="Standard shipping takes 3-5 business days.", effective_date=date(2026, 1, 1)),
            Policy(category="returns", question="What is the return policy?", answer="You can return items within 30 days of purchase for a full refund.", effective_date=date(2026, 1, 1)),
            Policy(category="privacy", question="How is my data used?", answer="We only use your data to process orders and improve our service.", effective_date=date(2026, 1, 1)),
        ]
        db.add_all(sample_policies)

        db.commit()
        logger.info(f"Added {len(sample_products)} products, {len(sample_reviews)} reviews, {len(sample_policies)} policies")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize SmartShop AI database")
    parser.add_argument("--no-alembic", action="store_true", help="Skip Alembic, create tables directly")
    parser.add_argument("--seed", action="store_true", help="Seed sample data")

    args = parser.parse_args()
    init_database(use_alembic=not args.no_alembic, seed_data=args.seed)
