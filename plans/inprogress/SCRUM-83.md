# SCRUM-83: Clickable Product Links in Chat Agent Responses

## Story Details
- **ID**: SCRUM-83
- **Title**: Clickable Product Links in Chat Agent Responses
- **Status**: In Progress
- **Story Points**: 3
- **Sprint**: Current

## Acceptance Criteria
- [ ] When any agent (Recommendation, Price, Review, General) mentions a product, the product name is rendered as a clickable hyperlink in the Streamlit chat UI
- [ ] Clicking the product link scrolls/navigates to that product on the main page and highlights or expands its product card
- [ ] Links work for all product references: single recommendations, comparison lists, review summaries, and price comparisons
- [ ] If a product ID is hallucinated or invalid, no link is rendered (graceful fallback to plain text)
- [ ] Links are visually distinct (styled as hyperlinks) so users can easily identify clickable products
- [ ] All existing 511 tests pass
- [ ] New tests for link generation and rendering logic

---

## Current State Analysis

### What Exists
1. **Product IDs flow through the entire stack** — agents return `product_id` in all response types (Recommendation, Review, Price), the Chat API passes full agent data in `ChatResponse.response`, and the floating chat JS receives the JSON with product_ids.
2. **Floating chat widget** (`app/ui/components/floating_chat.py`) renders messages using `textContent` (plain text only — no HTML).
3. **Chat helpers** (`app/ui/components/chat_helpers.py`) format responses with `format_recommendation_message()` and `format_review_message()` as plain markdown strings — no links.
4. **Product cards** (`app/ui/components/product_card.py`) are rendered as Streamlit containers with no anchor IDs for deep linking.
5. **Main app** (`app/ui/streamlit_app.py`) uses tab-based navigation, no query parameter routing.

### Key Insight
Product IDs are already available in the frontend JavaScript (floating chat receives the full response JSON). The work is entirely about **rendering links** and **handling navigation** — no backend agent changes needed.

---

## Technical Approach

### Architecture Decision: Session State + Streamlit Query Params

We'll use a **hybrid approach**:
- Floating chat renders product names as clickable links with `data-product-id` attributes
- Click handler uses `window.parent.postMessage()` to communicate product_id to Streamlit
- Streamlit receives via `st.query_params` or a hidden component and sets `st.session_state.focused_product_id`
- Main page scrolls to and highlights the focused product card

This aligns with existing patterns (compare panel uses session state, review panel uses session state) and avoids XSS risks.

---

## Implementation Plan

### Task 1: Add Product Link Rendering in Floating Chat Widget
**File**: `app/ui/components/floating_chat.py`

**Changes**:
1. Switch from `textContent` to `innerHTML` for bot messages (with sanitization)
2. Update recommendation/comparison formatting (lines ~387-398) to wrap product names in clickable `<a>` tags:
   ```javascript
   // Before:
   reply += (i+1) + '. ' + (r.name || r.product_id || 'Product') + ...

   // After:
   var productName = r.name || r.product_id || 'Product';
   var productId = r.product_id || '';
   var link = productId
     ? '<a href="#" class="ss-product-link" data-product-id="' + productId + '">' + escapeHtml(productName) + '</a>'
     : escapeHtml(productName);
   reply += (i+1) + '. <strong>' + link + '</strong>' + ...
   ```
3. Update review intent formatting to link product name
4. Update price intent formatting to link product names
5. Add `escapeHtml()` utility function to prevent XSS:
   ```javascript
   function escapeHtml(text) {
     var div = parentDoc.createElement('div');
     div.appendChild(parentDoc.createTextNode(text));
     return div.innerHTML;
   }
   ```

### Task 2: Add Product Link Click Handler
**File**: `app/ui/components/floating_chat.py`

**Changes**:
1. Add event delegation for `.ss-product-link` clicks:
   ```javascript
   msgs.addEventListener('click', function(e) {
     var link = e.target.closest('.ss-product-link');
     if (link) {
       e.preventDefault();
       var productId = link.getAttribute('data-product-id');
       // Communicate to Streamlit parent
       window.parent.postMessage({
         type: 'smartshop-navigate-product',
         productId: productId
       }, '*');
     }
   });
   ```

### Task 3: Add Product Link Styles
**File**: `app/ui/components/floating_chat.py`

**Changes** (in CSS section):
```css
.ss-product-link {
  color: #1f77b4;
  text-decoration: underline;
  cursor: pointer;
  font-weight: 600;
}
.ss-product-link:hover {
  color: #ff7f0e;
  text-decoration: underline;
}
```

### Task 4: Add Streamlit Message Receiver & Product Focus State
**File**: `app/ui/streamlit_app.py`

**Changes**:
1. Add a hidden Streamlit component that listens for `postMessage` events:
   ```python
   # Inject JS listener for product navigation from chat
   st.components.v1.html("""
   <script>
     window.addEventListener('message', function(event) {
       if (event.data && event.data.type === 'smartshop-navigate-product') {
         // Set query param to trigger Streamlit rerun
         const url = new URL(window.parent.location);
         url.searchParams.set('focus_product', event.data.productId);
         window.parent.history.pushState({}, '', url);
         // Trigger Streamlit rerun
         window.parent.document.querySelectorAll('button[kind="header"]')[0]?.click();
       }
     });
   </script>
   """, height=0)
   ```
2. At page load, check for `focus_product` query param:
   ```python
   focus_product_id = st.query_params.get("focus_product", None)
   if focus_product_id:
       st.session_state["focused_product_id"] = focus_product_id
       # Clear the param after reading
       st.query_params.clear()
   ```

### Task 5: Add Product Card Highlight & Scroll-To
**File**: `app/ui/components/product_card.py`

**Changes**:
1. Add an HTML anchor/ID to each product card container:
   ```python
   # At the start of render_product_card():
   is_focused = st.session_state.get("focused_product_id") == product.get("id")
   border_color = "#ff7f0e" if is_focused else None  # Orange highlight for focused

   with st.container(border=True):
       # Inject anchor element
       st.markdown(f'<div id="product-{product["id"]}"></div>', unsafe_allow_html=True)
       # ... existing card rendering ...
   ```
2. If product is focused, inject auto-scroll JavaScript:
   ```python
   if is_focused:
       st.markdown(f"""
       <script>
         document.getElementById('product-{product["id"]}')?.scrollIntoView({{
           behavior: 'smooth', block: 'center'
         }});
       </script>
       """, unsafe_allow_html=True)
       # Clear focus after scroll
       del st.session_state["focused_product_id"]
   ```
3. Apply visual highlight (thicker border, subtle glow) to focused card

### Task 6: Update Chat Helpers for Non-Widget Chat
**File**: `app/ui/components/chat_helpers.py`

**Changes**:
1. Update `format_recommendation_message()` to include product links as markdown:
   ```python
   def format_recommendation_message(recommendations: list) -> str:
       lines = []
       for i, rec in enumerate(recommendations, 1):
           name = rec.get("name", "Product")
           product_id = rec.get("product_id") or rec.get("id", "")
           price = rec.get("price", 0)
           # ... existing star rating logic ...
           if product_id:
               lines.append(f"**{i}. [{name}](#{product_id})** — ${price:.2f} {stars}")
           else:
               lines.append(f"**{i}. {name}** — ${price:.2f} {stars}")
           if rec.get("reason"):
               lines.append(f"   _{rec['reason']}_")
       return "\n".join(lines)
   ```
2. Similar updates for `format_review_message()` and price formatting

### Task 7: Handle Edge Cases
**File**: `app/ui/components/floating_chat.py`, `app/ui/streamlit_app.py`

**Changes**:
1. **Hallucinated product IDs**: If `product_id` is present but product doesn't exist in current page results, expand search or show "Product not found" toast
2. **Product not loaded**: If the product isn't in the current page of results, trigger a search for the product:
   ```python
   if focus_product_id and focus_product_id not in displayed_product_ids:
       # Fetch the specific product and prepend to results
       focused_product = api_client.get_product(focus_product_id)
       if focused_product:
           st.session_state["search_results"].insert(0, focused_product)
   ```
3. **Multiple products**: Each product in a list gets its own independent link
4. **Policy agent**: No product links (policies don't reference products) — skip gracefully

---

## File Map

| File | Action | Description |
|------|--------|-------------|
| `app/ui/components/floating_chat.py` | MODIFY | Link rendering, click handler, CSS styles |
| `app/ui/components/chat_helpers.py` | MODIFY | Markdown link formatting for recommendations, reviews, prices |
| `app/ui/components/product_card.py` | MODIFY | Add anchor IDs, focus highlight, scroll-to logic |
| `app/ui/streamlit_app.py` | MODIFY | Message listener, focus_product query param handling, product lookup |
| `app/ui/api_client.py` | MODIFY | Add `get_product(product_id)` method if not exists |
| `tests/test_ui/test_floating_chat.py` | MODIFY | Add tests for product link rendering |
| `tests/test_ui/test_chat_helpers.py` | CREATE | Tests for link formatting in chat helpers |
| `tests/test_ui/test_product_card.py` | MODIFY | Tests for focus highlight and anchor rendering |

---

## Test Requirements

### New Tests (Target: ~12-15 new tests)

**test_chat_helpers.py** (new file):
1. `test_format_recommendation_with_product_links` — verify links generated with product_id
2. `test_format_recommendation_without_product_id` — fallback to plain text
3. `test_format_recommendation_multiple_products` — all products get links
4. `test_format_review_with_product_link` — review includes product link
5. `test_format_price_with_product_links` — price comparison links
6. `test_escape_special_characters_in_product_name` — XSS prevention

**test_floating_chat.py** (existing):
7. `test_product_link_html_generation` — verify `<a>` tags with data-product-id
8. `test_product_link_css_styles` — verify link styles present
9. `test_click_handler_event_delegation` — verify click listener code
10. `test_escape_html_utility` — XSS sanitization function

**test_product_card.py** (existing):
11. `test_product_card_anchor_id` — verify anchor element rendered
12. `test_product_card_focus_highlight` — verify highlight when focused
13. `test_product_card_scroll_script` — verify scroll-to script injected
14. `test_product_card_focus_cleared_after_render` — state cleanup

**test_streamlit_app.py** or integration:
15. `test_focus_product_query_param_handling` — verify query param sets session state

---

## Dependencies
- **No backend changes required** — product IDs already flow through the stack
- **No agent changes required** — response structures already include product references
- **No DB changes** — no new tables or migrations
- **Depends on**: Existing agent response structure (SCRUM-10, SCRUM-11, SCRUM-14) all completed

## Risks
1. **Streamlit iframe limitations** — `postMessage` between floating chat iframe and Streamlit may have cross-origin restrictions. Mitigation: both are same-origin (localhost:8501)
2. **Product not in current view** — user may have search filters active that exclude the linked product. Mitigation: Task 7 handles this with dynamic product fetch
3. **XSS via product names** — using `innerHTML` requires sanitization. Mitigation: `escapeHtml()` utility for all dynamic content

## Execution Order
1. Task 1 (Link rendering) → Task 3 (Styles) → Task 2 (Click handler) — get links visible first
2. Task 4 (Streamlit receiver) → Task 5 (Product card highlight) — get navigation working
3. Task 6 (Chat helpers) — update non-widget formatting
4. Task 7 (Edge cases) — handle missing products
5. Tests throughout each task

## Estimated Time
- Implementation: ~2-3 hours
- Testing: ~1 hour
- Edge cases & polish: ~30 min
