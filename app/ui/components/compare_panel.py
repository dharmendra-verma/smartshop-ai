"""Inline product comparison panel — SCRUM-62."""

import streamlit as st


def _get_field(product: dict, key: str) -> str:
    """Return a display string for a product field."""
    val = product.get(key)
    if val is None:
        return "—"
    if key == "price":
        return f"${float(val):.2f}"
    if key == "rating":
        return f"{'⭐' * round(float(val))} ({float(val):.1f})"
    if key == "review_count":
        return str(val)
    return str(val)


COMPARE_FIELDS = [
    ("image", "Image"),
    ("name", "Name"),
    ("price", "Price"),
    ("brand", "Brand"),
    ("category", "Category"),
    ("rating", "Rating"),
    ("review_count", "Reviews"),
    ("description", "Description"),
]


def _fetch_review_summary(api_url: str, product: dict) -> dict | None:
    """Return cached or freshly fetched review summary for a product."""
    pid = product.get("id", "")
    cache_key = f"compare_summary_{pid}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        from app.ui.api_client import summarize_reviews

        result = summarize_reviews(
            api_url,
            query=product.get("name", ""),
            product_id=pid or None,
        )
        if result["success"]:
            st.session_state[cache_key] = result["data"]
            return result["data"]
    except Exception:
        pass
    return None


def _fetch_verdict(api_url: str, product_a: dict, product_b: dict) -> str | None:
    """Return cached or freshly fetched AI comparative verdict."""
    id_a = product_a.get("id", "")
    id_b = product_b.get("id", "")
    lo, hi = sorted([id_a, id_b])
    cache_key = f"compare_verdict_{lo}_{hi}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        from app.ui.api_client import chat

        name_a = product_a.get("name", "Product A")
        name_b = product_b.get("name", "Product B")
        prompt = (
            f"Compare these two products and give a concise verdict on which is better and why:\n"
            f"Product 1: {name_a} — ${product_a.get('price', '?')}, "
            f"rating {product_a.get('rating', '?')}/5, {product_a.get('review_count', '?')} reviews. "
            f"{product_a.get('description', '')}\n"
            f"Product 2: {name_b} — ${product_b.get('price', '?')}, "
            f"rating {product_b.get('rating', '?')}/5, {product_b.get('review_count', '?')} reviews. "
            f"{product_b.get('description', '')}"
        )
        result = chat(api_url, message=prompt)
        if result["success"]:
            data = result["data"]
            verdict = data.get("reasoning_summary") or data.get("answer") or ""
            if verdict:
                st.session_state[cache_key] = verdict
                return verdict
    except Exception:
        pass
    return None


def _render_ai_review_summaries(product_a: dict, product_b: dict, api_url: str) -> None:
    """Render side-by-side AI review summaries."""
    st.subheader("AI Review Summaries")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**{product_a.get('name', 'Product A')}**")
        summary_a = _fetch_review_summary(api_url, product_a)
        if summary_a:
            from app.ui.components.review_display import render_review_summary

            render_review_summary(summary_a)
        else:
            st.warning("Could not load review summary.")
    with col_b:
        st.markdown(f"**{product_b.get('name', 'Product B')}**")
        summary_b = _fetch_review_summary(api_url, product_b)
        if summary_b:
            from app.ui.components.review_display import render_review_summary

            render_review_summary(summary_b)
        else:
            st.warning("Could not load review summary.")


def _render_ai_verdict(product_a: dict, product_b: dict, api_url: str) -> None:
    """Render AI comparative verdict."""
    st.subheader("AI Verdict")
    verdict = _fetch_verdict(api_url, product_a, product_b)
    if verdict:
        st.info(verdict)
    else:
        st.warning("Could not generate AI verdict.")


def render_compare_panel(
    product_a: dict, product_b: dict, api_url: str | None = None
) -> None:
    """Render a full-width side-by-side comparison table for two products."""
    st.markdown(
        '<div class="compare-panel-header">📊 Product Comparison</div>',
        unsafe_allow_html=True,
    )

    rows_html = ""
    for field_key, field_label in COMPARE_FIELDS:
        if field_key == "image":
            img_a = product_a.get("image_url") or "https://placehold.co/80x60"
            img_b = product_b.get("image_url") or "https://placehold.co/80x60"
            rows_html += (
                f'<tr class="compare-row">'
                f'<td class="compare-label">{field_label}</td>'
                f'<td class="compare-cell"><img src="{img_a}" class="compare-thumb"/></td>'
                f'<td class="compare-cell"><img src="{img_b}" class="compare-thumb"/></td>'
                f"</tr>"
            )
        else:
            val_a = _get_field(product_a, field_key)
            val_b = _get_field(product_b, field_key)
            diff_class = "compare-row-diff" if val_a != val_b else "compare-row"
            rows_html += (
                f'<tr class="{diff_class}">'
                f'<td class="compare-label">{field_label}</td>'
                f'<td class="compare-cell">{val_a}</td>'
                f'<td class="compare-cell">{val_b}</td>'
                f"</tr>"
            )

    name_a = product_a.get("name", "Product A")
    name_b = product_b.get("name", "Product B")

    table_html = f"""
<div class="compare-panel">
  <table class="compare-table">
    <thead>
      <tr>
        <th class="compare-label">Field</th>
        <th class="compare-cell compare-col-header">{name_a}</th>
        <th class="compare-cell compare-col-header">{name_b}</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  <p class="compare-diff-legend">🟡 Highlighted rows indicate differences</p>
</div>
"""
    st.markdown(table_html, unsafe_allow_html=True)


def render_ai_comparison(product_a: dict, product_b: dict, api_url: str) -> None:
    """Render AI review summaries and verdict for two products."""
    with st.spinner("Generating AI comparison…"):
        _render_ai_review_summaries(product_a, product_b, api_url)
        st.divider()
        _render_ai_verdict(product_a, product_b, api_url)
