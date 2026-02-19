"""pydantic-ai tools for the PriceComparisonAgent."""

import logging
import time
from pydantic_ai import RunContext
from app.agents.dependencies import AgentDependencies
from app.models.product import Product

logger = logging.getLogger(__name__)


async def search_products_by_name(
    ctx: RunContext[AgentDependencies],
    name: str,
    limit: int = 5,
) -> list[dict]:
    """
    Search for products by name (fuzzy match on name and brand).

    Use this to find specific products mentioned by the user, e.g. "Samsung S24",
    "Google Pixel 8", "Sony WH-1000XM5".

    Args:
        name: Product name or brand+model string to search for
        limit: Maximum results (default 5)
    """
    db = ctx.deps.db
    products = (
        db.query(Product)
        .filter(Product.name.ilike(f"%{name}%"))
        .limit(limit)
        .all()
    )
    if not products:
        # Fallback: search by brand
        parts = name.split()
        if parts:
            products = (
                db.query(Product)
                .filter(Product.brand.ilike(f"%{parts[0]}%"))
                .limit(limit)
                .all()
            )
    logger.debug("search_products_by_name('%s'): found %d", name, len(products))
    return [p.to_dict() for p in products]


async def get_competitor_prices(
    ctx: RunContext[AgentDependencies],
    product_id: str,
    base_price: float,
) -> dict:
    """
    Retrieve competitor prices for a product from multiple sources.

    Checks the price cache first (1-hour TTL); fetches fresh prices on cache miss.
    Returns prices from Amazon, BestBuy, and Walmart alongside our catalog price.
    Also returns the best deal (lowest price) and savings percentage.

    Args:
        product_id: Product identifier (e.g. "PROD001")
        base_price: Our catalog price for this product
    """
    from app.services.pricing.price_cache import get_price_cache
    from app.services.pricing.mock_pricing import MockPricingService

    cache = get_price_cache()
    cached = cache.get(product_id)

    if cached:
        logger.debug("PriceCache hit for %s", product_id)
        return cached

    # Fetch fresh competitor prices
    service = MockPricingService()
    competitor_prices = service.get_prices(product_id, base_price)

    # Build full price map (include our price)
    all_prices = {"SmartShop": base_price, **competitor_prices}
    best_source = min(all_prices, key=all_prices.get)
    best_price = all_prices[best_source]
    savings_vs_highest = max(all_prices.values()) - best_price
    savings_pct = (savings_vs_highest / max(all_prices.values())) * 100 if savings_vs_highest > 0 else 0.0

    result = {
        "product_id": product_id,
        "prices": all_prices,
        "best_source": best_source,
        "best_price": best_price,
        "savings_pct": round(savings_pct, 1),
        "cached_at": time.time(),
        "is_cached": False,
    }

    cache.set(product_id, result, ttl=3600)
    logger.debug("PriceCache miss for %s — fetched and cached", product_id)
    return result
