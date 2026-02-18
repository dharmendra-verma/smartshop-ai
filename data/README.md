# SmartShop AI — Data Directory

## Overview

This directory contains the product catalog, customer reviews, and store policy data used by SmartShop AI.

## File Structure

```
data/
├── raw/                        # Source CSV files
│   ├── products.csv            # 2000 products
│   ├── reviews.csv             # 4000 customer reviews
│   ├── store_policies.csv      # 22 store policies
│   ├── sample_products.csv     # Small sample (10 products)
│   ├── sample_reviews.csv      # Small sample reviews
│   └── sample_policies.csv     # Small sample policies
├── processed/                  # Generated reports
│   ├── data_quality_report.json
│   └── quality_reports/        # Per-ingestion quality reports
└── README.md
```

## Data Dictionary

### products.csv (2000 records)

| Column | Type | Description |
|--------|------|-------------|
| id | String | Unique product ID (e.g., SP0001, LP0003, TV0004) |
| name | String | Product name |
| brand | String | Brand name (15 unique brands) |
| category | String | Product category: smartphone, laptop, smart_tv, speaker |
| price | Float | Price in USD ($51.25 - $2996.87) |
| description | String | Product description |
| stock | Integer | Units in stock |
| rating | Float | Average product rating (1.0 - 5.0) |

### reviews.csv (4000 records)

| Column | Type | Description |
|--------|------|-------------|
| product_id | String | Foreign key to products.id |
| rating | Float | Review rating (1.0 - 5.0) |
| text | String | Review text |
| date | String | Review date (M/D/YYYY format) |

### store_policies.csv (22 records)

| Column | Type | Description |
|--------|------|-------------|
| policy_type | String | Policy category: shipping, returns, warranty, exchanges, repairs, financing, preorder, price_matching |
| description | String | Policy title/description |
| conditions | String | Pipe-delimited conditions |
| timeframe | Integer | Timeframe in days |

## Loading Data

See [docs/data-loading.md](../docs/data-loading.md) for loading instructions.
