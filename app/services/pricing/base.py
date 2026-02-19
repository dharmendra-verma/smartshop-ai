"""Abstract base class for pricing services."""

from abc import ABC, abstractmethod


class PricingService(ABC):
    """Interface for fetching competitor prices."""

    SOURCES: list[str] = []

    @abstractmethod
    def get_prices(self, product_id: str, base_price: float) -> dict[str, float]:
        """
        Return competitor prices for a product.

        Args:
            product_id: Product identifier
            base_price: Our catalog price (used as reference for mock variants)

        Returns:
            Dict mapping source name → price, e.g. {"Amazon": 749.99, "BestBuy": 799.00}
        """
        ...
