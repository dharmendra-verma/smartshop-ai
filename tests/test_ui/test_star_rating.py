"""Unit tests for star_rating component (pure functions — no Streamlit calls)."""

import pytest
from app.ui.components.star_rating import render_star_rating_html, star_rating_text


def test_none_rating_returns_na():
    html = render_star_rating_html(None)
    assert "N/A" in html


def test_full_stars_five():
    html = render_star_rating_html(5.0)
    assert html.count("star-filled") == 5
    assert "star-empty" not in html
    assert "star-half" not in html


def test_half_star_precision():
    html = render_star_rating_html(4.5)
    assert html.count("star-filled") == 4
    assert "star-half" in html
    assert html.count("star-empty") == 0


def test_zero_rating_all_empty():
    html = render_star_rating_html(0.0)
    assert html.count("star-empty") == 5
    assert "star-filled" not in html


def test_aria_label_present():
    html = render_star_rating_html(3.7, label="Widget X")
    assert 'aria-label="Widget X: 3.7 out of 5 stars"' in html
    assert 'role="img"' in html


def test_star_rating_text_plain():
    text = star_rating_text(4.0)
    assert "★★★★" in text
    assert "4.0" in text
