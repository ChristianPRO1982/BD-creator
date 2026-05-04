from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, require_user
from app.api.schemas import (
    AssetOut,
    ComicCreate,
    ComicOut,
    ComicUpdate,
    PageCreate,
    PageOut,
    PageUpdate,
    PanelOut,
    PanelUpdate,
    TemplateOut,
    TextBlockCreate,
    TextBlockOut,
    TextBlockUpdate,
)
from app.api.utils import invalidate_page_artifact, validate_hex_color, validate_opacity, validate_text_bounds
from app.db.models import Asset, Comic, Page, Panel, Slot, Template, TextBlock
from app.db.session import get_db
from app.render.service import render_missing_artifacts
from app.storage.s3 import storage

router = APIRouter(prefix="/api")


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_user)):
    return db.scalars(select(Template).options(joinedload(Template.slots)).order_by(Template.id)).unique().all()


@router.get("/comics", response_model=list[ComicOut])
def list_comics(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    return db.scalars(select(Comic).where(Comic.user_id == user.user_uuid).order_by(Comic.created_at.desc())).all()


@router.post("/comics", response_model=ComicOut)
def create_comic(payload: ComicCreate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = Comic(
        user_id=user.user_uuid,
        name=payload.name,
        export_width=payload.export_width,
        export_height=payload.export_height,
        export_quality=payload.export_quality,
    )
    db.add(comic)
    db.commit()
    db.refresh(comic)
    return comic


@router.get("/comics/{comic_id}", response_model=ComicOut)
def get_comic(comic_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = db.scalar(select(Comic).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")
    return comic


@router.patch("/comics/{comic_id}", response_model=ComicOut)
def update_comic(comic_id: uuid.UUID, payload: ComicUpdate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = db.scalar(select(Comic).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(comic, key, value)
    db.add(comic)
    db.commit()
    db.refresh(comic)
    return comic


@router.delete("/comics/{comic_id}")
def delete_comic(comic_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = db.scalar(select(Comic).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")
    db.delete(comic)
    db.commit()
    return {"ok": True}


@router.get("/comics/{comic_id}/pages", response_model=list[PageOut])
def list_pages(comic_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = db.scalar(select(Comic.id).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")
    return db.scalars(select(Page).where(Page.comic_id == comic_id).order_by(Page.page_number)).all()


@router.post("/comics/{comic_id}/pages", response_model=PageOut)
def create_page(comic_id: uuid.UUID, payload: PageCreate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    comic = db.scalar(select(Comic).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")

    template = db.get(Template, payload.template_id)
    if template is None:
        raise HTTPException(status_code=400, detail="Invalid template")

    page = Page(comic_id=comic_id, template_id=payload.template_id, page_number=payload.page_number, status="draft")
    db.add(page)
    db.flush()

    slots = db.scalars(select(Slot).where(Slot.template_id == template.id).order_by(Slot.id)).all()
    for idx, slot in enumerate(slots, start=1):
        db.add(Panel(page_id=page.id, slot_id=slot.id, reading_order=idx))

    db.commit()
    db.refresh(page)
    return page


@router.get("/pages/{page_id}", response_model=PageOut)
def get_page(page_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.patch("/pages/{page_id}", response_model=PageOut)
def update_page(page_id: uuid.UUID, payload: PageUpdate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(page, key, value)

    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.post("/pages/{page_id}/validate", response_model=PageOut)
def validate_page(page_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    page.status = "validated"
    db.commit()
    db.refresh(page)
    return page


@router.post("/pages/{page_id}/unvalidate", response_model=PageOut)
def unvalidate_page(page_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    page.status = "draft"
    page.rendered_image_url = None
    page.artifact_generated_at = None
    db.commit()
    db.refresh(page)
    return page


@router.get("/pages/{page_id}/panels", response_model=list[PanelOut])
def list_panels(page_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page.id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return db.scalars(select(Panel).where(Panel.page_id == page_id).order_by(Panel.reading_order)).all()


@router.get("/pages/{page_id}/text-blocks", response_model=list[TextBlockOut])
def list_page_text_blocks(page_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    page = db.scalar(
        select(Page.id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Page.id == page_id, Comic.user_id == user.user_uuid)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return db.scalars(
        select(TextBlock)
        .join(Panel, Panel.id == TextBlock.panel_id)
        .where(Panel.page_id == page_id)
        .order_by(Panel.reading_order)
    ).all()


@router.patch("/panels/{panel_id}", response_model=PanelOut)
def update_panel(panel_id: uuid.UUID, payload: PanelUpdate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    panel = db.scalar(
        select(Panel)
        .join(Page, Page.id == Panel.page_id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Panel.id == panel_id, Comic.user_id == user.user_uuid)
    )
    if panel is None:
        raise HTTPException(status_code=404, detail="Panel not found")
    if panel.page.status == "validated":
        raise HTTPException(status_code=409, detail="Cannot edit a validated page")
    if payload.image_asset_id is not None:
        asset = db.scalar(
            select(Asset)
            .where(Asset.id == payload.image_asset_id, Asset.comic_id == panel.page.comic_id)
        )
        if asset is None:
            raise HTTPException(status_code=400, detail="Selected asset does not belong to this comic")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(panel, key, value)
    invalidate_page_artifact(db, panel.page_id)
    db.add(panel)
    db.commit()
    db.refresh(panel)
    return panel


@router.get("/panels/{panel_id}/text-blocks", response_model=list[TextBlockOut])
def list_text_blocks(panel_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    panel = db.scalar(
        select(Panel.id)
        .join(Page, Page.id == Panel.page_id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Panel.id == panel_id, Comic.user_id == user.user_uuid)
    )
    if panel is None:
        raise HTTPException(status_code=404, detail="Panel not found")
    return db.scalars(select(TextBlock).where(TextBlock.panel_id == panel_id)).all()


@router.post("/panels/{panel_id}/text-blocks", response_model=TextBlockOut)
def create_text_block(panel_id: uuid.UUID, payload: TextBlockCreate, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    panel = db.scalar(
        select(Panel)
        .join(Page, Page.id == Panel.page_id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(Panel.id == panel_id, Comic.user_id == user.user_uuid)
    )
    if panel is None:
        raise HTTPException(status_code=404, detail="Panel not found")
    if panel.page.status == "validated":
        raise HTTPException(status_code=409, detail="Cannot edit a validated page")
    try:
        validate_text_bounds(payload.x, payload.y, payload.width, payload.height)
        validate_hex_color(payload.text_color)
        validate_hex_color(payload.background_color)
        validate_opacity(payload.background_opacity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    text_block = TextBlock(panel_id=panel_id, **payload.model_dump())
    db.add(text_block)
    invalidate_page_artifact(db, panel.page_id)
    db.commit()
    db.refresh(text_block)
    return text_block


@router.patch("/panels/{panel_id}/text-blocks/{text_block_id}", response_model=TextBlockOut)
def update_text_block(
    panel_id: uuid.UUID,
    text_block_id: uuid.UUID,
    payload: TextBlockUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    text_block = db.scalar(
        select(TextBlock)
        .join(Panel, Panel.id == TextBlock.panel_id)
        .join(Page, Page.id == Panel.page_id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(TextBlock.id == text_block_id, TextBlock.panel_id == panel_id, Comic.user_id == user.user_uuid)
    )
    if text_block is None:
        raise HTTPException(status_code=404, detail="Text block not found")
    if text_block.panel.page.status == "validated":
        raise HTTPException(status_code=409, detail="Cannot edit a validated page")

    merged = text_block.__dict__.copy()
    merged.update(payload.model_dump(exclude_unset=True))
    try:
        validate_text_bounds(merged["x"], merged["y"], merged["width"], merged["height"])
        validate_hex_color(merged["text_color"])
        validate_hex_color(merged["background_color"])
        validate_opacity(merged["background_opacity"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(text_block, key, value)

    invalidate_page_artifact(db, text_block.panel.page_id)
    db.add(text_block)
    db.commit()
    db.refresh(text_block)
    return text_block


@router.delete("/panels/{panel_id}/text-blocks/{text_block_id}")
def delete_text_block(
    panel_id: uuid.UUID,
    text_block_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    text_block = db.scalar(
        select(TextBlock)
        .join(Panel, Panel.id == TextBlock.panel_id)
        .join(Page, Page.id == Panel.page_id)
        .join(Comic, Comic.id == Page.comic_id)
        .where(TextBlock.id == text_block_id, TextBlock.panel_id == panel_id, Comic.user_id == user.user_uuid)
    )
    if text_block is None:
        raise HTTPException(status_code=404, detail="Text block not found")
    if text_block.panel.page.status == "validated":
        raise HTTPException(status_code=409, detail="Cannot edit a validated page")

    page_id = text_block.panel.page_id
    db.delete(text_block)
    invalidate_page_artifact(db, page_id)
    db.commit()
    return {"ok": True}


@router.post("/comics/{comic_id}/assets/upload", response_model=AssetOut)
def upload_comic_asset(
    comic_id: uuid.UUID,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    comic = db.scalar(select(Comic.id).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")

    storage.ensure_bucket()
    content = file.file.read()
    safe_name = name or file.filename or "asset"

    count = db.scalar(select(func.count(Asset.id)).where(Asset.comic_id == comic_id)) or 0
    key = f"comics/{comic_id}/assets/{count + 1}_{safe_name}"
    file_url = storage.upload_bytes(key, content, file.content_type or "application/octet-stream")

    asset = Asset(comic_id=comic_id, user_id=user.user_uuid, name=safe_name, file_path=file_url)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/comics/{comic_id}/assets", response_model=list[AssetOut])
def list_comic_assets(
    comic_id: uuid.UUID,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    comic = db.scalar(select(Comic.id).where(Comic.id == comic_id, Comic.user_id == user.user_uuid))
    if comic is None:
        raise HTTPException(status_code=404, detail="Comic not found")
    stmt = select(Asset).where(Asset.comic_id == comic_id)
    if search:
        stmt = stmt.where(Asset.name.ilike(f"%{search}%"))
    return db.scalars(stmt.order_by(Asset.name.asc())).all()


@router.post("/render/comics/{comic_id}/generate-missing")
async def render_comic_missing(comic_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    generated = await render_missing_artifacts(db, comic_id, user.user_uuid)
    return {"generated": generated}
