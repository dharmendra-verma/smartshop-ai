"""Star rating renderer — half-star precision, WCAG aria-label."""

import math


def render_star_rating_html(rating: float | None,
                             max_stars: int = 5,
                             label: str | None = None) -> str:
    """
    Return an HTML span with filled / half / empty star characters and
    an aria-label for screen-reader accessibility.

    Args:
        rating: float 0–5 (None → returns "N/A")
        max_stars: defaults to 5
        label: optional additional aria description (e.g. product name)

    Returns:
        HTML string safe to use with st.markdown(..., unsafe_allow_html=True)

    Examples:
        render_star_rating_html(4.3) →
            <span class="star-rating" aria-label="4.3 out of 5 stars" role="img">
              ★★★★½☆</span>
    """
    if rating is None:
        return '<span class="star-empty" aria-label="No rating">N/A</span>'

    rating = max(0.0, min(float(rating), float(max_stars)))
    aria = f"{rating:.1f} out of {max_stars} stars"
    if label:
        aria = f"{label}: {aria}"

    stars_html = []
    for i in range(max_stars):
        if rating >= i + 1:
            stars_html.append('<span class="star-filled" aria-hidden="true">★</span>')
        elif rating >= i + 0.5:
            stars_html.append('<span class="star-half"  aria-hidden="true">⯨</span>')
        else:
            stars_html.append('<span class="star-empty" aria-hidden="true">☆</span>')

    inner = "".join(stars_html)
    return (
        f'<span class="star-rating" aria-label="{aria}" role="img">'
        f'{inner}</span>'
    )


def star_rating_text(rating: float | None, max_stars: int = 5) -> str:
    """Plain-text fallback (for emails, tooltips). E.g. '★★★★½☆ (4.3)'"""
    if rating is None:
        return "N/A"
    rating = max(0.0, min(float(rating), float(max_stars)))
    stars = []
    for i in range(max_stars):
        if rating >= i + 1:
            stars.append("★")
        elif rating >= i + 0.5:
            stars.append("½")
        else:
            stars.append("☆")
    return f"{''.join(stars)} ({rating:.1f})"
