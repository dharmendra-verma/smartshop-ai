"""Tools for the Review Summarization Agent."""

import logging
from pydantic_ai import RunContext
from sqlalchemy import func
from app.agents.dependencies import AgentDependencies
from app.models.review import Review
from app.models.product import Product

logger = logging.getLogger(__name__)


async def find_product(
    ctx: RunContext[AgentDependencies],
    name_or_id: str,
) -> dict | None:
    """
    Find a product by name (fuzzy) or exact product ID.

    Always call this first when the user provides a product name.
    Returns product dict with 'id' and 'name', or None if not found.

    Args:
        name_or_id: Product name (e.g. "iPhone 15", "Samsung Galaxy") or exact ID (e.g. "PROD001")
    """
    db = ctx.deps.db
    # Try exact ID first
    product = db.query(Product).filter(Product.id == name_or_id).first()
    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fuzzy name match
    product = db.query(Product).filter(
        Product.name.ilike(f"%{name_or_id}%")
    ).order_by(Product.rating.desc().nullslast()).first()

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fallback: search by brand
    product = db.query(Product).filter(
        Product.brand.ilike(f"%{name_or_id}%")
    ).order_by(Product.rating.desc().nullslast()).first()

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fallback: search by category
    product = db.query(Product).filter(
        Product.category.ilike(f"%{name_or_id}%")
    ).order_by(Product.rating.desc().nullslast()).first()

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}
    return None


async def get_review_stats(
    ctx: RunContext[AgentDependencies],
    product_id: str,
) -> dict:
    """
    Get aggregated review statistics for a product from the database.

    Returns counts by sentiment label, average rating, rating distribution,
    and total review count. This is a fast database query -- no LLM involved.

    Args:
        product_id: Exact product ID (e.g. "PROD001")
    """
    db = ctx.deps.db

    # Sentiment counts
    sentiment_rows = (
        db.query(Review.sentiment, func.count(Review.review_id))
        .filter(Review.product_id == product_id)
        .group_by(Review.sentiment)
        .all()
    )
    sentiment_counts = {row[0]: row[1] for row in sentiment_rows}

    # Rating distribution
    dist_rows = (
        db.query(
            func.floor(Review.rating).label("bucket"),
            func.count(Review.review_id),
        )
        .filter(Review.product_id == product_id)
        .group_by("bucket")
        .all()
    )
    rating_dist = {int(row[0]): row[1] for row in dist_rows}

    # Average rating
    avg_row = (
        db.query(func.avg(Review.rating))
        .filter(Review.product_id == product_id)
        .scalar()
    )
    avg_rating = round(float(avg_row), 2) if avg_row else 0.0

    total = sum(sentiment_counts.values())
    positive = sentiment_counts.get("positive", 0)

    # Sentiment score: proportion of positive reviews on 0-1 scale
    sentiment_score = round(positive / total, 3) if total > 0 else 0.0

    logger.debug("get_review_stats: product=%s total=%d", product_id, total)

    return {
        "product_id": product_id,
        "total_reviews": total,
        "sentiment_counts": sentiment_counts,
        "sentiment_score": sentiment_score,
        "average_rating": avg_rating,
        "rating_distribution": {
            "one_star": rating_dist.get(1, 0),
            "two_star": rating_dist.get(2, 0),
            "three_star": rating_dist.get(3, 0),
            "four_star": rating_dist.get(4, 0),
            "five_star": rating_dist.get(5, 0),
        },
    }


async def get_review_samples(
    ctx: RunContext[AgentDependencies],
    product_id: str,
    max_positive: int = 10,
    max_negative: int = 10,
) -> dict:
    """
    Fetch a sample of review texts for LLM theme extraction.

    Returns up to max_positive positive reviews and max_negative negative reviews,
    ordered by most recent first. Texts are truncated to 200 chars to manage tokens.

    Call this AFTER get_review_stats to get the actual text content for summarisation.

    Args:
        product_id: Exact product ID
        max_positive: Max positive review texts to fetch (default 10)
        max_negative: Max negative review texts to fetch (default 10)
    """
    db = ctx.deps.db

    def fetch_reviews(sentiment: str, limit: int) -> list[str]:
        rows = (
            db.query(Review.text)
            .filter(
                Review.product_id == product_id,
                Review.sentiment == sentiment,
                Review.text.isnot(None),
            )
            .order_by(Review.review_date.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [str(r[0])[:200] for r in rows if r[0]]

    positive_texts = fetch_reviews("positive", max_positive)
    negative_texts = fetch_reviews("negative", max_negative)
    neutral_texts = fetch_reviews("neutral", 5)

    return {
        "product_id": product_id,
        "positive_reviews": positive_texts,
        "negative_reviews": negative_texts,
        "neutral_reviews": neutral_texts,
        "counts": {
            "positive": len(positive_texts),
            "negative": len(negative_texts),
            "neutral": len(neutral_texts),
        },
    }
