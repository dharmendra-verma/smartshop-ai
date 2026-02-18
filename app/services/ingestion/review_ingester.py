"""Review data ingestion pipeline."""

import hashlib
import logging
from datetime import datetime
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
    "review_body": "text",
    "comment": "text",
    "review_content": "text",
    "review_description": "text",
    "review_text": "text",
}


class ReviewIngester(DataIngestionPipeline[ReviewIngestionSchema]):
    """Ingests review data from CSV files."""

    def __init__(self, db_session: Session, batch_size: int = 100):
        super().__init__(db_session, batch_size)
        self._valid_product_ids: set[str] | None = None

    def _get_valid_product_ids(self) -> set[str]:
        """Cache and return all valid product IDs from DB."""
        if self._valid_product_ids is None:
            products = self.db.query(Product.id).all()
            self._valid_product_ids = {p.id for p in products}
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
        product_id = str(row.get("product_id", "")).strip()

        valid_ids = self._get_valid_product_ids()
        if product_id not in valid_ids:
            raise ValueError(f"Product ID {product_id} does not exist")

        rating = float(row.get("rating", 0))

        sentiment = row.get("sentiment")
        if pd.isna(sentiment) or sentiment is None:
            if rating >= 4:
                sentiment = "positive"
            elif rating <= 2:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        text = row.get("text")
        if pd.notna(text):
            text = str(text).strip()
        else:
            text = None

        # Parse date
        review_date = None
        date_val = row.get("date")
        if pd.notna(date_val) and date_val is not None:
            if isinstance(date_val, str):
                try:
                    review_date = datetime.strptime(date_val.strip(), "%m/%d/%Y").date()
                except ValueError:
                    try:
                        review_date = datetime.strptime(date_val.strip(), "%Y-%m-%d").date()
                    except ValueError:
                        logger.warning(f"Could not parse date: {date_val}")
            else:
                review_date = pd.Timestamp(date_val).date()

        return ReviewIngestionSchema(
            product_id=product_id,
            rating=rating,
            text=text,
            sentiment=str(sentiment).lower(),
            review_date=review_date,
        )

    def _get_dedup_key(self, record: ReviewIngestionSchema) -> str:
        """Deduplicate by product_id + text hash."""
        text = (record.text or "").lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"{record.product_id}|{text_hash}"

    def _insert_record(self, record: ReviewIngestionSchema) -> None:
        """Insert validated review into the database."""
        review = Review(
            product_id=record.product_id,
            rating=record.rating,
            text=record.text,
            sentiment=record.sentiment,
            review_date=record.review_date,
        )
        self.db.add(review)
