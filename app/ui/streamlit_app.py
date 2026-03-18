"""SmartShop AI — Streamlit User Interface."""

import os
import sys

# Ensure project root is on sys.path so 'app' package is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st  # noqa: E402

from app.ui.api_client import (  # noqa: E402
    health_check,
    get_categories,
    get_recommendations,
    summarize_reviews,
    search_products,
    compare_prices,
)
from app.ui.components.product_card import render_product_grid  # noqa: E402
from app.ui.components.review_display import render_review_summary  # noqa: E402
from app.ui.components.floating_chat import render_floating_chat_widget  # noqa: E402

# -- Config --------------------------------------------------------------------
st.set_page_config(
    page_title="SmartShop AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.ui.design_tokens import get_global_css  # noqa: E402

st.markdown(get_global_css(), unsafe_allow_html=True)

# -- Sidebar -------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="main-header">🛒 SmartShop</p>', unsafe_allow_html=True)
    st.caption("AI-Powered Shopping Assistant")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🔍 Product Search & Recommendations",
            "⭐ Review Summarization",
            "💰 Pricing Insights",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("⚙️ Settings")
    # Read from env var (Docker) or allow manual override
    default_url = os.getenv("API_URL", "http://localhost:8080")
    api_url = st.text_input("API URL", default_url)

    # Backend status indicator
    if health_check(api_url):
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend unreachable")
        st.caption(f"Ensure FastAPI is running at {api_url}")

    import uuid

    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())


# -- Page: Product Search & Recommendations -----------------------------------
if page == "🔍 Product Search & Recommendations":
    st.header("Product Search & Recommendations")

    tab_search, tab_recommend = st.tabs(["🔍 Filter Search", "🤖 AI Recommendations"])

    # Tab 1: Structured filter search
    PRODUCTS_BATCH_SIZE = 24

    def _init_search_state():
        for key, default in [
            ("search_products_list", []),
            ("search_page", 0),
            ("search_total", 0),
            ("search_total_pages", 0),
            ("search_params", {}),
            ("selected_review_product_id", None),
            ("review_panel_offset", 0),
            ("compare_product_ids", []),
            ("compare_open", False),
            ("compare_ai_open", False),
        ]:
            if key not in st.session_state:
                st.session_state[key] = default

    with tab_search:
        _init_search_state()

        col1, col2 = st.columns(2)
        with col1:
            categories = st.session_state.get("_categories_cache")
            if categories is None:
                categories = get_categories(api_url)
                st.session_state["_categories_cache"] = categories
            category = st.selectbox("Category", ["All"] + categories)
        with col2:
            brand = st.text_input(
                "Name / Brand", placeholder="e.g. Samsung, Galaxy S24, Apple"
            )

        if st.button("Search Products", type="primary"):
            params = {
                "category": category if category != "All" else None,
                "brand": brand or None,
            }
            st.session_state["search_products_list"] = []
            st.session_state["search_page"] = 0
            st.session_state["search_total"] = 0
            st.session_state["search_total_pages"] = 0
            st.session_state["search_params"] = params
            with st.spinner("Searching..."):
                result = search_products(
                    api_url,
                    category=params["category"],
                    brand=params["brand"],
                    page=1,
                    page_size=PRODUCTS_BATCH_SIZE,
                )
            if result["success"]:
                data = result["data"]
                st.session_state["search_products_list"] = data["items"]
                st.session_state["search_page"] = 1
                st.session_state["search_total"] = data["total"]
                st.session_state["search_total_pages"] = data["pages"]
            else:
                st.error(result["error"])

        # Display accumulated results
        products = st.session_state.get("search_products_list", [])
        total = st.session_state.get("search_total", 0)
        cur_page = st.session_state.get("search_page", 0)
        tot_pages = st.session_state.get("search_total_pages", 0)

        if products:
            shown = len(products)
            st.markdown(
                f'<p class="product-count-header">Showing <strong>1–{shown}</strong> of '
                f"<strong>{total}</strong> products</p>",
                unsafe_allow_html=True,
            )

            # Inline review panel — rendered ABOVE the grid so it's visible (SCRUM-61)
            selected_id = st.session_state.get("selected_review_product_id")
            if selected_id:
                selected_product = next(
                    (p for p in products if p.get("id") == selected_id),
                    None,
                )
                if selected_product:
                    from app.ui.components.review_panel import render_review_panel

                    render_review_panel(selected_product, api_url)
                else:
                    st.session_state["selected_review_product_id"] = None

            # Compare action bar + panel — above grid (SCRUM-62)
            compare_ids = st.session_state.get("compare_product_ids", [])
            if compare_ids:
                compare_products = [p for p in products if p.get("id") in compare_ids]
                n = len(compare_ids)

                bar_col1, bar_col2, bar_col3 = st.columns([4, 2, 2])
                with bar_col1:
                    names = " vs ".join(
                        p.get("name", "?")[:30] for p in compare_products
                    )
                    st.markdown(
                        f'<div class="compare-action-bar">⚖️ Comparing: <strong>{names}</strong></div>',
                        unsafe_allow_html=True,
                    )
                with bar_col2:
                    if st.button(
                        f"Compare Products ({n}/2)",
                        type="primary",
                        disabled=(n < 2),
                        use_container_width=True,
                    ):
                        st.session_state["compare_open"] = True
                        st.rerun()
                with bar_col3:
                    if st.button("✕ Clear Selection", use_container_width=True):
                        st.session_state["compare_product_ids"] = []
                        st.session_state["compare_open"] = False
                        st.session_state["compare_ai_open"] = False
                        st.rerun()

                if st.session_state.get("compare_open") and len(compare_products) == 2:
                    from app.ui.components.compare_panel import (
                        render_compare_panel,
                        render_ai_comparison,
                    )

                    with st.container():
                        render_compare_panel(compare_products[0], compare_products[1])
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button(
                                "🤖 AI Compare",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state["compare_ai_open"] = True
                                st.rerun()
                        with btn_col2:
                            if st.button(
                                "✕ Close Comparison", use_container_width=True
                            ):
                                st.session_state["compare_open"] = False
                                st.session_state["compare_ai_open"] = False
                                st.rerun()
                        if st.session_state.get("compare_ai_open"):
                            st.divider()
                            render_ai_comparison(
                                compare_products[0], compare_products[1], api_url
                            )
                elif st.session_state.get("compare_open") and len(compare_products) < 2:
                    st.info("Please select a second product to compare.")

            render_product_grid(products, cols=3)

            if cur_page < tot_pages:
                if st.button("Load More Products", use_container_width=True):
                    next_page = cur_page + 1
                    params = st.session_state.get("search_params", {})
                    with st.spinner("Loading more products..."):
                        result = search_products(
                            api_url,
                            category=params.get("category"),
                            brand=params.get("brand"),
                            page=next_page,
                            page_size=PRODUCTS_BATCH_SIZE,
                        )
                    if result["success"]:
                        data = result["data"]
                        st.session_state["search_products_list"].extend(data["items"])
                        st.session_state["search_page"] = next_page
                        st.rerun()
                    else:
                        st.error(result["error"])
            elif cur_page > 0 and cur_page >= tot_pages:
                st.success(f"All {total} products loaded.")

    # Tab 2: AI recommendation
    with tab_recommend:
        nl_query = st.text_input(
            "Describe what you're looking for",
            placeholder="e.g. 'best wireless headphones for gym use under $150'",
        )
        max_results = st.slider("Number of recommendations", 1, 10, 5)

        if st.button("Get AI Recommendations", type="primary"):
            if not nl_query.strip():
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Finding the best matches for you..."):
                    result = get_recommendations(
                        api_url, query=nl_query, max_results=max_results
                    )
                if result["success"]:
                    data = result["data"]
                    st.success(f"Found {data['total_found']} recommendation(s)")
                    if data.get("reasoning_summary"):
                        st.info(f"💡 {data['reasoning_summary']}")
                    render_product_grid(data["recommendations"], cols=3)
                else:
                    st.error(result["error"])

# -- Page: Review Summarization ------------------------------------------------
elif page == "⭐ Review Summarization":
    st.header("Review Summarization")
    st.caption("Get AI-powered summaries of what customers say about any product.")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Product name or question",
            placeholder="e.g. 'Summarize reviews for Sony WH-1000XM5'",
        )
    with col2:
        product_id = st.text_input("Product ID (optional)", placeholder="e.g. PROD001")

    max_reviews = st.slider("Reviews to analyse", 5, 50, 20, step=5)

    if not query.strip() and not st.session_state.get("review_submitted"):
        from app.ui.design_tokens import render_empty_state

        st.markdown(
            render_empty_state(
                "⭐",
                "Enter a product name above to summarise its reviews.",
                "Try: 'Sony WH-1000XM5' or 'Samsung Galaxy S24'",
            ),
            unsafe_allow_html=True,
        )
    elif st.button("Summarize Reviews", type="primary"):
        if not query.strip():
            st.warning("Please enter a product name or question.")
        else:
            with st.spinner("Analysing customer reviews..."):
                result = summarize_reviews(
                    api_url,
                    query=query,
                    product_id=product_id.strip() or None,
                    max_reviews=max_reviews,
                )
            if result["success"]:
                data = result["data"]
                st.subheader(f"Reviews for: **{data.get('product_name', query)}**")
                render_review_summary(data)
            else:
                st.error(result["error"])

# -- Page: Pricing Insights ----------------------------------------------------
elif page == "💰 Pricing Insights":
    st.header("Pricing Insights")
    st.caption(
        "Compare prices across Amazon, BestBuy, and Walmart to find the best deal."
    )

    query = st.text_input(
        "What would you like to compare?",
        placeholder="e.g. 'Compare Samsung S24 and Google Pixel 8'",
    )
    max_results = st.slider("Max products to compare", 2, 6, 4)

    if not query.strip():
        from app.ui.design_tokens import render_empty_state

        st.markdown(
            render_empty_state(
                "💰",
                "Enter a comparison search above.",
                "Try: 'Compare Samsung S24 and Google Pixel 8'",
            ),
            unsafe_allow_html=True,
        )
    elif st.button("Compare Prices", type="primary"):
        if not query.strip():
            st.warning("Please enter a comparison query.")
        else:
            with st.spinner("Fetching prices from multiple sources..."):
                result = compare_prices(api_url, query=query, max_results=max_results)

            if result["success"]:
                data = result["data"]
                st.success(f"Compared **{data['total_compared']}** products")

                # Best deal highlight
                st.info(
                    f"🏆 **Best Deal:** {data['best_deal']}\n\n{data['recommendation']}"
                )

                # Side-by-side comparison table
                if data["products"]:
                    import pandas as pd

                    # Build comparison DataFrame
                    rows = []
                    for p in data["products"]:
                        row = {
                            "Product": p["name"],
                            "SmartShop": f"${p['our_price']:,.2f}",
                        }
                        for pp in p["competitor_prices"]:
                            row[pp["source"]] = f"${pp['price']:,.2f}" + (
                                " ✓" if pp["is_best"] else ""
                            )
                        row["Best Price"] = (
                            f"${p['best_price']:,.2f} ({p['best_source']})"
                        )
                        row["Savings"] = (
                            f"{p['savings_pct']:.1f}%" if p["savings_pct"] > 0 else "—"
                        )
                        row["Rating"] = (
                            f"{'⭐' * round(p['rating'])} ({p['rating']:.1f})"
                            if p.get("rating")
                            else "N/A"
                        )
                        row["Cached"] = "♻️" if p.get("is_cached") else "🔴 Live"
                        rows.append(row)

                    df = pd.DataFrame(rows).set_index("Product")
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(result["error"])

# -- Floating Chat Widget (available on all pages) ----------------------------
render_floating_chat_widget(api_url)

# -- Footer --------------------------------------------------------------------
st.divider()
st.caption("SmartShop AI v1.0.0 · Powered by pydantic-ai & FastAPI")
