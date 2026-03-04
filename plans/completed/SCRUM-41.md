# SCRUM-41 — Floating Chat Assistant Widget with Slide-in Chat Window

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-41
**Priority:** Medium
**Status:** Completed

---

## Story

> As a shopper on the e-commerce site, I want a floating chat assistant icon always visible on the page, so that I can quickly get help or ask questions without navigating away from what I'm browsing.

---

## Acceptance Criteria

- [x] A floating circular chat icon (💬) is fixed at the bottom-right corner of every page
- [x] The icon is visible across all pages (product search, reviews, pricing) and does not overlap critical UI elements
- [x] Clicking the chat icon opens a chat window that slides in from the right side of the screen
- [x] The chat window does not navigate away from the current page — it overlays as a side panel
- [x] The chat window has a close button (`>>` chevron icon in footer) that dismisses it and returns to the floating icon state
- [x] The chat window retains conversation history within the same session (does not reset on close)
- [x] On mobile, the chat window takes full width for usability
- [x] The floating icon has a subtle pulse animation on first load, stopping after 3 cycles
- [x] Accessibility: button has aria-label, keyboard navigable (Escape to close), screen-reader friendly
- [x] Center "AI Chat Assistant" page removed — floating widget is the only chat interface
- [x] Chat panel is resizable by dragging the left edge
- [x] Blue header bar with "SmartShop AI" title (built via createElement with inline styles to avoid Streamlit CSS interference)

---

## Implementation

### Architecture

The widget uses `st.components.v1.html()` to run JavaScript that injects the floating button and chat panel directly into the **parent Streamlit document** (`window.parent.document`). This bypasses Streamlit's iframe sandboxing so `position: fixed` works correctly across the entire viewport.

All panel child elements (header, messages, input, footer, close button) are built via `document.createElement()` with inline `style.cssText` to prevent Streamlit's global CSS from hiding or overriding them.

```
app/ui/components/floating_chat.py    ← Widget component
    render_floating_chat_widget(api_url)  → calls components.html() with height=0
    _build_floating_chat_html(api_url)    → returns JS that injects into parent document

app/ui/streamlit_app.py               ← Modified
    - Removed "🤖 AI Chat Assistant" from sidebar navigation
    - Removed center chat page (~80 lines)
    - Removed "Clear Conversation" sidebar button
    - Calls render_floating_chat_widget(api_url) before footer
```

### Key Technical Decisions

1. **`window.parent.document` injection** — `st.markdown(unsafe_allow_html=True)` and `st.html()` both render inside sandboxed containers where `position: fixed` is clipped. Using `components.html()` with `height=0` creates an invisible iframe whose JS injects elements into the parent page DOM.

2. **`createElement` with inline styles** — Streamlit's parent page CSS aggressively overrides injected HTML elements (especially `<h3>`, `<button>`, `<div>` with class names). All panel elements are built programmatically via `createElement()` with `style.cssText` inline styles to guarantee visibility regardless of Streamlit's global styles.

3. **Stale widget cleanup** — Duplicate injection guard checks for both the chat button AND the close button. If the button exists but close button is missing (stale version), old elements are removed and re-injected fresh. This handles code updates without requiring hard refresh.

4. **Direct `fetch()` to `/api/v1/chat`** — Bypasses Streamlit re-renders for smooth chat UX. Session ID stored in `window.parent.sessionStorage`.

5. **`ChatResponse` parsing** — API returns `intent` and `response` at the top level (not nested under `data`). JS reads `data.intent` and `data.response` directly. Intent-specific formatting:
   - `general` / `policy`: shows `resp.answer`
   - `recommendation` / `comparison`: numbered list with name, price, reason
   - `review`: rating + total reviews + overall summary
   - `price`: best deal + recommendation text

6. **Resize handle** — Left edge drag handle (`cursor: col-resize`) with mousedown/mousemove/mouseup listeners. Min width 280px, max 80% viewport. `.resizing` class disables CSS transitions during drag.

7. **Close button in footer** — A `>>` chevron icon (matching Streamlit's `<<` sidebar collapse style) in a grey footer bar below the input row. Positioned left-aligned for easy access.

### File Map

| File | Action | What Changed |
|------|--------|-------------|
| `app/ui/components/floating_chat.py` | CREATE → REWRITE | Uses `components.html()` + `window.parent.document` injection; all elements via `createElement`; resize handle; footer close button; intent-aware response formatting |
| `app/ui/streamlit_app.py` | MODIFY | Removed center chat page, sidebar nav item, clear button; `if` instead of `elif` for first page |
| `tests/test_ui/test_floating_chat.py` | CREATE | 13 tests for JS generation, aria labels, parent injection, duplicate guard, resize, close button |

### DOM Structure (injected into parent)

```
<button #smartshop-chat-btn>  💬 floating button (body)
<div #smartshop-chat-panel>   slide-in panel (body)
  ├── <div #smartshop-chat-resize>    drag handle (absolute, left edge)
  ├── <div #smartshop-chat-header>    blue title bar "SmartShop AI"
  ├── <div #smartshop-chat-messages>  scrollable message area
  │     └── .ss-chat-msg-bot / .ss-chat-msg-user bubbles
  ├── <div #smartshop-chat-input-row> input + Send button
  └── <div #smartshop-chat-footer>    footer with >> close button
        └── <button #smartshop-chat-close>
```

---

## Tests

**File:** `tests/test_ui/test_floating_chat.py` — 13 tests

```
test_js_creates_chat_button          — "smartshop-chat-btn" in output
test_js_creates_chat_panel           — "smartshop-chat-panel" in output
test_api_url_injected_into_html      — api_url appears in JS
test_html_contains_aria_labels       — all 5 aria-labels present
test_js_creates_close_button         — "smartshop-chat-close" in output
test_js_creates_input_and_send       — input + send IDs present
test_html_contains_slide_animation   — "right 0.3s ease" transition
test_html_contains_mobile_media      — @media (max-width: 600px)
test_different_api_url_injected      — custom URL + /api/v1/chat present
test_injects_into_parent_document    — window.parent.document + parentDoc.body.appendChild
test_prevents_duplicate_injection    — getElementById check + return guard
test_resize_handle_present           — resize div + col-resize + mousedown/mousemove
test_close_button_in_footer          — close button + footer bar IDs present
```

---

## Dependencies

- Depends on SCRUM-18 (UI Polish, `design_tokens.py` in place) ✅
- Requires existing `/api/v1/chat` endpoint from SCRUM-16 ✅
- Uses `streamlit.components.v1.html()` (built-in, no new packages)

---

## Out of Scope

- Push notifications or chat history across sessions
- Backend/AI integration changes (API already exists)
