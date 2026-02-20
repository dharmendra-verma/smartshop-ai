"""SmartShop AI — Streamlit User Interface."""

import os
import streamlit as st

from app.ui.api_client import (
    health_check,
    get_recommendations,
    summarize_reviews,
    search_products,
    compare_prices,
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

from app.ui.design_tokens import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

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

    import uuid
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    
    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        from app.ui.api_client import _post
        _post(f"{api_url}/api/v1/chat/session/{st.session_state['session_id']}", {})
        st.session_state["messages"] = [
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
        st.session_state["session_id"] = str(uuid.uuid4())
        st.rerun()

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
            if msg.get("timestamp"):
                import datetime
                ts = datetime.datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M")
                st.markdown(
                    f'<div class="chat-timestamp">{ts}</div>',
                    unsafe_allow_html=True,
                )

    # Chat input
    if prompt := st.chat_input("Ask me about products or reviews..."):
        import time
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": time.time()})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Route and call API
        from app.ui.api_client import chat as chat_api
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = chat_api(api_url, message=prompt, session_id=st.session_state.get("session_id"), max_results=5)
                if result["success"]:
                    if result["data"].get("session_id"):
                        st.session_state["session_id"] = result["data"]["session_id"]
                    data   = result["data"]
                    intent = data.get("intent", "general")
                    agent_resp = data.get("response", {})
                    if intent == "review":
                        reply = format_review_message(agent_resp)
                    elif intent in ("recommendation", "comparison"):
                        reply = format_recommendation_message(agent_resp)
                    elif intent == "price":
                        best  = agent_resp.get("best_deal", "")
                        rec   = agent_resp.get("recommendation", "")
                        reply = f"🏆 **Best Deal:** {best}\n\n{rec}" if best else rec or "No comparison data."
                    elif intent == "policy":
                        answer  = agent_resp.get("answer", "")
                        sources = ", ".join(f"_{s}_" for s in agent_resp.get("sources", []))
                        reply   = f"{answer}\n\n📋 **Source:** {sources}" if sources else answer
                    else:
                        reply = agent_resp.get("answer", "I'm not sure how to help with that.")
                else:
                    reply = f"⚠️ {result['error']}"
            st.markdown(reply)
            import datetime, time
            st.markdown(
                f'<div class="chat-timestamp">{datetime.datetime.now().strftime("%H:%M")}</div>',
                unsafe_allow_html=True,
            )
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
            "timestamp": time.time()
        })



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

    if not query.strip() and not st.session_state.get("review_submitted"):
        from app.ui.design_tokens import render_empty_state
        st.markdown(
            render_empty_state("⭐", "Enter a product name above to summarise its reviews.",
                               "Try: 'Sony WH-1000XM5' or 'Samsung Galaxy S24'"),
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
            render_empty_state("💰", "Enter a comparison search above.",
                               "Try: 'Compare Samsung S24 and Google Pixel 8'"),
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
                st.info(f"🏆 **Best Deal:** {data['best_deal']}\n\n{data['recommendation']}")

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
                            row[pp["source"]] = f"${pp['price']:,.2f}" + (" ✓" if pp["is_best"] else "")
                        row["Best Price"] = f"${p['best_price']:,.2f} ({p['best_source']})"
                        row["Savings"] = f"{p['savings_pct']:.1f}%" if p["savings_pct"] > 0 else "—"
                        row["Rating"] = f"{'⭐' * round(p['rating'])} ({p['rating']:.1f})" if p.get("rating") else "N/A"
                        row["Cached"] = "♻️" if p.get("is_cached") else "🔴 Live"
                        rows.append(row)

                    df = pd.DataFrame(rows).set_index("Product")
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(result["error"])

# -- Footer --------------------------------------------------------------------
st.divider()
st.caption("SmartShop AI v1.0.0 · Powered by pydantic-ai & FastAPI")
