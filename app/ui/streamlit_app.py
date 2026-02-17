"""SmartShop AI - Streamlit User Interface."""

import streamlit as st
import requests
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SmartShop AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🛒 SmartShop AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your AI-Powered Shopping Assistant</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📋 Navigation")
    page = st.radio(
        "Select Module",
        ["🤖 AI Chat Assistant", "🔍 Product Search", "💰 Price Comparison", "⭐ Review Summarization"],
        label_visibility="collapsed"
    )

    st.divider()

    st.subheader("⚙️ Settings")
    api_url = st.text_input("API URL", "http://localhost:8000", help="FastAPI backend URL")

    st.divider()

    # Connection status
    try:
        response = requests.get(f"{api_url}/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ Connected to backend")
        else:
            st.error("❌ Backend not responding")
    except:
        st.warning("⚠️ Cannot connect to backend")
        st.caption("Make sure FastAPI is running on port 8000")

# Main content area
if page == "🤖 AI Chat Assistant":
    st.header("AI Shopping Assistant")
    st.caption("Ask me anything about products, prices, reviews, or store policies!")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Hi! I'm your AI shopping assistant. I can help you discover products, compare prices, summarize reviews, and answer policy questions. What are you looking for today?"
        }]

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about products..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # TODO: Call FastAPI backend once agents are implemented
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Placeholder response - replace with actual API call
                response = f"I received your query: '{prompt}'. Once the backend agents are implemented, I'll provide intelligent responses!"
                st.markdown(response)
                st.info("💡 **Next Steps:** Implement the agent endpoints in FastAPI to enable real AI responses.")

            st.session_state.messages.append({"role": "assistant", "content": response})

elif page == "🔍 Product Search":
    st.header("Product Search")

    col1, col2, col3 = st.columns(3)

    with col1:
        category = st.selectbox("Category", ["All", "Electronics", "Clothing", "Home & Kitchen", "Books"])

    with col2:
        min_price = st.number_input("Min Price ($)", min_value=0, value=0)

    with col3:
        max_price = st.number_input("Max Price ($)", min_value=0, value=1000)

    search_query = st.text_input("🔍 Search for products...")

    if st.button("Search", type="primary"):
        st.info("🚧 Product search functionality coming soon! Connect to the Product Recommendation Agent.")

elif page == "💰 Price Comparison":
    st.header("Price Comparison")
    st.write("Compare prices across multiple retailers")

    product_input = st.text_input("Enter product name or ID")

    if st.button("Compare Prices", type="primary"):
        st.info("🚧 Price comparison functionality coming soon! Connect to the Price Comparison Agent.")

    # Placeholder comparison table
    with st.expander("Example: How it will look"):
        import pandas as pd
        example_data = {
            "Retailer": ["Amazon", "Walmart", "Best Buy", "Target"],
            "Price": ["$299.99", "$289.99", "$309.99", "$295.99"],
            "Availability": ["In Stock", "In Stock", "Out of Stock", "Limited"],
            "Rating": ["4.5⭐", "4.3⭐", "4.6⭐", "4.4⭐"]
        }
        st.dataframe(pd.DataFrame(example_data), use_container_width=True)

elif page == "⭐ Review Summarization":
    st.header("Review Summarization")
    st.write("Get AI-powered summaries of customer reviews")

    product_id = st.text_input("Enter product name or ID")

    if st.button("Summarize Reviews", type="primary"):
        st.info("🚧 Review summarization functionality coming soon! Connect to the Review Summarization Agent.")

    # Placeholder summary
    with st.expander("Example: How it will look"):
        st.subheader("Positive Themes")
        st.write("✅ Great build quality (confidence: 85%)")
        st.write("✅ Easy to use (confidence: 78%)")
        st.write("✅ Good value for money (confidence: 72%)")

        st.subheader("Negative Themes")
        st.write("❌ Battery life could be better (confidence: 65%)")
        st.write("❌ Customer service issues (confidence: 58%)")

        st.metric("Overall Sentiment", "4.2/5.0", "+0.3")

# Footer
st.divider()
st.caption(f"SmartShop AI v1.0.0 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.caption("🤖 Powered by Claude Sonnet 4.5 & FastAPI")
