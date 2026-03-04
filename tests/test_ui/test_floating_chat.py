"""Unit tests for floating chat widget (SCRUM-41) — pure HTML generation, no Streamlit."""

import pytest
from app.ui.components.floating_chat import _build_floating_chat_html


@pytest.fixture
def chat_html():
    """Generate the widget HTML once for all tests."""
    return _build_floating_chat_html("http://localhost:8000")


def test_html_contains_chat_button(chat_html):
    assert 'id="smartshop-chat-btn"' in chat_html


def test_html_contains_chat_panel(chat_html):
    assert 'id="smartshop-chat-panel"' in chat_html


def test_api_url_injected_into_html(chat_html):
    assert "http://localhost:8000" in chat_html


def test_html_contains_aria_labels(chat_html):
    assert 'aria-label="Open AI chat assistant"' in chat_html
    assert 'aria-label="AI Chat Assistant"' in chat_html
    assert 'aria-label="Chat message input"' in chat_html
    assert 'aria-label="Send message"' in chat_html
    assert 'aria-label="Close chat"' in chat_html


def test_html_contains_close_button(chat_html):
    assert 'id="smartshop-chat-close"' in chat_html


def test_html_contains_input_and_send(chat_html):
    assert 'id="smartshop-chat-input"' in chat_html
    assert 'id="smartshop-chat-send"' in chat_html


def test_html_contains_slide_animation_css(chat_html):
    assert "transition" in chat_html
    assert "right 0.3s ease" in chat_html


def test_html_contains_mobile_media_query(chat_html):
    assert "@media (max-width: 600px)" in chat_html


def test_different_api_url_injected():
    html = _build_floating_chat_html("https://api.example.com")
    assert "https://api.example.com" in html
    assert "/api/v1/chat" in html
