from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
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
    TemplateGroupCreate,
    TemplateGroupOut,
    TemplateGroupUpdate,
    TemplateOut,
    TextBlockCreate,
    TextBlockOut,
    TextBlockUpdate,
)
from app.api.utils import (
    invalidate_page_artifact,
    validate_hex_color,
    validate_opacity,
    validate_template_payload,
    validate_text_bounds,
)
from app.db.models import Asset, Comic, Page, Panel, Slot, Template, TemplateGroup, TextBlock
from app.db.session import get_db
from app.render.service import render_missing_artifacts
from app.storage.s3 import storage

router = APIRouter(prefix="/api")


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_user)):
    templates = db.scalars(
        select(Template)
        .options(joinedload(Template.slots), joinedload(Template.group).joinedload(TemplateGroup.parent))
        .order_by(Template.sort_order, Template.name, Template.id)
    ).unique().all()
    return [
        TemplateOut(
            id=template.id,
            name=template.name,
            columns=template.columns,
            rows=template.rows,
            group_id=template.group_id,
            group_name=template.group.name,
            parent_group_id=template.group.parent_id,
            parent_group_name=template.group.parent.name if template.group.parent is not None else None,
            source_filename=template.source_filename,
            installed_at=template.installed_at,
            sort_order=template.sort_order,
            slots=template.slots,
        )
        for template in templates
    ]


@router.get("/template-groups", response_model=list[TemplateGroupOut])
def list_template_groups(db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_user)):
    return db.scalars(
        select(TemplateGroup).order_by(TemplateGroup.parent_id.nullsfirst(), TemplateGroup.sort_order, TemplateGroup.name, TemplateGroup.id)
    ).all()


@router.post("/template-groups", response_model=TemplateGroupOut)
def create_template_group(
    payload: TemplateGroupCreate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_user),
):
    if payload.parent_id is not None:
        parent = db.get(TemplateGroup, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent group not found")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="A subgroup cannot contain another subgroup")
    group = TemplateGroup(name=payload.name.strip(), parent_id=payload.parent_id, sort_order=payload.sort_order)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.patch("/template-groups/{group_id}", response_model=TemplateGroupOut)
def update_template_group(
    group_id: int,
    payload: TemplateGroupUpdate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_user),
):
    group = db.get(TemplateGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Template group not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        group.name = data["name"].strip()
    if "sort_order" in data and data["sort_order"] is not None:
        group.sort_order = data["sort_order"]
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/template-groups/{group_id}")
def delete_template_group(group_id: int, db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_user)):
    group = db.get(TemplateGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Template group not found")
    if group.parent_id is None:
        subgroups_count = db.scalar(select(func.count()).select_from(TemplateGroup).where(TemplateGroup.parent_id == group_id)) or 0
        if subgroups_count > 0:
            raise HTTPException(status_code=409, detail="Impossible de supprimer ce groupe : il contient des sous-groupes.")
    else:
        templates_count = db.scalar(select(func.count()).select_from(Template).where(Template.group_id == group_id)) or 0
        if templates_count > 0:
            raise HTTPException(status_code=409, detail="Impossible de supprimer ce sous-groupe : il contient des gabarits.")
    db.delete(group)
    db.commit()
    return {"ok": True}


@router.post("/templates/install", response_model=TemplateOut)
async def install_template(
    group_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_user),
):
    group = db.get(TemplateGroup, group_id)
    if group is None:
        raise HTTPException(status_code=400, detail="Invalid group_id")
    if group.parent_id is None:
        raise HTTPException(status_code=400, detail="group_id must reference a subgroup")

    raw = await file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON template file") from exc

    try:
        name, columns, rows, slots = validate_template_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    next_sort_order = (db.scalar(select(func.coalesce(func.max(Template.sort_order), 0)).where(Template.group_id == group_id)) or 0) + 1
    template = Template(
        group_id=group_id,
        name=name,
        columns=columns,
        rows=rows,
        source_filename=file.filename or "template.json",
        sort_order=next_sort_order,
    )
    db.add(template)
    db.flush()

    for slot in slots:
        db.add(
            Slot(
                template_id=template.id,
                col_start=int(slot["col_start"]),
                row_start=int(slot["row_start"]),
                col_span=int(slot["col_span"]),
                row_span=int(slot["row_span"]),
                geometry_type=str(slot["geometry_type"]),
            )
        )

    db.commit()
    db.refresh(template)
    template = db.scalar(
        select(Template)
        .where(Template.id == template.id)
        .options(joinedload(Template.slots), joinedload(Template.group).joinedload(TemplateGroup.parent))
    )
    assert template is not None
    return TemplateOut(
        id=template.id,
        name=template.name,
        columns=template.columns,
        rows=template.rows,
        group_id=template.group_id,
        group_name=template.group.name,
        parent_group_id=template.group.parent_id,
        parent_group_name=template.group.parent.name if template.group.parent is not None else None,
        source_filename=template.source_filename,
        installed_at=template.installed_at,
        sort_order=template.sort_order,
        slots=template.slots,
    )


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_user)):
    template = db.get(Template, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    in_use = db.scalar(select(func.count()).select_from(Page).where(Page.template_id == template_id)) or 0
    if in_use > 0:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer ce gabarit : il est utilisé par une ou plusieurs planches.",
        )
    db.delete(template)
    db.commit()
    return {"ok": True}


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
    comic_assets = db.scalars(select(Asset).where(Asset.comic_id == comic_id)).all()
    for asset in comic_assets:
        key = storage.key_from_url(asset.file_path)
        if not key:
            continue
        try:
            storage.delete_object(key)
        except Exception:
            # Keep DB deletion as source of truth even if object storage cleanup fails.
            pass
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


@router.get("/assets/{asset_id}/content")
def get_asset_content(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    asset = db.scalar(
        select(Asset)
        .join(Comic, Comic.id == Asset.comic_id)
        .where(Asset.id == asset_id, Comic.user_id == user.user_uuid)
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    key = storage.key_from_url(asset.file_path)
    if not key:
        raise HTTPException(status_code=404, detail="Asset file is missing")
    try:
        data, content_type = storage.download_bytes(key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Asset file is missing") from exc
    return Response(content=data, media_type=content_type)


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_user),
):
    asset = db.scalar(
        select(Asset)
        .join(Comic, Comic.id == Asset.comic_id)
        .where(Asset.id == asset_id, Comic.user_id == user.user_uuid)
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    panel_in_use = db.scalar(select(Panel.id).where(Panel.image_asset_id == asset_id).limit(1))
    if panel_in_use is not None:
        raise HTTPException(status_code=409, detail="Asset is used by one or more panels")

    key = storage.key_from_url(asset.file_path)
    if key:
        try:
            storage.delete_object(key)
        except Exception:
            pass
    db.delete(asset)
    db.commit()
    return {"ok": True}


@router.post("/render/comics/{comic_id}/generate-missing")
async def render_comic_missing(comic_id: uuid.UUID, db: Session = Depends(get_db), user: AuthenticatedUser = Depends(require_user)):
    generated = await render_missing_artifacts(db, comic_id, user.user_uuid)
    return {"generated": generated}
