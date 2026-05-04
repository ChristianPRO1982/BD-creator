"""add text block color fields

Revision ID: 0002_text_block_colors
Revises: 0001_initial
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_text_block_colors"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

SCHEMA = "bd"


def upgrade() -> None:
    op.add_column(
        "text_blocks",
        sa.Column("text_color", sa.String(length=16), nullable=False, server_default="#000000"),
        schema=SCHEMA,
    )
    op.add_column(
        "text_blocks",
        sa.Column("background_color", sa.String(length=16), nullable=False, server_default="#ffffff"),
        schema=SCHEMA,
    )
    op.add_column(
        "text_blocks",
        sa.Column("background_opacity", sa.Float(), nullable=False, server_default="1"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("text_blocks", "background_opacity", schema=SCHEMA)
    op.drop_column("text_blocks", "background_color", schema=SCHEMA)
    op.drop_column("text_blocks", "text_color", schema=SCHEMA)
