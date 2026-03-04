"""Add performance indexes for rating, stock ordering and review lookups.

Revision ID: 003
Revises: 002
Create Date: 2026-03-04
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def _index_exists(conn, table, index_name):
    inspector = sa_inspect(conn)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def upgrade():
    conn = op.get_bind()
    if not _index_exists(conn, "products", "idx_product_rating"):
        op.create_index("idx_product_rating", "products", ["rating"])
    if not _index_exists(conn, "products", "idx_product_stock"):
        op.create_index("idx_product_stock", "products", ["stock"])
    if not _index_exists(conn, "reviews", "idx_review_product_id"):
        op.create_index("idx_review_product_id", "reviews", ["product_id"])
    if not _index_exists(conn, "reviews", "idx_review_rating"):
        op.create_index("idx_review_rating", "reviews", ["rating"])


def downgrade():
    op.drop_index("idx_review_rating", "reviews")
    op.drop_index("idx_review_product_id", "reviews")
    op.drop_index("idx_product_stock", "products")
    op.drop_index("idx_product_rating", "products")
