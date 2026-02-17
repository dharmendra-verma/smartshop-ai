# Database Documentation

## Schema Overview

### Products Table (`products`)

Stores the e-commerce product catalog.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| product_id | Integer (PK) | No | Auto-incrementing primary key |
| name | String(255) | No | Product name |
| description | Text | Yes | Product description |
| price | Numeric(10,2) | No | Product price |
| brand | String(100) | Yes | Brand name |
| category | String(100) | No | Product category |
| image_url | String(500) | Yes | Product image URL |
| created_at | DateTime(tz) | No | Record creation timestamp |
| updated_at | DateTime(tz) | Yes | Last update timestamp |

**Indexes:** product_id, name, brand, category, (category + brand), price

### Reviews Table (`reviews`)

Stores customer product reviews with sentiment analysis.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| review_id | Integer (PK) | No | Auto-incrementing primary key |
| product_id | Integer (FK) | No | References products.product_id (CASCADE) |
| rating | Integer | No | Rating 1-5 (CHECK constraint) |
| review_text | Text | Yes | Review content |
| sentiment | String(20) | Yes | positive, negative, or neutral |
| timestamp | DateTime(tz) | No | Review creation timestamp |

**Indexes:** review_id, product_id, (product_id + rating), sentiment, timestamp
**Constraints:** `check_rating_range` (rating >= 1 AND rating <= 5)

### Policies Table (`policies`)

Stores store policies and FAQs for the RAG agent.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| policy_id | Integer (PK) | No | Auto-incrementing primary key |
| category | String(100) | No | Policy category (shipping, returns, privacy) |
| question | Text | No | FAQ question |
| answer | Text | No | FAQ answer |
| effective_date | Date | No | When policy takes effect |
| created_at | DateTime(tz) | No | Record creation timestamp |
| updated_at | DateTime(tz) | Yes | Last update timestamp |

**Indexes:** policy_id, category, effective_date, (category + effective_date)

## Relationships

- **Product -> Reviews**: One-to-Many (cascade delete)
- Access reviews from product: `product.reviews`
- Access product from review: `review.product`

## Migrations

Managed with Alembic. Migration files are in `alembic/versions/`.

```bash
# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Check current version
alembic current

# Create new migration
alembic revision --autogenerate -m "description"
```

Current version: `001` (initial schema)

## Setup

1. Configure `DATABASE_URL` in `.env`
2. Run: `python scripts/init_db.py`
3. To seed sample data: `python scripts/init_db.py --seed`
4. To skip Alembic and create tables directly: `python scripts/init_db.py --no-alembic`
