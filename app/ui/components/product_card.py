"""Product card and grid rendering components."""

import streamlit as st


def render_product_card(product: dict) -> None:
    """Render a single product as a styled card."""
    with st.container(border=True):
        st.markdown(f"**{product.get('name', 'Unknown')}**")

        col1, col2 = st.columns(2)
        with col1:
            price = product.get("price")
            st.metric("Price", f"${float(price):.2f}" if price else "N/A")
        with col2:
            rating = product.get("rating")
            st.metric("Rating", f"{'⭐' * round(rating)} ({rating:.1f})" if rating else "N/A")

        if product.get("brand"):
            st.caption(f"Brand: {product['brand']} · Category: {product.get('category', '')}")

        stock = product.get("stock")
        if stock is not None:
            if stock > 10:
                st.success(f"In Stock ({stock} units)")
            elif stock > 0:
                st.warning(f"Low Stock ({stock} units)")
            else:
                st.error("Out of Stock")

        if product.get("reason"):
            st.info(f"{product['reason']}")

        if product.get("relevance_score") is not None:
            score = product["relevance_score"]
            st.progress(score, text=f"Relevance: {score:.0%}")


def render_product_grid(products: list[dict], cols: int = 3) -> None:
    """Render a grid of product cards."""
    if not products:
        st.info("No products found matching your criteria.")
        return

    columns = st.columns(cols)
    for i, product in enumerate(products):
        with columns[i % cols]:
            render_product_card(product)
