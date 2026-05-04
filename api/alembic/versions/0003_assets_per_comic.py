"""scope assets per comic

Revision ID: 0003_assets_per_comic
Revises: 0002_text_block_colors
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_assets_per_comic"
down_revision = "0002_text_block_colors"
branch_labels = None
depends_on = None

SCHEMA = "bd"


def upgrade() -> None:
    op.execute(f"UPDATE {SCHEMA}.panels SET image_asset_id = NULL WHERE image_asset_id IS NOT NULL")
    op.execute(f"DELETE FROM {SCHEMA}.assets")

    op.add_column("assets", sa.Column("comic_id", postgresql.UUID(as_uuid=True), nullable=True), schema=SCHEMA)
    op.execute(
        f"""
        UPDATE {SCHEMA}.assets a
        SET comic_id = c.id
        FROM {SCHEMA}.comics c
        WHERE c.user_id = a.user_id
        """
    )
    op.alter_column("assets", "comic_id", nullable=False, schema=SCHEMA)
    op.create_foreign_key(
        "fk_assets_comic_id",
        "assets",
        "comics",
        ["comic_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="CASCADE",
    )
    op.create_index("ix_assets_comic_id", "assets", ["comic_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_assets_comic_id", table_name="assets", schema=SCHEMA)
    op.drop_constraint("fk_assets_comic_id", "assets", schema=SCHEMA, type_="foreignkey")
    op.drop_column("assets", "comic_id", schema=SCHEMA)
