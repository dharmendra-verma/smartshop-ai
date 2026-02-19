"""SmartShop AI — Streamlit User Interface."""

import os
import streamlit as st

from app.ui.api_client import (
    health_check,
    get_recommendations,
    summarize_reviews,
    search_products,
)
from app.ui.components.product_card import render_product_grid
from app.ui.components.review_display import render_review_summary
from app.ui.components.chat_helpers import (
    detect_intent,
    format_recommendation_message,
    format_review_message,
)

# -- Config --------------------------------------------------------------------
st.set_page_config(
    page_title="SmartShop AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; }
    .sub-header  { font-size: 1.1rem; color: #666; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# -- Sidebar -------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="main-header">🛒 SmartShop</p>', unsafe_allow_html=True)
    st.caption("AI-Powered Shopping Assistant")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🤖 AI Chat Assistant",
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

# -- Page: AI Chat Assistant ---------------------------------------------------
if page == "🤖 AI Chat Assistant":
    st.header("AI Shopping Assistant")
    st.caption(
        "Ask me to find products or summarize reviews. "
        "Try: _'Show me laptops under $800'_ or _'Summarize reviews for Samsung'_"
    )

    # Initialise chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hi! I'm your AI shopping assistant. I can help you:\n\n"
                    "- 🔍 **Find products** — _'Recommend budget headphones under $100'_\n"
                    "- ⭐ **Summarize reviews** — _'What do customers say about Sony speakers?'_\n\n"
                    "What are you looking for today?"
                ),
            }
        ]

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me about products or reviews..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Route and call API
        # TODO SCRUM-16: Replace detect_intent() with POST /api/v1/chat orchestrator call
        intent = detect_intent(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if intent == "review":
                    result = summarize_reviews(api_url, query=prompt)
                    if result["success"]:
                        reply = format_review_message(result["data"])
                    else:
                        reply = f"⚠️ {result['error']}"
                else:
                    result = get_recommendations(api_url, query=prompt, max_results=5)
                    if result["success"]:
                        reply = format_recommendation_message(result["data"])
                    else:
                        reply = f"⚠️ {result['error']}"
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    # Clear chat button
    if st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state.messages = []
        st.rerun()

# -- Page: Product Search & Recommendations -----------------------------------
elif page == "🔍 Product Search & Recommendations":
    st.header("Product Search & Recommendations")

    tab_search, tab_recommend = st.tabs(["🔍 Filter Search", "🤖 AI Recommendations"])

    # Tab 1: Structured filter search
    with tab_search:
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox(
                "Category",
                ["All", "smartphones", "laptops", "headphones", "speakers", "tablets", "cameras"],
            )
        with col2:
            brand = st.text_input("Brand (optional)", placeholder="e.g. Samsung, Apple")

        if st.button("Search Products", type="primary"):
            with st.spinner("Searching..."):
                result = search_products(
                    api_url,
                    category=category if category != "All" else None,
                    brand=brand or None,
                    page_size=12,
                )
            if result["success"]:
                data = result["data"]
                st.success(f"Found {data['total']} products (showing {len(data['items'])})")
                render_product_grid(data["items"], cols=3)
            else:
                st.error(result["error"])

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

    if st.button("Summarize Reviews", type="primary"):
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
    st.caption("Compare prices and find the best deals.")

    st.info(
        "🚧 **Coming in SCRUM-14** — Price Comparison Agent will provide real-time "
        "pricing data, deal alerts, and side-by-side comparisons. "
        "Use **Product Search & Recommendations** in the meantime to explore products by price range."
    )

    # Preview of what it will look like
    with st.expander("Preview: What Pricing Insights will show"):
        import pandas as pd
        st.dataframe(
            pd.DataFrame({
                "Product": ["Phone A", "Phone B", "Phone C"],
                "Our Price": ["$299", "$349", "$399"],
                "Avg Market": ["$319", "$339", "$419"],
                "Deal Score": ["🔥 Good", "✅ Fair", "⭐ Best"],
                "In Stock": ["Yes", "Yes", "Low"],
            }),
            use_container_width=True,
        )

# -- Footer --------------------------------------------------------------------
st.divider()
st.caption("SmartShop AI v1.0.0 · Powered by pydantic-ai & FastAPI")
