"""Product card and grid rendering components — v2 (SCRUM-18)."""

import streamlit as st
from app.ui.components.star_rating import render_star_rating_html
from app.ui.design_tokens import render_empty_state

PLACEHOLDER_IMG = "https://placehold.co/300x160/f0f4f8/1f77b4?text=No+Image"


def _product_image_url(product: dict) -> str:
    """Return product image URL or placehold.co fallback."""
    return product.get("image_url") or PLACEHOLDER_IMG


def render_product_card(product: dict) -> None:
    """Render a single product as a styled card — v2."""
    with st.container(border=True):
        # Image
        img_url = _product_image_url(product)
        st.markdown(
            f'<img src="{img_url}" class="product-image" '
            f'alt="{product.get("name", "Product image")}" />',
            unsafe_allow_html=True,
        )

        st.markdown(f"**{product.get('name', 'Unknown')}**")

        # Price badge + star rating side by side
        price = product.get("price")
        rating = product.get("rating")
        price_html = (
            f'<span class="price-badge">${float(price):.2f}</span>'
            if price is not None
            else '<span class="price-badge">N/A</span>'
        )
        stars_html = render_star_rating_html(rating, label=product.get("name"))
        st.markdown(f"{price_html} &nbsp; {stars_html}", unsafe_allow_html=True)

        if product.get("brand"):
            st.caption(f"Brand: {product['brand']} · {product.get('category', '')}")

        # Stock indicator
        stock = product.get("stock")
        if stock is not None:
            if stock > 10:
                st.markdown(
                    f'<span class="stock-badge-ok">✅ In Stock ({stock})</span>',
                    unsafe_allow_html=True,
                )
            elif stock > 0:
                st.markdown(
                    f'<span class="stock-badge-low">⚠️ Low Stock ({stock})</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span class="stock-badge-out">❌ Out of Stock</span>',
                    unsafe_allow_html=True,
                )

        if product.get("reason"):
            st.info(f"{product['reason']}")

        if product.get("relevance_score") is not None:
            score = product["relevance_score"]
            st.progress(score, text=f"Relevance: {score:.0%}")


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
