# Data Pipeline

SmartShop AI ingests product, review, and policy data from CSV files into PostgreSQL and builds a FAISS vector index for policy RAG.

---

## Data Sources

```
data/raw/
├── products.csv         # Product catalog (~50 records)
├── reviews.csv          # Customer reviews (~1000 records)
└── store_policies.csv   # Store policies (~20 records)
```

---

## CSV Schemas

### products.csv

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | string | Yes | Primary key (e.g., `SP0001`) |
| `name` | string | Yes | Aliases: `product_name`, `product_title`, `title` |
| `brand` | string | No | Alias: `brand_name` |
| `category` | string | Yes | Aliases: `main_category`, `sub_category` |
| `price` | float | Yes | Aliases: `actual_price`, `selling_price`; strips currency symbols |
| `description` | string | No | Aliases: `desc`, `product_description` |
| `stock` | int | No | Default: 0 |
| `rating` | float | No | 0.0–5.0 |

**Categories:** smartphone, laptop, speaker, smart_tv

**Price range:** $73 – $2173

### reviews.csv

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `product_id` | string | Yes | FK to products |
| `rating` | float | Yes | Aliases: `user_rating`, `star_rating`, `stars` |
| `text` | string | No | Aliases: `review_body`, `comment`, `review_text` |
| `date` | string | No | Parsed as `MM/DD/YYYY` or `YYYY-MM-DD` |

**Sentiment inference** (if not provided): rating >= 4 → positive, <= 2 → negative, else → neutral.

### store_policies.csv

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `policy_type` | string | Yes | e.g., returns, warranty, shipping |
| `description` | string | Yes | Policy description |
| `conditions` | string | No | Pipe-delimited (`\|`) conditions |
| `timeframe` | int | No | Days (0 = N/A) |

---

## Ingestion Pipeline

### Architecture

All ingesters inherit from `DataIngestionPipeline[T]`:

```python
class DataIngestionPipeline(ABC, Generic[T]):
    def run(self, file_path: str) -> IngestionResult:
        1. Read CSV with column normalization
        2. Validate rows (Pydantic schemas)
        3. Deduplicate by key
        4. Insert in batches of 100
        5. Commit + return result
```

### Deduplication Keys

| Ingester | Key |
|----------|-----|
| Products | `product_id.lower()` |
| Reviews | `"{product_id}\|{MD5(text)[:12]}"` |
| Policies | `"{policy_type.lower()}\|{MD5(description)[:12]}"` |

### Running Ingestion

```bash
python -m scripts.load_data
```

This runs all three ingesters in sequence and logs results.

### IngestionResult

```python
@dataclass
class IngestionResult:
    total_records: int
    successful: int
    failed: int
    duplicates_skipped: int
    success_rate: float  # percentage
    errors: list[str]    # up to 10 sample errors
```

---

## Quality Monitoring

**File:** `app/services/ingestion/quality_monitor.py`

After each ingestion run, quality checks verify:
- Success rate >= 80%
- Error count <= 100

Reports are written to `data/processed/quality_reports/<source>_<timestamp>.json`.

---

## FAISS Vector Index

The PolicyAgent uses a FAISS vector index for semantic retrieval.

### Build Process

1. Load all Policy records from PostgreSQL
2. Concatenate `description + conditions` per policy
3. Embed using `text-embedding-3-small` (1536 dimensions)
4. L2-normalize vectors (`faiss.normalize_L2`)
5. Index using `faiss.IndexFlatIP` (inner product = cosine similarity on normalized vectors)
6. Persist index to `data/embeddings/faiss_index.bin`
7. Persist metadata to `data/embeddings/faiss_metadata.json`

### Load Strategy

On startup, `PolicyVectorStore.load_or_build()`:
1. If `faiss_index.bin` exists and policy count matches → load from disk
2. Otherwise → rebuild from DB

### Extending

To add new policies:
1. Add rows to `data/raw/store_policies.csv`
2. Re-run `python -m scripts.load_data`
3. Delete `data/embeddings/faiss_index.bin` to force rebuild (or restart the API)

To add a new product category:
1. Add rows to `data/raw/products.csv`
2. Re-run ingestion

---

## Adding a New Data Source

1. Create CSV in `data/raw/`
2. Create Pydantic validation schema in `app/schemas/`
3. Create ingester class extending `DataIngestionPipeline[T]`
4. Implement `_validate_row()` and `_insert_record()`
5. Register in `scripts/load_data.py`
6. Add quality monitor thresholds
