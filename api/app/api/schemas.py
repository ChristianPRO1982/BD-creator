from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class ComicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    export_width: int = 2480
    export_height: int = 3508
    export_quality: int = 90


class ComicUpdate(BaseModel):
    name: str | None = None
    export_width: int | None = None
    export_height: int | None = None
    export_quality: int | None = None


class ComicOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    export_width: int
    export_height: int
    export_quality: int
    created_at: dt.datetime

    class Config:
        from_attributes = True


class PageCreate(BaseModel):
    template_id: int
    page_number: int


class PageUpdate(BaseModel):
    status: str | None = None


class PageOut(BaseModel):
    id: uuid.UUID
    comic_id: uuid.UUID
    template_id: int
    page_number: int
    status: str
    rendered_image_url: str | None
    artifact_generated_at: dt.datetime | None

    class Config:
        from_attributes = True


class PanelUpdate(BaseModel):
    image_asset_id: uuid.UUID | None = None
    crop_zoom: float = 1.0
    crop_offset_x: float = 0.0
    crop_offset_y: float = 0.0


class PanelOut(BaseModel):
    id: uuid.UUID
    page_id: uuid.UUID
    slot_id: int
    reading_order: int
    image_asset_id: uuid.UUID | None
    crop_zoom: float
    crop_offset_x: float
    crop_offset_y: float

    class Config:
        from_attributes = True


class TextBlockCreate(BaseModel):
    content: str
    x: float
    y: float
    width: float
    height: float
    font_size: int = 16
    bubble_style: str = "speech"
    text_color: str = "#000000"
    background_color: str = "#ffffff"
    background_opacity: float = 1.0


class TextBlockUpdate(BaseModel):
    content: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    font_size: int | None = None
    bubble_style: str | None = None
    text_color: str | None = None
    background_color: str | None = None
    background_opacity: float | None = None


class TextBlockOut(BaseModel):
    id: uuid.UUID
    panel_id: uuid.UUID
    content: str
    x: float
    y: float
    width: float
    height: float
    font_size: int
    bubble_style: str
    text_color: str
    background_color: str
    background_opacity: float

    class Config:
        from_attributes = True


class TemplateSlotOut(BaseModel):
    id: int
    col_start: int
    row_start: int
    col_span: int
    row_span: int
    geometry_type: str

    class Config:
        from_attributes = True


class TemplateOut(BaseModel):
    id: int
    name: str
    columns: int
    rows: int
    slots: list[TemplateSlotOut]

    class Config:
        from_attributes = True


class AssetOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    file_path: str
    created_at: dt.datetime

    class Config:
        from_attributes = True
