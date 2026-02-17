"""initial schema with products reviews and policies

Revision ID: 001
Revises:
Create Date: 2026-02-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Products table
    op.create_table(
        "products",
        sa.Column("product_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_index(op.f("ix_products_product_id"), "products", ["product_id"])
    op.create_index(op.f("ix_products_name"), "products", ["name"])
    op.create_index(op.f("ix_products_brand"), "products", ["brand"])
    op.create_index(op.f("ix_products_category"), "products", ["category"])
    op.create_index("idx_product_category_brand", "products", ["category", "brand"])
    op.create_index("idx_product_price", "products", ["price"])

    # Reviews table
    op.create_table(
        "reviews",
        sa.Column("review_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="CASCADE"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index(op.f("ix_reviews_review_id"), "reviews", ["review_id"])
    op.create_index(op.f("ix_reviews_product_id"), "reviews", ["product_id"])
    op.create_index("idx_review_product_rating", "reviews", ["product_id", "rating"])
    op.create_index("idx_review_sentiment", "reviews", ["sentiment"])
    op.create_index("idx_review_timestamp", "reviews", ["timestamp"])

    # Policies table
    op.create_table(
        "policies",
        sa.Column("policy_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("policy_id"),
    )
    op.create_index(op.f("ix_policies_policy_id"), "policies", ["policy_id"])
    op.create_index(op.f("ix_policies_category"), "policies", ["category"])
    op.create_index(op.f("ix_policies_effective_date"), "policies", ["effective_date"])
    op.create_index("idx_policy_category_effective", "policies", ["category", "effective_date"])


def downgrade() -> None:
    op.drop_table("policies")
    op.drop_table("reviews")
    op.drop_table("products")
