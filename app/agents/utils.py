"""Shared utilities for agent query building."""


def build_recommendation_query(query: str, hints: dict, max_results: int) -> str:
    """Build enriched query string for the RecommendationAgent."""
    parts = [query]
    if hints.get("max_price"):
        parts.append(f"Maximum price: ${hints['max_price']}")
    if hints.get("min_price"):
        parts.append(f"Minimum price: ${hints['min_price']}")
    if hints.get("category"):
        parts.append(f"Category: {hints['category']}")
    if hints.get("min_rating"):
        parts.append(f"Minimum rating: {hints['min_rating']}/5")
    parts.append(f"Return top {max_results} recommendations.")
    return "\n".join(parts)


def build_review_query(query: str, product_id: str | None, max_reviews: int) -> str:
    """Build enriched query string for the ReviewSummarizationAgent."""
    parts = [query]
    if product_id:
        parts.append(f"Product ID (use directly, skip find_product): {product_id}")
    parts.append(
        f"Fetch up to {max_reviews // 2} positive and {max_reviews // 2} negative reviews."
    )
    return "\n".join(parts)
