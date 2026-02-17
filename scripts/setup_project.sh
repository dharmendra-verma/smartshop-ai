#!/bin/bash

# SmartShop AI - Project Setup Script
# This script creates the complete directory structure and placeholder files

echo "🚀 Setting up SmartShop AI project structure..."

# Create main directories
mkdir -p app/{agents,api,core,models,schemas,services,ui/components,utils}
mkdir -p data/{raw,processed,embeddings}
mkdir -p scripts
mkdir -p tests/{test_agents,test_api,test_services}
mkdir -p docs
mkdir -p logs

# Create __init__.py files for Python packages
touch app/__init__.py
touch app/agents/__init__.py
touch app/api/__init__.py
touch app/core/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/ui/__init__.py
touch app/ui/components/__init__.py
touch app/utils/__init__.py

# Create agent files
cat > app/agents/base.py << 'EOF'
"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Standard agent response format."""
    success: bool
    data: Dict[str, Any]
    error: str | None = None
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """Base class for all agents in SmartShop AI."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def process(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """Process a user query and return a response."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
EOF

touch app/agents/orchestrator.py
touch app/agents/recommendation.py
touch app/agents/review.py
touch app/agents/price.py
touch app/agents/policy.py

# Create API files
cat > app/api/health.py << 'EOF'
"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "SmartShop AI",
        "version": "1.0.0"
    }
EOF

touch app/api/products.py
touch app/api/chat.py
touch app/api/agents.py

# Create core configuration files
cat > app/core/config.py << 'EOF'
"""Application configuration management."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "SmartShop AI"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = True

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1500

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
EOF

touch app/core/database.py
touch app/core/cache.py

# Create main FastAPI application
cat > app/main.py << 'EOF'
"""SmartShop AI - Main FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import health

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Driven Multi-Agent E-commerce Assistant",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print(f"👋 Shutting down {settings.APP_NAME}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
EOF

# Create basic Streamlit UI
cat > app/ui/streamlit_app.py << 'EOF'
"""SmartShop AI - Streamlit User Interface."""

import streamlit as st
import requests

# Page configuration
st.set_page_config(
    page_title="SmartShop AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🛒 SmartShop AI")
st.markdown("*Your AI-Powered Shopping Assistant*")

# Sidebar
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Module",
        ["🤖 AI Chat", "🔍 Product Search", "💰 Price Comparison", "⭐ Reviews"]
    )

# Main content area
if page == "🤖 AI Chat":
    st.header("AI Shopping Assistant")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

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

        # TODO: Call FastAPI backend
        with st.chat_message("assistant"):
            response = "I'm being set up! Connect me to the FastAPI backend soon."
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

elif page == "🔍 Product Search":
    st.header("Product Search")
    st.info("Product search functionality coming soon!")

elif page == "💰 Price Comparison":
    st.header("Price Comparison")
    st.info("Price comparison functionality coming soon!")

elif page == "⭐ Reviews":
    st.header("Review Summarization")
    st.info("Review summarization functionality coming soon!")
EOF

# Create .gitkeep files for empty directories
touch data/raw/.gitkeep
touch data/processed/.gitkeep
touch data/embeddings/.gitkeep
touch logs/.gitkeep

# Create test files
cat > tests/test_agents/test_base.py << 'EOF'
"""Tests for base agent class."""

import pytest
from app.agents.base import BaseAgent


def test_base_agent_initialization():
    """Test that BaseAgent cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAgent("test")
EOF

# Create pytest configuration
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
EOF

echo "✅ Project structure created successfully!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your credentials"
echo "2. Run: pip install -r requirements.txt"
echo "3. Run: python scripts/init_db.py (after setting up database)"
echo "4. Run: uvicorn app.main:app --reload"
echo ""
echo "Happy coding! 🚀"
