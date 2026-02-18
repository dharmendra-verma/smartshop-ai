"""Tests for product catalog ingester."""

import pytest
from decimal import Decimal

from app.models.product import Product
from app.services.ingestion.product_ingester import ProductIngester


class TestProductIngester:
    """Tests for ProductIngester."""

    def test_ingest_valid_csv(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,description,price,brand,category,stock,rating\n"
            "SP0001,Headphones,Great sound,79.99,SoundMax,Electronics,45,4.5\n"
            "SP0002,Watch,Smart watch,149.99,FitTech,Electronics,30,4.2\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.total_records == 2
        assert result.successful == 2
        assert result.failed == 0

        products = db_session.query(Product).all()
        assert len(products) == 2
        assert products[0].name == "Headphones"
        assert products[0].category == "Electronics"

    def test_column_name_mapping(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,product_name,product_description,selling_price,brand_name,main_category\n"
            "LP0001,Laptop,Fast laptop,999.99,TechCo,Computers\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        product = db_session.query(Product).first()
        assert product.name == "Laptop"

    def test_price_cleaning_currency_symbol(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,price,category\n"
            "SP0010,Item,$299.99,Electronics\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        product = db_session.query(Product).first()
        assert float(product.price) == 299.99

    def test_deduplication_by_id(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,price,brand,category\n"
            "SP0001,Widget,10.0,BrandA,General\n"
            "SP0001,Widget Updated,15.0,BrandA,General\n"
            "SP0002,Widget,10.0,BrandB,General\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 2  # SP0001 and SP0002
        assert result.duplicates_skipped == 1

    def test_missing_optional_columns(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,price,category\n"
            "SP0020,Simple Item,9.99,General\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        product = db_session.query(Product).first()
        assert product.brand is None

    def test_invalid_rows_counted_as_failures(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,price,category\n"
            "SP0030,Good Item,10.0,Electronics\n"
            ",0,\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        assert result.successful == 1
        assert result.failed == 1

    def test_category_normalized_to_title_case(self, db_session, tmp_path):
        csv_file = tmp_path / "products.csv"
        csv_file.write_text(
            "id,name,price,category\n"
            "SP0040,Item,10.0,home & kitchen\n"
        )

        ingester = ProductIngester(db_session=db_session)
        result = ingester.run(csv_file)

        product = db_session.query(Product).first()
        assert product.category == "Home & Kitchen"
