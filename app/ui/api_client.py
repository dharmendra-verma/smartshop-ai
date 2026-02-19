"""HTTP client for SmartShop AI FastAPI backend.

All functions return a result dict: {"success": bool, "data": any, "error": str | None}
Never raises — all exceptions are caught and returned as error responses.
"""

import logging
import time
import requests
from typing import Any

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 60  # seconds – agent endpoints call LLMs and need more time

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_RETRY_DELAYS = [0.5, 1.0, 2.0]  # seconds — exponential back-off


def _get(url: str, params: dict | None = None) -> dict[str, Any]:
    """Internal GET helper with retry on transient failures."""
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if r.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
                continue
            r.raise_for_status()
            return {"success": True, "data": r.json(), "error": None}
        except requests.exceptions.ConnectionError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
        except requests.exceptions.HTTPError as e:
            detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            return {"success": False, "data": None, "error": f"API error: {detail}"}
        except Exception as e:
            logger.error("Unexpected error in GET %s: %s", url, e)
            return {"success": False, "data": None, "error": f"Unexpected error: {str(e)}"}

    # All retries exhausted
    if isinstance(last_error, requests.exceptions.Timeout):
        return {"success": False, "data": None, "error": "Request timed out after retries. Please try again."}
    return {"success": False, "data": None, "error": "Cannot connect to backend after retries. Is FastAPI running?"}


def _post(url: str, payload: dict) -> dict[str, Any]:
    """Internal POST helper with retry on transient failures."""
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
            if r.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
                continue
            r.raise_for_status()
            return {"success": True, "data": r.json(), "error": None}
        except requests.exceptions.ConnectionError as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAYS[attempt])
        except requests.exceptions.HTTPError as e:
            detail = e.response.json().get("detail", str(e)) if e.response else str(e)
            return {"success": False, "data": None, "error": f"API error: {detail}"}
        except Exception as e:
            logger.error("Unexpected error in POST %s: %s", url, e)
            return {"success": False, "data": None, "error": f"Unexpected error: {str(e)}"}

    if isinstance(last_error, requests.exceptions.Timeout):
        return {"success": False, "data": None, "error": "Request timed out after retries. Please try again."}
    return {"success": False, "data": None, "error": "Cannot connect to backend after retries. Is FastAPI running?"}


# -- Public API ----------------------------------------------------------------

def health_check(api_url: str) -> bool:
    """Returns True if the backend is reachable and healthy."""
    result = _get(f"{api_url}/health")
    return result["success"]


def get_recommendations(
    api_url: str,
    query: str,
    max_results: int = 5,
    max_price: float | None = None,
    min_price: float | None = None,
    category: str | None = None,
    min_rating: float | None = None,
) -> dict[str, Any]:
    """
    Call POST /api/v1/recommendations.
    Returns {"success": bool, "data": RecommendationResponse dict, "error": str | None}
    """
    payload = {"query": query, "max_results": max_results}
    if max_price is not None:
        payload["max_price"] = max_price
    if min_price is not None:
        payload["min_price"] = min_price
    if category:
        payload["category"] = category
    if min_rating is not None:
        payload["min_rating"] = min_rating
    return _post(f"{api_url}/api/v1/recommendations", payload)


def summarize_reviews(
    api_url: str,
    query: str,
    product_id: str | None = None,
    max_reviews: int = 20,
) -> dict[str, Any]:
    """
    Call POST /api/v1/reviews/summarize.
    Returns {"success": bool, "data": ReviewSummarizationResponse dict, "error": str | None}
    """
    payload = {"query": query, "max_reviews": max_reviews}
    if product_id:
        payload["product_id"] = product_id
    return _post(f"{api_url}/api/v1/reviews/summarize", payload)


def search_products(
    api_url: str,
    category: str | None = None,
    brand: str | None = None,
    page: int = 1,
    page_size: int = 12,
) -> dict[str, Any]:
    """
    Call GET /api/v1/products with filters.
    Returns {"success": bool, "data": ProductListResponse dict, "error": str | None}
    """
    params: dict = {"page": page, "page_size": page_size}
    if category and category != "All":
        params["category"] = category
    if brand:
        params["brand"] = brand
    return _get(f"{api_url}/api/v1/products", params=params)
