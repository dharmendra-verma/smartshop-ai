"""Mock pricing service — deterministic competitor prices from product_id seed."""

import hashlib
from app.services.pricing.base import PricingService

# Price variation ranges per source (as fraction of base price)
_SOURCE_VARIATIONS = {
    "Amazon":  (-0.08, -0.03),   # typically 3-8% cheaper
    "BestBuy": (-0.02,  0.05),   # near parity to +5%
    "Walmart": (-0.12, -0.05),   # typically 5-12% cheaper
}


class MockPricingService(PricingService):
    """
    Generates deterministic mock competitor prices.

    Uses a hash of product_id to produce stable, repeatable price variants.
    Replace with a real API client when live pricing is available.
    """

    SOURCES = list(_SOURCE_VARIATIONS.keys())

    def get_prices(self, product_id: str, base_price: float) -> dict[str, float]:
        prices = {}
        for i, (source, (low, high)) in enumerate(_SOURCE_VARIATIONS.items()):
            # Deterministic variation: hash(product_id + source) → float in [low, high]
            seed = int(hashlib.md5(f"{product_id}:{source}".encode()).hexdigest()[:8], 16)
            variation = low + (seed / 0xFFFFFFFF) * (high - low)
            raw_price = base_price * (1 + variation)
            # Round to nearest $0.99
            prices[source] = round(raw_price - 0.01, 2) if raw_price > 1 else round(raw_price, 2)
        return prices
