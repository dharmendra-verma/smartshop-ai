"""SmartShop AI design tokens & global CSS."""

# --- Colour palette -----------------------------------------------------------
COLOR_BRAND_PRIMARY   = "#1f77b4"
COLOR_BRAND_SECONDARY = "#ff7f0e"
COLOR_SUCCESS         = "#2ca02c"
COLOR_WARNING         = "#d62728"
COLOR_NEUTRAL_DARK    = "#1a1a2e"
COLOR_NEUTRAL_LIGHT   = "#f0f4f8"

# --- Typography ---------------------------------------------------------------
FONT_SIZE_H1 = "2.4rem"
FONT_SIZE_H2 = "1.6rem"
FONT_SIZE_BODY = "1rem"
FONT_SIZE_CAPTION = "0.85rem"

# --- Spacing -----------------------------------------------------------------
SPACE_XS = "4px"
SPACE_SM = "8px"
SPACE_MD = "16px"
SPACE_LG = "24px"
SPACE_XL = "40px"

# --- Border radius -----------------------------------------------------------
RADIUS_SM = "6px"
RADIUS_MD = "12px"
RADIUS_LG = "20px"


def get_global_css() -> str:
    """
    Return the complete SmartShop AI stylesheet as a <style> string.
    Inject once via st.markdown(get_global_css(), unsafe_allow_html=True).
    """
    return f"""<style>
/* ── Brand Header ─────────────────────────────────────────────── */
.main-header {{
    font-size: {FONT_SIZE_H1};
    font-weight: 700;
    color: {COLOR_BRAND_PRIMARY};
    letter-spacing: -0.5px;
}}
.sub-header {{
    font-size: {FONT_SIZE_BODY};
    color: #666;
    margin-bottom: {SPACE_LG};
}}

/* ── Product Card ─────────────────────────────────────────────── */
.product-card {{
    border: 1px solid #e0e0e0;
    border-radius: {RADIUS_MD};
    padding: {SPACE_MD};
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}}
.product-card:hover {{
    box-shadow: 0 4px 16px rgba(31,119,180,0.18);
    transform: translateY(-2px);
}}
.product-image {{
    width: 100%;
    border-radius: {RADIUS_SM};
    object-fit: contain;
    max-height: 160px;
    background: {COLOR_NEUTRAL_LIGHT};
}}
.price-badge {{
    display: inline-block;
    background: {COLOR_BRAND_PRIMARY};
    color: #fff;
    border-radius: {RADIUS_SM};
    padding: 2px 10px;
    font-size: {FONT_SIZE_CAPTION};
    font-weight: 600;
}}
.stock-badge-ok      {{ color: {COLOR_SUCCESS}; font-weight: 600; }}
.stock-badge-low     {{ color: {COLOR_BRAND_SECONDARY}; font-weight: 600; }}
.stock-badge-out     {{ color: {COLOR_WARNING}; font-weight: 600; }}

/* ── Star Rating ──────────────────────────────────────────────── */
.star-rating {{
    display: inline-flex;
    gap: 2px;
    vertical-align: middle;
}}
.star-filled  {{ color: #f5a623; font-size: 1.1rem; }}
.star-half    {{ color: #f5a623; font-size: 1.1rem; }}
.star-empty   {{ color: #d0d0d0; font-size: 1.1rem; }}

/* ── Chat Bubbles ─────────────────────────────────────────────── */
.chat-timestamp {{
    font-size: {FONT_SIZE_CAPTION};
    color: #999;
    margin-top: {SPACE_XS};
}}

/* ── Empty State ──────────────────────────────────────────────── */
.empty-state {{
    text-align: center;
    padding: {SPACE_XL};
    color: #888;
    font-size: {FONT_SIZE_BODY};
}}

/* ── Accessibility: focus ring ────────────────────────────────── */
button:focus-visible, a:focus-visible {{
    outline: 3px solid {COLOR_BRAND_PRIMARY};
    outline-offset: 2px;
}}
</style>
"""


def render_empty_state(icon: str = "🔍", message: str = "No results found.",
                        hint: str = "") -> str:
    """Return an HTML empty-state block."""
    hint_html = f'<p style="font-size:0.85rem;color:#aaa;">{hint}</p>' if hint else ""
    return (
        f'<div class="empty-state">'
        f'<div style="font-size:3rem;">{icon}</div>'
        f'<p>{message}</p>{hint_html}'
        f'</div>'
    )
