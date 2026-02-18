"""Product search tools for the Recommendation Agent."""

import logging
from pydantic_ai import RunContext
from sqlalchemy.orm import Session
from app.agents.dependencies import AgentDependencies
from app.models.product import Product

logger = logging.getLogger(__name__)


async def search_products_by_filters(
    ctx: RunContext[AgentDependencies],
    category: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search the product catalog with optional filters.

    Use this to find products matching user criteria. All filters are optional
    and combined with AND logic. Call multiple times with different filters
    to explore the catalog.

    Args:
        category: Product category (e.g. "electronics", "laptops", "smartphones")
        brand: Brand name (e.g. "Samsung", "Apple", "Sony")
        min_price: Minimum price in USD
        max_price: Maximum price in USD
        min_rating: Minimum rating (0.0-5.0)
        limit: Max results to return (default 20, max 50)
    """
    db: Session = ctx.deps.db
    query = db.query(Product)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)

    limit = min(limit, 50)
    products = query.order_by(Product.rating.desc().nullslast()).limit(limit).all()

    logger.debug("search_products_by_filters: found %d products", len(products))
    return [p.to_dict() for p in products]


async def get_product_details(
    ctx: RunContext[AgentDependencies],
    product_id: str,
) -> dict | None:
    """
    Retrieve full details for a specific product by its ID.

    Use this when you need more information about a product you found via search,
    or when the user asks about a specific product by ID.

    Args:
        product_id: The product's unique identifier (e.g. "PROD001")
    """
    db: Session = ctx.deps.db
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    return product.to_dict()


async def get_categories(ctx: RunContext[AgentDependencies]) -> list[str]:
    """
    Get a list of all distinct product categories available in the catalog.

    Use this when you're unsure what categories exist, to help interpret
    vague user queries (e.g. mapping "phones" to "smartphones").
    """
    db: Session = ctx.deps.db
    from sqlalchemy import distinct
    results = db.query(distinct(Product.category)).filter(
        Product.category.isnot(None)
    ).all()
    return sorted([r[0] for r in results if r[0]])
