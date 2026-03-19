"""Tools for the Review Summarization Agent."""

import logging
from pydantic_ai import RunContext
from sqlalchemy import func, case, literal
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
    product = (
        db.query(Product)
        .filter(Product.name.ilike(f"%{name_or_id}%"))
        .order_by(Product.rating.desc().nullslast())
        .first()
    )

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fallback: search by brand
    product = (
        db.query(Product)
        .filter(Product.brand.ilike(f"%{name_or_id}%"))
        .order_by(Product.rating.desc().nullslast())
        .first()
    )

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fallback: search by category
    product = (
        db.query(Product)
        .filter(Product.category.ilike(f"%{name_or_id}%"))
        .order_by(Product.rating.desc().nullslast())
        .first()
    )

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

    # Single aggregation query for all stats
    row = (
        db.query(
            func.count(Review.review_id).label("total"),
            func.avg(Review.rating).label("avg_rating"),
            func.sum(case((Review.sentiment == "positive", 1), else_=0)).label(
                "positive"
            ),
            func.sum(case((Review.sentiment == "negative", 1), else_=0)).label(
                "negative"
            ),
            func.sum(case((Review.sentiment == "neutral", 1), else_=0)).label(
                "neutral"
            ),
            func.sum(
                case((func.floor(Review.rating) == literal(1), 1), else_=0)
            ).label("star_1"),
            func.sum(
                case((func.floor(Review.rating) == literal(2), 1), else_=0)
            ).label("star_2"),
            func.sum(
                case((func.floor(Review.rating) == literal(3), 1), else_=0)
            ).label("star_3"),
            func.sum(
                case((func.floor(Review.rating) == literal(4), 1), else_=0)
            ).label("star_4"),
            func.sum(
                case((func.floor(Review.rating) == literal(5), 1), else_=0)
            ).label("star_5"),
        )
        .filter(Review.product_id == product_id)
        .first()
    )

    total = int(row.total) if row and row.total else 0
    avg_rating = round(float(row.avg_rating), 2) if row and row.avg_rating else 0.0
    positive = int(row.positive) if row and row.positive else 0
    negative = int(row.negative) if row and row.negative else 0
    neutral = int(row.neutral) if row and row.neutral else 0
    sentiment_counts = {"positive": positive, "negative": negative, "neutral": neutral}
    rating_dist = {
        i: int(getattr(row, f"star_{i}") or 0) if row else 0 for i in range(1, 6)
    }

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

    # Single query with row_number window to fetch all sentiments at once
    max_per_sentiment = max(max_positive, max_negative, 5)
    rows = (
        db.query(Review.text, Review.sentiment)
        .filter(
            Review.product_id == product_id,
            Review.sentiment.in_(["positive", "negative", "neutral"]),
            Review.text.isnot(None),
        )
        .order_by(Review.sentiment, Review.review_date.desc().nullslast())
        .limit(max_per_sentiment * 3)
        .all()
    )

    # Split results by sentiment with per-sentiment limits
    limits = {"positive": max_positive, "negative": max_negative, "neutral": 5}
    buckets: dict[str, list[str]] = {"positive": [], "negative": [], "neutral": []}
    for text, sentiment in rows:
        if text and sentiment in buckets and len(buckets[sentiment]) < limits[sentiment]:
            buckets[sentiment].append(str(text)[:200])

    positive_texts = buckets["positive"]
    negative_texts = buckets["negative"]
    neutral_texts = buckets["neutral"]

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
