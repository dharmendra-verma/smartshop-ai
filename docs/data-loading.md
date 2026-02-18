# Data Loading Guide

## Prerequisites

1. **PostgreSQL** installed and running
2. **Database** created (or use existing `postgres` database)
3. **`.env`** configured with your `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/postgres
   ```
4. **Dependencies** installed: `pip install -r requirements.txt`

## Loading Data

### Full Load (Recommended)

Load all products, reviews, and policies with a clean database:

```bash
python scripts/load_catalog.py --clean
```

### Load Without Dropping Tables

Append data (duplicates are automatically skipped):

```bash
python scripts/load_catalog.py
```

### Load Specific Data Type

```bash
python scripts/load_catalog.py --type products
python scripts/load_catalog.py --type reviews
python scripts/load_catalog.py --type policies
```

### Alternative: Using ingest_data.py

```bash
python scripts/ingest_data.py --type all
python scripts/ingest_data.py --type products --file data/raw/products.csv
```

## Verification

### Run Data Quality Report

```bash
python scripts/verify_data.py
python scripts/verify_data.py --save  # Also saves JSON report
```

### Run Sample Queries

```bash
python scripts/sample_queries.py
```

## Expected Results

After a successful load:

| Table | Records |
|-------|---------|
| Products | 2,000 |
| Reviews | ~3,946 (54 duplicates skipped) |
| Policies | 22 |

- 4 product categories: Smartphone, Laptop, Smart_Tv, Speaker
- 15 unique brands
- Price range: $51.25 - $2,996.87
- 8 policy types: shipping, returns, warranty, exchanges, repairs, financing, preorder, price_matching

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: psycopg2` | `pip install psycopg2-binary` |
| Connection refused | Check PostgreSQL is running on the configured host/port |
| Authentication failed | Verify DATABASE_URL credentials in `.env` |
| Tables already exist | Use `--clean` flag to drop and recreate |
