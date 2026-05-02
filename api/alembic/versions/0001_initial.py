"""initial bd schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA = "bd"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "comics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("export_width", sa.Integer(), nullable=False, server_default="2480"),
        sa.Column("export_height", sa.Integer(), nullable=False, server_default="3508"),
        sa.Column("export_quality", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=SCHEMA,
    )
    op.create_index("ix_comics_user_id", "comics", ["user_id"], schema=SCHEMA)

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("columns", sa.Integer(), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("col_start", sa.Integer(), nullable=False),
        sa.Column("row_start", sa.Integer(), nullable=False),
        sa.Column("col_span", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("row_span", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("geometry_type", sa.String(length=24), nullable=False, server_default="rectangle"),
        schema=SCHEMA,
    )

    op.create_table(
        "pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("comic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.comics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.templates.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("rendered_image_url", sa.String(length=1024), nullable=True),
        sa.Column("artifact_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("comic_id", "page_number", name="uq_pages_comic_page_number"),
        schema=SCHEMA,
    )
    op.create_index("ix_pages_comic_id", "pages", ["comic_id"], schema=SCHEMA)

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=SCHEMA,
    )
    op.create_index("ix_assets_user_id", "assets", ["user_id"], schema=SCHEMA)

    op.create_table(
        "panels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.slots.id"), nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("image_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.assets.id"), nullable=True),
        sa.Column("crop_zoom", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("crop_offset_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("crop_offset_y", sa.Float(), nullable=False, server_default="0.0"),
        schema=SCHEMA,
    )
    op.create_index("ix_panels_page_id", "panels", ["page_id"], schema=SCHEMA)

    op.create_table(
        "text_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("panel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.panels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("y", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("width", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("height", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("font_size", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("bubble_style", sa.String(length=32), nullable=False, server_default="speech"),
        schema=SCHEMA,
    )
    op.create_index("ix_text_blocks_panel_id", "text_blocks", ["panel_id"], schema=SCHEMA)

    op.execute(
        f"""
        INSERT INTO {SCHEMA}.templates (id, name, columns, rows) VALUES
        (1, '1 case', 1, 1),
        (2, '2 vertical', 2, 1),
        (3, '2 horizontal', 1, 2),
        (4, '3 cases', 3, 1),
        (5, '4 cases', 2, 2)
        """
    )

    op.execute(
        f"""
        INSERT INTO {SCHEMA}.slots
        (id, template_id, col_start, row_start, col_span, row_span, geometry_type) VALUES
        (1, 1, 1, 1, 1, 1, 'rectangle'),
        (2, 2, 1, 1, 1, 1, 'rectangle'),
        (3, 2, 2, 1, 1, 1, 'rectangle'),
        (4, 3, 1, 1, 1, 1, 'rectangle'),
        (5, 3, 1, 2, 1, 1, 'rectangle'),
        (6, 4, 1, 1, 1, 1, 'rectangle'),
        (7, 4, 2, 1, 1, 1, 'rectangle'),
        (8, 4, 3, 1, 1, 1, 'rectangle'),
        (9, 5, 1, 1, 1, 1, 'rectangle'),
        (10, 5, 2, 1, 1, 1, 'rectangle'),
        (11, 5, 1, 2, 1, 1, 'rectangle'),
        (12, 5, 2, 2, 1, 1, 'rectangle')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_text_blocks_panel_id", table_name="text_blocks", schema=SCHEMA)
    op.drop_table("text_blocks", schema=SCHEMA)
    op.drop_index("ix_panels_page_id", table_name="panels", schema=SCHEMA)
    op.drop_table("panels", schema=SCHEMA)
    op.drop_index("ix_assets_user_id", table_name="assets", schema=SCHEMA)
    op.drop_table("assets", schema=SCHEMA)
    op.drop_index("ix_pages_comic_id", table_name="pages", schema=SCHEMA)
    op.drop_table("pages", schema=SCHEMA)
    op.drop_table("slots", schema=SCHEMA)
    op.drop_table("templates", schema=SCHEMA)
    op.drop_index("ix_comics_user_id", table_name="comics", schema=SCHEMA)
    op.drop_table("comics", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
