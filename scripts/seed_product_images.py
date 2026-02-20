#!/usr/bin/env python3
"""
Seed image_url for products that have no picture yet.

Uses https://picsum.photos/seed/{n}/400/300 which returns a deterministic
real photograph based on the seed number (consistent across runs).
"""

import hashlib
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session_factory
from app.models.product import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _image_url_for(product_id: str) -> str:
    """
    Return a deterministic picsum.photos URL for a product.

    The seed is a 4-digit number derived from the product_id's MD5 hash,
    ensuring each product always gets the same image across re-runs.
    """
    digest = hashlib.md5(product_id.encode()).hexdigest()
    seed = int(digest[:4], 16) % 1000   # 0–999 picsum seeds
    return f"https://picsum.photos/seed/{seed}/400/300"


def seed_images(dry_run: bool = False) -> int:
    """
    Update products with NULL image_url.

    Returns:
        Number of rows updated.
    """
    Session = get_session_factory()
    updated = 0

    with Session() as session:
        products = session.query(Product).filter(Product.image_url.is_(None)).all()
        logger.info("Found %d products with no image_url", len(products))

        for product in products:
            url = _image_url_for(product.id)
            if not dry_run:
                product.image_url = url
            updated += 1
            logger.debug("  %s → %s", product.id, url)

        if not dry_run:
            session.commit()
            logger.info("Committed %d image_url updates", updated)
        else:
            logger.info("Dry-run: would update %d products", updated)

    return updated


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    count = seed_images(dry_run=dry)
    print(f"{'Would update' if dry else 'Updated'} {count} products.")
