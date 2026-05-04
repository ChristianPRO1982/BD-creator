"""add template hierarchy and install metadata

Revision ID: 0004_template_hierarchy
Revises: 0003_assets_per_comic
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision = "0004_template_hierarchy"
down_revision = "0003_assets_per_comic"
branch_labels = None
depends_on = None

SCHEMA = "bd"


def upgrade() -> None:
    op.create_table(
        "template_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey(f"{SCHEMA}.template_groups.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=SCHEMA,
    )
    op.create_index("ix_template_groups_parent_id", "template_groups", ["parent_id"], schema=SCHEMA)

    op.add_column("templates", sa.Column("group_id", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column("templates", sa.Column("source_filename", sa.String(length=255), nullable=True), schema=SCHEMA)
    op.add_column("templates", sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA)
    op.add_column("templates", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), schema=SCHEMA)

    conn = op.get_bind()
    root_group_id = conn.execute(
        text(
            f"""
            INSERT INTO {SCHEMA}.template_groups (name, parent_id, sort_order)
            VALUES ('Classique', NULL, 1)
            RETURNING id
            """
        )
    ).scalar_one()

    base_group_id = conn.execute(
        text(
            f"""
            INSERT INTO {SCHEMA}.template_groups (name, parent_id, sort_order)
            VALUES ('Base', :parent_id, 1)
            RETURNING id
            """
        ),
        {"parent_id": root_group_id},
    ).scalar_one()

    conn.execute(
        text(
            f"""
            UPDATE {SCHEMA}.templates
            SET group_id = :group_id,
                source_filename = 'legacy-seed',
                installed_at = now()
            """
        ),
        {"group_id": base_group_id},
    )

    op.alter_column("templates", "group_id", nullable=False, schema=SCHEMA)
    op.alter_column("templates", "source_filename", nullable=False, schema=SCHEMA)
    op.alter_column("templates", "installed_at", nullable=False, schema=SCHEMA)

    op.create_foreign_key(
        "fk_templates_group_id",
        "templates",
        "template_groups",
        ["group_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.execute(f"ALTER TABLE {SCHEMA}.templates DROP CONSTRAINT IF EXISTS templates_name_key")


def downgrade() -> None:
    op.drop_constraint("fk_templates_group_id", "templates", schema=SCHEMA, type_="foreignkey")
    op.drop_column("templates", "sort_order", schema=SCHEMA)
    op.drop_column("templates", "installed_at", schema=SCHEMA)
    op.drop_column("templates", "source_filename", schema=SCHEMA)
    op.drop_column("templates", "group_id", schema=SCHEMA)

    op.drop_index("ix_template_groups_parent_id", table_name="template_groups", schema=SCHEMA)
    op.drop_table("template_groups", schema=SCHEMA)
