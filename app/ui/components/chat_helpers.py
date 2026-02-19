"""Chat intent routing and message formatting helpers."""

# Keyword sets for client-side intent detection
# TODO SCRUM-16: Replace with POST /api/v1/chat once the Orchestrator is live.
_REVIEW_KEYWORDS = {
    "review", "reviews", "summarize", "summary", "opinions",
    "what do customers", "what people say", "feedback", "ratings",
    "pros and cons", "pros cons",
}

_RECOMMENDATION_KEYWORDS = {
    "recommend", "suggest", "find", "show me", "best", "budget",
    "under $", "cheap", "affordable", "top", "popular", "buy",
    "looking for", "want to buy", "gift",
}


def detect_intent(query: str) -> str:
    """
    Detect user intent from a chat query.

    Returns: "review" | "recommendation" | "unknown"

    TODO SCRUM-16: Remove when Orchestrator endpoint is live.
    """
    q = query.lower()
    if any(kw in q for kw in _REVIEW_KEYWORDS):
        return "review"
    if any(kw in q for kw in _RECOMMENDATION_KEYWORDS):
        return "recommendation"
    # Default to recommendation for product-sounding queries
    return "recommendation"


def format_recommendation_message(data: dict) -> str:
    """Format a recommendation API response as markdown for chat display."""
    recs = data.get("recommendations", [])
    if not recs:
        return "I couldn't find any products matching your query. Try broadening your search."

    lines = [f"Here are my top recommendations for **\"{data.get('query', '')}\"**:\n"]
    for i, rec in enumerate(recs, 1):
        price = float(rec.get("price", 0))
        rating = rec.get("rating")
        stars = f"{'⭐' * round(rating)}" if rating else ""
        lines.append(
            f"**{i}. {rec['name']}** — ${price:.2f} {stars}\n"
            f"   _{rec.get('reason', '')}_\n"
        )

    summary = data.get("reasoning_summary", "")
    if summary:
        lines.append(f"\n{summary}")
    return "\n".join(lines)


def format_review_message(data: dict) -> str:
    """Format a review summarization response as markdown for chat display."""
    product_name = data.get("product_name", "this product")
    total = data.get("total_reviews", 0)
    avg = data.get("average_rating", 0)
    score = data.get("sentiment_score", 0)

    pos = data.get("positive_themes", [])
    neg = data.get("negative_themes", [])

    lines = [
        f"**Review Summary: {product_name}**",
        f"_{total} reviews · {avg:.1f}/5.0 avg · {score:.0%} positive sentiment_\n",
    ]
    if pos:
        lines.append("✅ **Top Positives:**")
        for t in pos:
            lines.append(f"  - {t['theme']} ({t['confidence']:.0%} confidence)")
    if neg:
        lines.append("\n❌ **Top Concerns:**")
        for t in neg:
            lines.append(f"  - {t['theme']} ({t['confidence']:.0%} confidence)")

    summary = data.get("overall_summary", "")
    if summary:
        lines.append(f"\n{summary}")
    return "\n".join(lines)
