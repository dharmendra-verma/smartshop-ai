"""Product catalog data ingestion pipeline."""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.ingestion import ProductIngestionSchema
from app.services.ingestion.base import DataIngestionPipeline

logger = logging.getLogger(__name__)

COLUMN_MAPPINGS = {
    "product_name": "name",
    "product_title": "name",
    "title": "name",
    "desc": "description",
    "product_description": "description",
    "actual_price": "price",
    "selling_price": "price",
    "discounted_price": "price",
    "brand_name": "brand",
    "main_category": "category",
    "sub_category": "category",
    "product_category": "category",
}


class ProductIngester(DataIngestionPipeline[ProductIngestionSchema]):
    """Ingests product catalog data from CSV files."""

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read CSV and normalize column names."""
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        rename_map = {
            old: new for old, new in COLUMN_MAPPINGS.items() if old in df.columns
        }
        df = df.rename(columns=rename_map)

        logger.info(f"Columns after normalization: {list(df.columns)}")
        return df

    def _validate_row(self, row: pd.Series) -> ProductIngestionSchema:
        """Validate a product row."""
        price = row.get("price", 0)
        if isinstance(price, str):
            price = price.replace("\u20b9", "").replace("$", "").replace(",", "").strip()
            price = float(price) if price else 0

        stock = row.get("stock")
        stock = int(stock) if pd.notna(stock) else None

        rating = row.get("rating")
        rating = float(rating) if pd.notna(rating) else None

        image_url = row.get("image_url") or row.get("picture")
        image_url = str(image_url).strip() if pd.notna(image_url) and image_url else None

        return ProductIngestionSchema(
            id=str(row.get("id", "")).strip(),
            name=str(row.get("name", "")).strip(),
            description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
            price=float(price),
            brand=str(row.get("brand", "")).strip() if pd.notna(row.get("brand")) else None,
            category=str(row.get("category", "General")).strip(),
            stock=stock,
            rating=rating,
            image_url=image_url,
        )

    def _get_dedup_key(self, record: ProductIngestionSchema) -> str:
        """Deduplicate by product ID."""
        return record.id.lower()

    def _insert_record(self, record: ProductIngestionSchema) -> None:
        """Insert validated product into the database."""
        product = Product(
            id=record.id,
            name=record.name,
            description=record.description,
            price=record.price,
            brand=record.brand,
            category=record.category,
            stock=record.stock,
            rating=record.rating,
            image_url=record.image_url,
        )
        self.db.add(product)
