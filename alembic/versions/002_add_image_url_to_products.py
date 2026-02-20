"""add image_url to products (safe migration)

Revision ID: 002
Revises: 001
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" not in columns:
        op.add_column(
            "products",
            sa.Column("image_url", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("products")]
    if "image_url" in columns:
        op.drop_column("products", "image_url")
