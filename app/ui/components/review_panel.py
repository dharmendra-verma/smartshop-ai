"""Inline review panel component — SCRUM-61."""

import streamlit as st
from app.ui.components.star_rating import render_star_rating_html
from app.ui.components.review_display import render_review_summary

REVIEWS_PAGE_SIZE = 10

_SENTIMENT_BADGE = {
    "positive": '<span style="color:#2ca02c;font-weight:600;">Positive</span>',
    "negative": '<span style="color:#d62728;font-weight:600;">Negative</span>',
    "neutral": '<span style="color:#666;font-weight:600;">Neutral</span>',
}


def render_review_panel(product: dict, api_url: str) -> None:
    """
    Render the full-width inline review panel for a selected product.
    Reads/writes session state for pagination and summary cache.
    """
    product_id = product["id"]
    product_name = product.get("name", "Product")
    avg_rating = product.get("rating")
    review_count = product.get("review_count", 0)

    # Panel wrapper
    st.markdown(
        '<div style="background:#f8f9fa;border-top:2px solid #1f77b4;'
        'border-radius:8px;padding:16px;margin-top:16px;">',
        unsafe_allow_html=True,
    )

    # Panel header row
    col_title, col_close = st.columns([5, 1])
    with col_title:
        stars_html = render_star_rating_html(avg_rating)
        st.markdown(
            f"### Reviews for **{product_name}**&nbsp;&nbsp;"
            f"{stars_html}&nbsp;&nbsp;"
            f'<span style="color:#666;font-size:0.9rem;">({review_count} reviews)</span>',
            unsafe_allow_html=True,
        )
    with col_close:

        def _close_panel():
            st.session_state["selected_review_product_id"] = None
            st.session_state["review_panel_offset"] = 0

        st.button(
            "Close Reviews", key=f"close_reviews_{product_id}", on_click=_close_panel
        )

    # AI Summarize button
    summary_cache_key = f"review_summary_{product_id}"
    if summary_cache_key not in st.session_state:
        if st.button(
            "Summarize Reviews with AI",
            key=f"summarize_{product_id}",
            type="secondary",
            use_container_width=True,
        ):
            with st.spinner("Asking AI to summarise all reviews..."):
                from app.ui.api_client import summarize_reviews

                result = summarize_reviews(
                    api_url,
                    query=f"Summarize customer reviews for {product_name}",
                    product_id=product_id,
                    max_reviews=50,
                )
            if result["success"]:
                st.session_state[summary_cache_key] = result["data"]
                st.rerun()
            else:
                st.error(f"Summarization failed: {result['error']}")
    else:
        st.markdown("#### AI Review Summary")
        render_review_summary(st.session_state[summary_cache_key])
        if st.button(
            "Re-summarize",
            key=f"resummarise_{product_id}",
            help="Clear cached summary and fetch a fresh one",
        ):
            del st.session_state[summary_cache_key]
            st.rerun()

    st.divider()

    # Raw reviews list
    from app.ui.api_client import get_product_reviews

    result = get_product_reviews(api_url, product_id, limit=REVIEWS_PAGE_SIZE, offset=0)

    if not result["success"]:
        st.error(f"Could not load reviews: {result['error']}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    data = result["data"]
    reviews = data.get("reviews", [])
    total = data.get("total", 0)

    # Accumulate all loaded reviews in session state for "Load More"
    loaded_key = f"review_loaded_{product_id}"
    if loaded_key not in st.session_state:
        st.session_state[loaded_key] = reviews
    current_reviews = st.session_state[loaded_key]

    if not current_reviews:
        st.info("No reviews yet for this product.")
    else:
        st.caption(f"Showing {len(current_reviews)} of {total} reviews — newest first")
        for rev in current_reviews:
            _render_single_review(rev)

        # Load More
        if len(current_reviews) < total:
            if st.button(
                "Load More Reviews",
                key=f"more_reviews_{product_id}",
                use_container_width=True,
            ):
                next_offset = len(current_reviews)
                more = get_product_reviews(
                    api_url,
                    product_id,
                    limit=REVIEWS_PAGE_SIZE,
                    offset=next_offset,
                )
                if more["success"]:
                    st.session_state[loaded_key].extend(more["data"]["reviews"])
                    st.rerun()
        else:
            if total > 0:
                st.caption(f"All {total} reviews loaded.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_single_review(review: dict) -> None:
    """Render one review card with rating, sentiment, date, and text."""
    rating = review.get("rating", 0)
    sentiment = (review.get("sentiment") or "").lower()
    date_str = review.get("review_date", "")
    text = review.get("text") or "_No review text provided._"

    badge_html = _SENTIMENT_BADGE.get(sentiment, "")
    stars_html = render_star_rating_html(rating)

    st.markdown(
        f'<div class="review-card">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">'
        f"{stars_html}&nbsp;{badge_html}"
        f'<span style="color:#aaa;font-size:0.8rem;margin-left:auto;">{date_str}</span>'
        f"</div>"
        f'<p style="margin:0;font-size:0.9rem;color:#333;">{text}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )
