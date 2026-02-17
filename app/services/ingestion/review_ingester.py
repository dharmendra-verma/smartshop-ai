"""Review data ingestion pipeline."""

import hashlib
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.product import Product
from app.schemas.ingestion import ReviewIngestionSchema
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)

REVIEW_COLUMN_MAPPINGS = {
    "user_rating": "rating",
    "star_rating": "rating",
    "stars": "rating",
    "review_body": "review_text",
    "comment": "review_text",
    "review_content": "review_text",
    "review_description": "review_text",
}


class ReviewIngester(DataIngestionPipeline[ReviewIngestionSchema]):
    """Ingests review data from CSV files."""

    def __init__(self, db_session: Session, batch_size: int = 100):
        super().__init__(db_session, batch_size)
        self._valid_product_ids: set[int] | None = None

    def _get_valid_product_ids(self) -> set[int]:
        """Cache and return all valid product IDs from DB."""
        if self._valid_product_ids is None:
            products = self.db.query(Product.product_id).all()
            self._valid_product_ids = {p.product_id for p in products}
            logger.info(f"Loaded {len(self._valid_product_ids)} valid product IDs")
        return self._valid_product_ids

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read review CSV and normalize columns."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        rename_map = {
            old: new for old, new in REVIEW_COLUMN_MAPPINGS.items() if old in df.columns
        }
        df = df.rename(columns=rename_map)
        return df

    def _validate_row(self, row: pd.Series) -> ReviewIngestionSchema:
        """Validate a review row with sentiment inference."""
        product_id = int(row.get("product_id", 0))

        valid_ids = self._get_valid_product_ids()
        if product_id not in valid_ids:
            raise ValueError(f"Product ID {product_id} does not exist")

        rating = int(float(row.get("rating", 0)))

        sentiment = row.get("sentiment")
        if pd.isna(sentiment) or sentiment is None:
            if rating >= 4:
                sentiment = "positive"
            elif rating <= 2:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        review_text = row.get("review_text")
        if pd.notna(review_text):
            review_text = str(review_text).strip()
        else:
            review_text = None

        return ReviewIngestionSchema(
            product_id=product_id,
            rating=rating,
            review_text=review_text,
            sentiment=str(sentiment).lower(),
        )

    def _get_dedup_key(self, record: ReviewIngestionSchema) -> str:
        """Deduplicate by product_id + review_text hash."""
        text = (record.review_text or "").lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{record.product_id}|{text_hash}"

    def _insert_record(self, record: ReviewIngestionSchema) -> None:
        """Insert validated review into the database."""
        review = Review(
            product_id=record.product_id,
            rating=record.rating,
            review_text=record.review_text,
            sentiment=record.sentiment,
        )
        self.db.add(review)
