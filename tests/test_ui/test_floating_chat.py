"""Unit tests for floating chat widget (SCRUM-41) — pure HTML/JS generation, no Streamlit."""

import pytest
from app.ui.components.floating_chat import _build_floating_chat_html


@pytest.fixture
def chat_html():
    """Generate the widget HTML once for all tests."""
    return _build_floating_chat_html("http://localhost:8000")


def test_js_creates_chat_button(chat_html):
    assert "smartshop-chat-btn" in chat_html


def test_js_creates_chat_panel(chat_html):
    assert "smartshop-chat-panel" in chat_html


def test_api_url_injected_into_html(chat_html):
    assert "http://localhost:8000" in chat_html


def test_html_contains_aria_labels(chat_html):
    assert "Open AI chat assistant" in chat_html
    assert "AI Chat Assistant" in chat_html
    assert "Chat message input" in chat_html
    assert "Send message" in chat_html
    assert "Close chat" in chat_html


def test_js_creates_close_button(chat_html):
    assert "smartshop-chat-close" in chat_html


def test_js_creates_input_and_send(chat_html):
    assert "smartshop-chat-input" in chat_html
    assert "smartshop-chat-send" in chat_html


def test_html_contains_slide_animation_css(chat_html):
    assert "transition" in chat_html
    assert "right 0.3s ease" in chat_html


def test_html_contains_mobile_media_query(chat_html):
    assert "@media (max-width: 600px)" in chat_html


def test_different_api_url_injected():
    html = _build_floating_chat_html("https://api.example.com")
    assert "https://api.example.com" in html
    assert "/api/v1/chat" in html


def test_injects_into_parent_document(chat_html):
    """Verify the widget injects into parent document, not the iframe."""
    assert "window.parent.document" in chat_html
    assert "parentDoc.body.appendChild" in chat_html


def test_prevents_duplicate_injection(chat_html):
    """Verify the script checks for existing button before re-injecting."""
    assert "getElementById('smartshop-chat-btn')" in chat_html
    assert "return" in chat_html


def test_resize_handle_present(chat_html):
    """Verify the resize handle element and drag logic are included."""
    assert "smartshop-chat-resize" in chat_html
    assert "col-resize" in chat_html
    assert "mousedown" in chat_html
    assert "mousemove" in chat_html


def test_close_button_in_footer(chat_html):
    """Verify the close button is present in the footer bar."""
    assert "smartshop-chat-close" in chat_html
    assert "Close chat" in chat_html
    assert "smartshop-chat-footer" in chat_html


# -- SCRUM-83: Product link tests --


def test_product_link_css_styles(chat_html):
    """Verify product link CSS styles are present."""
    assert ".ss-product-link" in chat_html
    assert "text-decoration: underline" in chat_html
    assert "cursor: pointer" in chat_html


def test_escape_html_utility_present(chat_html):
    """Verify the escapeHtml function is defined."""
    assert "function escapeHtml(text)" in chat_html
    assert "createTextNode" in chat_html


def test_product_link_builder_present(chat_html):
    """Verify the productLink function is defined."""
    assert "function productLink(name, productId)" in chat_html
    assert "ss-product-link" in chat_html
    assert "data-product-id" in chat_html


def test_click_handler_event_delegation(chat_html):
    """Verify click listener on parent document navigates via query param."""
    assert "parentDoc.addEventListener('click'" in chat_html
    assert "closest('.ss-product-link')" in chat_html
    assert "focus_product" in chat_html
    assert "parentWin.location.href" in chat_html


def test_chat_history_saved_on_link_click(chat_html):
    """Verify chat history is saved to sessionStorage before navigation."""
    assert "smartshop_chat_history" in chat_html
    assert "smartshop_chat_open" in chat_html


def test_chat_history_restored_on_init(chat_html):
    """Verify chat history is restored from sessionStorage on init."""
    assert "JSON.parse(savedHistory)" in chat_html


def test_recommendation_uses_product_link(chat_html):
    """Verify recommendation intent formatting uses productLink with id fallback."""
    assert "productLink(name, pid)" in chat_html
    assert "r.product_id || r.id" in chat_html


def test_bot_message_uses_inner_html_for_links(chat_html):
    """Verify bot messages use innerHTML when useHtml is true."""
    assert "useHtml" in chat_html
    assert "botDiv.innerHTML = reply" in chat_html
