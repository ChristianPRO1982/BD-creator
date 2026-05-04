from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

SCHEMA = "bd"


class Comic(Base):
    __tablename__ = "comics"
    __table_args__ = (
        Index("ix_comics_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    export_width: Mapped[int] = mapped_column(Integer, default=2480, nullable=False)
    export_height: Mapped[int] = mapped_column(Integer, default=3508, nullable=False)
    export_quality: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow, nullable=False)

    pages: Mapped[list[Page]] = relationship(back_populates="comic", cascade="all, delete-orphan")


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    columns: Mapped[int] = mapped_column(Integer, nullable=False)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)

    slots: Mapped[list[Slot]] = relationship(back_populates="template", cascade="all, delete-orphan")


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.templates.id", ondelete="CASCADE"), nullable=False)
    col_start: Mapped[int] = mapped_column(Integer, nullable=False)
    row_start: Mapped[int] = mapped_column(Integer, nullable=False)
    col_span: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    row_span: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(24), default="rectangle", nullable=False)

    template: Mapped[Template] = relationship(back_populates="slots")


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("comic_id", "page_number", name="uq_pages_comic_page_number"),
        Index("ix_pages_comic_id", "comic_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.comics.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.templates.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    rendered_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artifact_generated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comic: Mapped[Comic] = relationship(back_populates="pages")
    template: Mapped[Template] = relationship()
    panels: Mapped[list[Panel]] = relationship(back_populates="page", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow, nullable=False)


class Panel(Base):
    __tablename__ = "panels"
    __table_args__ = (
        Index("ix_panels_page_id", "page_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.pages.id", ondelete="CASCADE"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.slots.id"), nullable=False)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False)
    image_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{SCHEMA}.assets.id"), nullable=True)
    crop_zoom: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    crop_offset_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    crop_offset_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    page: Mapped[Page] = relationship(back_populates="panels")
    slot: Mapped[Slot] = relationship()
    image_asset: Mapped[Asset | None] = relationship()
    text_blocks: Mapped[list[TextBlock]] = relationship(back_populates="panel", cascade="all, delete-orphan")


class TextBlock(Base):
    __tablename__ = "text_blocks"
    __table_args__ = (
        Index("ix_text_blocks_panel_id", "panel_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    panel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{SCHEMA}.panels.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    width: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    height: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    font_size: Mapped[int] = mapped_column(Integer, default=16, nullable=False)
    bubble_style: Mapped[str] = mapped_column(String(32), default="speech", nullable=False)
    text_color: Mapped[str] = mapped_column(String(16), default="#000000", nullable=False)
    background_color: Mapped[str] = mapped_column(String(16), default="#ffffff", nullable=False)
    background_opacity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    panel: Mapped[Panel] = relationship(back_populates="text_blocks")
