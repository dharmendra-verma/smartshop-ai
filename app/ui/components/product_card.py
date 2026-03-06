"""Product card and grid rendering components — v2 (SCRUM-18)."""

import streamlit as st
from app.ui.components.star_rating import render_star_rating_html
from app.ui.design_tokens import render_empty_state

PLACEHOLDER_IMG = "https://placehold.co/300x160/f0f4f8/1f77b4?text=No+Image"


def _product_image_url(product: dict) -> str:
    """Return product image URL or placehold.co fallback."""
    return product.get("image_url") or PLACEHOLDER_IMG


def _build_card_html(product: dict) -> str:
    """Build the inner HTML for a product card (everything below the image)."""
    parts: list[str] = []

    # Product name
    name = product.get("name", "Unknown")
    parts.append(f'<div class="card-name"><strong>{name}</strong></div>')

    # Price badge + star rating
    price = product.get("price")
    price_html = (
        f'<span class="price-badge">${float(price):.2f}</span>'
        if price is not None
        else '<span class="price-badge">N/A</span>'
    )
    stars_html = render_star_rating_html(
        product.get("rating"),
        label=name,
        review_count=product.get("review_count"),
    )
    parts.append(f'<div class="card-row">{price_html} &nbsp; {stars_html}</div>')

    # Brand + category
    if product.get("brand"):
        parts.append(
            f'<div class="card-caption">Brand: {product["brand"]}'
            f' · {product.get("category", "")}</div>'
        )

    # Stock indicator
    stock = product.get("stock")
    if stock is not None:
        if stock > 10:
            parts.append(
                f'<div class="card-row stock-badge-ok">✅ In Stock ({stock})</div>'
            )
        elif stock > 0:
            parts.append(
                f'<div class="card-row stock-badge-low">⚠️ Low Stock ({stock})</div>'
            )
        else:
            parts.append('<div class="card-row stock-badge-out">❌ Out of Stock</div>')

    # Description
    if product.get("description"):
        parts.append(f'<p class="product-description">{product["description"]}</p>')

    return "\n".join(parts)


def render_product_card(product: dict) -> None:
    """Render a single product as a styled card — v2."""
    with st.container(border=True):
        # Image — kept as separate st.markdown so Streamlit can handle <img>
        img_url = _product_image_url(product)
        st.markdown(
            f'<img src="{img_url}" class="product-image" '
            f'alt="{product.get("name", "Product image")}" />',
            unsafe_allow_html=True,
        )

        # All card details as a single HTML block — no extra Streamlit spacing
        st.markdown(_build_card_html(product), unsafe_allow_html=True)

        # These use native Streamlit widgets so must stay separate
        if product.get("reason"):
            st.info(f"{product['reason']}")

        if product.get("relevance_score") is not None:
            score = product["relevance_score"]
            st.progress(score, text=f"Relevance: {score:.0%}")

        # Compare checkbox (SCRUM-62)
        product_id = product.get("id", "")
        compare_ids: list = st.session_state.get("compare_product_ids", [])
        is_comparing = product_id in compare_ids

        def _toggle_compare(pid=product_id):
            ids: list = list(st.session_state.get("compare_product_ids", []))
            if pid in ids:
                ids.remove(pid)
                st.session_state["compare_open"] = False
                st.session_state["compare_ai_open"] = False
            else:
                if len(ids) >= 2:
                    ids.pop(0)  # FIFO: remove oldest selection
                ids.append(pid)
            st.session_state["compare_product_ids"] = ids

        st.checkbox(
            "⚖️ Compare",
            value=is_comparing,
            key=f"compare_{product_id}",
            on_change=_toggle_compare,
        )

        # Clickable reviews button (SCRUM-61)
        review_count = product.get("review_count", 0)
        if review_count and review_count > 0:
            is_selected = (
                st.session_state.get("selected_review_product_id") == product_id
            )
            plural = "s" if review_count != 1 else ""
            btn_label = (
                f"{'Open' if not is_selected else 'Hide'} {review_count} review{plural}"
            )
            btn_style = "primary" if is_selected else "secondary"

            def _toggle_reviews(pid=product_id, currently_selected=is_selected):
                if currently_selected:
                    st.session_state["selected_review_product_id"] = None
                    st.session_state.pop(f"review_loaded_{pid}", None)
                else:
                    st.session_state["selected_review_product_id"] = pid
                    st.session_state.pop(f"review_loaded_{pid}", None)

            st.button(
                btn_label,
                key=f"show_reviews_{product_id}",
                type=btn_style,
                use_container_width=True,
                on_click=_toggle_reviews,
            )
        else:
            st.caption("No reviews yet")


def render_product_grid(products: list[dict], cols: int = 3) -> None:
    """Render a grid of product cards with an empty state if none found."""
    if not products:
        st.markdown(
            render_empty_state(
                icon="🔍",
                message="No products found matching your criteria.",
                hint="Try broadening your search or removing filters.",
            ),
            unsafe_allow_html=True,
        )
        return

    columns = st.columns(cols)
    for i, product in enumerate(products):
        with columns[i % cols]:
            render_product_card(product)
