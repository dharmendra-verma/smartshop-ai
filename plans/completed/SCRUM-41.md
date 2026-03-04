# SCRUM-41 — Floating Chat Assistant Widget with Slide-in Chat Window

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-41
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a shopper on the e-commerce site, I want a floating chat assistant icon always visible on the page, so that I can quickly get help or ask questions without navigating away from what I'm browsing.

---

## Acceptance Criteria

- [ ] A floating circular chat icon is fixed at the bottom-right corner of every page
- [ ] The icon is visible across all pages (product listing, product detail, cart, checkout) and does not overlap critical UI elements
- [ ] Clicking the chat icon opens a chat window that slides in from the right side of the screen
- [ ] The chat window does not navigate away from the current page — it overlays as a side panel
- [ ] The chat window has a close/collapse button (X) that dismisses it and returns to the floating icon state
- [ ] The chat window retains conversation history within the same session (does not reset on minimise)
- [ ] On mobile, the chat window takes full width for usability
- [ ] The floating icon has a subtle animation (pulse or bounce) on first load, stopping after first interaction
- [ ] Accessibility: button has aria-label, keyboard navigable, chat window is screen-reader friendly

---

## Current State

- Chat assistant currently lives as a dedicated page/tab in the sidebar navigation (`🤖 AI Chat Assistant`)
- `streamlit_app.py` routes between pages via `st.radio` in the sidebar
- `app/ui/components/chat_helpers.py` contains `detect_intent`, `format_recommendation_message`, `format_review_message`
- `app/ui/api_client.py` has a `chat(api_url, message, session_id, max_results)` function ready
- Session ID is stored in `st.session_state["session_id"]`
- `design_tokens.py` defines `COLOR_BRAND_PRIMARY = "#1f77b4"` — use for icon background

---

## Technical Approach

Streamlit does not support true CSS `position: fixed` overlays out-of-the-box, but we can inject a fully self-contained floating widget using `st.components.v1.html()` with JavaScript + `window.parent.postMessage` for Streamlit<→iframe communication, or — more practically — inject the floating button + chat panel entirely via `st.markdown(..., unsafe_allow_html=True)` with `<style>` + `<script>` HTML, and use Streamlit's session state + `st.rerun()` to toggle open/closed state.

**Chosen approach:** Pure HTML/CSS/JS injected via `st.markdown` into `streamlit_app.py`. The widget calls the FastAPI `/api/v1/chat` endpoint directly via `fetch()` in JavaScript to avoid Streamlit re-renders on every message (smoother UX). Session ID is created in JS and stored in `sessionStorage`.

### Architecture

```
app/ui/components/floating_chat.py       ← NEW file
    render_floating_chat_widget(api_url) → injects the full widget HTML
    _build_floating_chat_html(api_url)   → returns complete HTML string

app/ui/streamlit_app.py                  ← MODIFY
    + import render_floating_chat_widget
    + call render_floating_chat_widget(api_url) near end of file
      (after all page content, before footer)

app/ui/design_tokens.py                  ← MODIFY (additive)
    + floating chat CSS tokens added to get_global_css()
```

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `app/ui/components/floating_chat.py` | CREATE | New component with full floating widget |
| `app/ui/streamlit_app.py` | MODIFY | Import and call `render_floating_chat_widget(api_url)` |
| `app/ui/design_tokens.py` | MODIFY | Add `.floating-chat-*` CSS classes |
| `tests/test_ui/test_floating_chat.py` | CREATE | Unit tests for HTML generation |

---

## Code Snippets

### `app/ui/components/floating_chat.py`

```python
"""Floating chat assistant widget — SCRUM-41."""

import streamlit as st


def render_floating_chat_widget(api_url: str) -> None:
    """Inject floating chat button + slide-in panel into the page."""
    html = _build_floating_chat_html(api_url)
    st.markdown(html, unsafe_allow_html=True)


def _build_floating_chat_html(api_url: str) -> str:
    """Return self-contained HTML/CSS/JS for the floating chat widget."""
    return f"""
<style>
/* Floating Chat Button */
#smartshop-chat-btn {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #1f77b4;
    color: #fff;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(31,119,180,0.4);
    font-size: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    animation: chatPulse 2s ease-in-out 3;
    transition: transform 0.15s ease;
    aria-label: "Open chat assistant";
}}
#smartshop-chat-btn:hover {{ transform: scale(1.1); }}
@keyframes chatPulse {{
    0%, 100% {{ box-shadow: 0 4px 16px rgba(31,119,180,0.4); }}
    50% {{ box-shadow: 0 4px 28px rgba(31,119,180,0.8); }}
}}

/* Chat Panel */
#smartshop-chat-panel {{
    position: fixed;
    top: 0;
    right: -400px;
    width: 380px;
    height: 100vh;
    background: #fff;
    box-shadow: -4px 0 24px rgba(0,0,0,0.15);
    z-index: 9998;
    display: flex;
    flex-direction: column;
    transition: right 0.3s ease;
    border-left: 1px solid #e0e0e0;
}}
#smartshop-chat-panel.open {{ right: 0; }}

/* Panel Header */
#smartshop-chat-header {{
    background: #1f77b4;
    color: #fff;
    padding: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}}
#smartshop-chat-header h3 {{ margin: 0; font-size: 1rem; }}
#smartshop-chat-close {{
    background: none;
    border: none;
    color: #fff;
    font-size: 1.4rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
}}

/* Messages */
#smartshop-chat-messages {{
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}}
.chat-msg-user {{
    align-self: flex-end;
    background: #1f77b4;
    color: #fff;
    padding: 8px 12px;
    border-radius: 12px 12px 2px 12px;
    max-width: 80%;
    font-size: 0.9rem;
}}
.chat-msg-bot {{
    align-self: flex-start;
    background: #f0f4f8;
    color: #333;
    padding: 8px 12px;
    border-radius: 12px 12px 12px 2px;
    max-width: 85%;
    font-size: 0.9rem;
}}
.chat-spinner {{ color: #999; font-style: italic; font-size: 0.85rem; }}

/* Input */
#smartshop-chat-input-row {{
    display: flex;
    padding: 12px;
    border-top: 1px solid #e0e0e0;
    gap: 8px;
    flex-shrink: 0;
}}
#smartshop-chat-input {{
    flex: 1;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.9rem;
    outline: none;
}}
#smartshop-chat-input:focus {{ border-color: #1f77b4; }}
#smartshop-chat-send {{
    background: #1f77b4;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 0.9rem;
}}

/* Mobile */
@media (max-width: 600px) {{
    #smartshop-chat-panel {{ width: 100%; right: -100%; }}
}}
</style>

<!-- Floating Button -->
<button id="smartshop-chat-btn" aria-label="Open AI chat assistant" title="Chat with AI Assistant">
  💬
</button>

<!-- Chat Panel -->
<div id="smartshop-chat-panel" role="dialog" aria-label="AI Chat Assistant" aria-modal="true">
  <div id="smartshop-chat-header">
    <h3>🛒 SmartShop AI</h3>
    <button id="smartshop-chat-close" aria-label="Close chat">✕</button>
  </div>
  <div id="smartshop-chat-messages" aria-live="polite" aria-label="Chat messages">
    <div class="chat-msg-bot">
      👋 Hi! Ask me about products, prices, or reviews!
    </div>
  </div>
  <div id="smartshop-chat-input-row">
    <input id="smartshop-chat-input" type="text"
           placeholder="Ask me anything..." aria-label="Chat message input" />
    <button id="smartshop-chat-send" aria-label="Send message">Send</button>
  </div>
</div>

<script>
(function() {{
  var btn   = document.getElementById('smartshop-chat-btn');
  var panel = document.getElementById('smartshop-chat-panel');
  var close = document.getElementById('smartshop-chat-close');
  var msgs  = document.getElementById('smartshop-chat-messages');
  var input = document.getElementById('smartshop-chat-input');
  var send  = document.getElementById('smartshop-chat-send');
  var API_URL = '{api_url}';

  // Session ID
  var sessionId = sessionStorage.getItem('smartshop_session_id');
  if (!sessionId) {{
    sessionId = 'chat-' + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('smartshop_session_id', sessionId);
  }}

  // Open/close
  btn.addEventListener('click', function() {{
    panel.classList.add('open');
    btn.style.display = 'none';
    input.focus();
  }});
  close.addEventListener('click', function() {{
    panel.classList.remove('open');
    btn.style.display = 'flex';
  }});

  // Keyboard: Escape to close
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape' && panel.classList.contains('open')) {{
      panel.classList.remove('open');
      btn.style.display = 'flex';
      btn.focus();
    }}
  }});

  // Send message
  function sendMessage() {{
    var text = input.value.trim();
    if (!text) return;
    input.value = '';

    // User bubble
    var userDiv = document.createElement('div');
    userDiv.className = 'chat-msg-user';
    userDiv.textContent = text;
    msgs.appendChild(userDiv);

    // Spinner
    var spinner = document.createElement('div');
    spinner.className = 'chat-msg-bot chat-spinner';
    spinner.textContent = 'Thinking...';
    msgs.appendChild(spinner);
    msgs.scrollTop = msgs.scrollHeight;

    fetch(API_URL + '/api/v1/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        message: text,
        session_id: sessionId,
        max_results: 5
      }})
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      msgs.removeChild(spinner);
      var reply = '';
      if (data.success) {{
        var d = data.data || {{}};
        var intent = d.intent || 'general';
        var resp = d.response || {{}};
        if (intent === 'general') {{
          reply = resp.answer || 'I am not sure how to help with that.';
        }} else if (intent === 'policy') {{
          reply = resp.answer || 'No policy information found.';
        }} else if (intent === 'price') {{
          reply = (resp.best_deal ? '🏆 Best Deal: ' + resp.best_deal + '\\n\\n' : '') +
                  (resp.recommendation || 'No comparison data.');
        }} else {{
          reply = resp.summary || resp.reasoning_summary || JSON.stringify(resp).substring(0, 200);
        }}
      }} else {{
        reply = '⚠️ ' + (data.error || 'Something went wrong.');
      }}
      var botDiv = document.createElement('div');
      botDiv.className = 'chat-msg-bot';
      botDiv.textContent = reply;
      msgs.appendChild(botDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }})
    .catch(function(err) {{
      msgs.removeChild(spinner);
      var errDiv = document.createElement('div');
      errDiv.className = 'chat-msg-bot';
      errDiv.textContent = '⚠️ Could not connect to assistant.';
      msgs.appendChild(errDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }});
  }}

  send.addEventListener('click', sendMessage);
  input.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') sendMessage();
  }});
}})();
</script>
"""
```

### `streamlit_app.py` change (add near end, before footer divider)

```python
from app.ui.components.floating_chat import render_floating_chat_widget

# -- Floating Chat Widget (available on all pages) -------------------------
render_floating_chat_widget(api_url)

# -- Footer ----------------------------------------------------------------
st.divider()
```

---

## Test Requirements

**New file:** `tests/test_ui/test_floating_chat.py`

Tests to write (~8 new tests):

```python
test_html_contains_chat_button()         # id="smartshop-chat-btn" present
test_html_contains_chat_panel()          # id="smartshop-chat-panel" present
test_api_url_injected_into_html()        # api_url appears in output
test_html_contains_aria_labels()         # aria-label on btn and panel
test_html_contains_close_button()        # id="smartshop-chat-close"
test_html_contains_input_and_send()      # input + send button present
test_html_contains_slide_animation_css() # "transition" in CSS
test_html_contains_mobile_media_query()  # @media (max-width: 600px)
```

**Expected new tests:** ~8
**Total after story:** ~295

---

## Dependencies

- Depends on SCRUM-18 (UI Polish, `design_tokens.py` in place) ✅
- Requires existing `/api/v1/chat` endpoint from SCRUM-16 ✅
- No new Python packages needed

---

## Out of Scope

- Push notifications or chat history across sessions
- Backend/AI integration changes (API already exists)
