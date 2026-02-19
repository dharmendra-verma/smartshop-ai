"""Review summarization display components."""

import streamlit as st


def render_sentiment_themes(themes: list[dict], label: str, emoji: str) -> None:
    """Render a list of sentiment themes with confidence bars."""
    st.markdown(f"**{emoji} {label}**")
    if not themes:
        st.caption("No themes identified.")
        return
    for theme in themes:
        confidence = theme.get("confidence", 0)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(confidence, text=theme.get("theme", ""))
        with col2:
            st.caption(f"{confidence:.0%}")
        if theme.get("example_quote"):
            st.caption(f'_"{theme["example_quote"]}"_')


def render_rating_distribution(dist: dict) -> None:
    """Render star rating distribution as a horizontal bar chart."""
    st.markdown("**Rating Distribution**")
    labels = ["5 star", "4 star", "3 star", "2 star", "1 star"]
    keys = ["five_star", "four_star", "three_star", "two_star", "one_star"]
    total = sum(dist.get(k, 0) for k in keys) or 1
    for label, key in zip(labels, keys):
        count = dist.get(key, 0)
        pct = count / total
        st.progress(pct, text=f"{label}  ({count})")


def render_review_summary(data: dict) -> None:
    """Render a full review summarization response."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reviews", data.get("total_reviews", 0))
    with col2:
        score = data.get("sentiment_score", 0)
        st.metric("Sentiment Score", f"{score:.2f}/1.0")
    with col3:
        avg = data.get("average_rating", 0)
        st.metric("Avg Rating", f"{avg:.1f}/5.0")

    if data.get("cached"):
        st.caption("Served from cache")

    st.divider()
    col_pos, col_neg = st.columns(2)
    with col_pos:
        render_sentiment_themes(data.get("positive_themes", []), "Positive Themes", "✅")
    with col_neg:
        render_sentiment_themes(data.get("negative_themes", []), "Negative Themes", "❌")

    st.divider()
    render_rating_distribution(data.get("rating_distribution", {}))

    st.divider()
    st.markdown("**Overall Summary**")
    st.write(data.get("overall_summary", "No summary available."))
