from __future__ import annotations

import datetime as dt
import html
import uuid

from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Comic, Page, Panel, TextBlock
from app.storage.s3 import storage


def _hex_to_rgba(color: str, opacity: float) -> str:
    color = color.lstrip("#")
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {opacity:.3f})"


def _bubble_style_css(style: str) -> str:
    if style == "tail_top_left":
        return "border-top-left-radius:0px;"
    if style == "tail_top_right":
        return "border-top-right-radius:0px;"
    if style == "tail_bottom_left":
        return "border-bottom-left-radius:0px;"
    if style == "tail_bottom_right":
        return "border-bottom-right-radius:0px;"
    if style == "thought":
        return "border:2px dashed rgba(0,0,0,0.75);"
    return ""


def _page_html(page: Page, panels: list[Panel]) -> str:
    template = page.template
    panel_divs = []
    for panel in panels:
        slot = panel.slot
        text_html = "".join(
            (
                f"<div style='position:absolute;left:{tb.x*100:.2f}%;top:{tb.y*100:.2f}%;"
                f"width:{tb.width*100:.2f}%;height:{tb.height*100:.2f}%;"
                f"font-size:{tb.font_size}px;color:{tb.text_color};"
                f"background:{_hex_to_rgba(tb.background_color, tb.background_opacity)};"
                f"padding:6px;border-radius:8px;overflow:hidden;{_bubble_style_css(tb.bubble_style)}'>"
                f"{html.escape(tb.content)}</div>"
            )
            for tb in panel.text_blocks
        )
        panel_divs.append(
            (
                f"<div style='position:relative;border:2px solid #111;background:#f9f9f9;"
                f"grid-column:{slot.col_start} / span {slot.col_span};"
                f"grid-row:{slot.row_start} / span {slot.row_span};overflow:hidden;'>"
                f"{text_html}</div>"
            )
        )

    return (
        "<html><body style='margin:0;background:#fff;'>"
        f"<div style='width:100%;height:100%;display:grid;grid-template-columns:repeat({template.columns},1fr);"
        f"grid-template-rows:repeat({template.rows},1fr);gap:10px;padding:20px;box-sizing:border-box;'>"
        + "".join(panel_divs)
        + "</div></body></html>"
    )


async def render_missing_artifacts(db: Session, comic_id: uuid.UUID, owner_id: uuid.UUID) -> int:
    comic = db.scalar(select(Comic).where(Comic.id == comic_id, Comic.user_id == owner_id))
    if comic is None:
        return 0

    pages = db.scalars(
        select(Page)
        .where(Page.comic_id == comic.id)
        .options(
            joinedload(Page.template),
            joinedload(Page.panels).joinedload(Panel.slot),
            joinedload(Page.panels).joinedload(Panel.text_blocks),
        )
        .order_by(Page.page_number)
    ).unique().all()

    to_generate = [page for page in pages if not page.rendered_image_url]
    if not to_generate:
        return 0

    storage.ensure_bucket()
    generated = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for page in to_generate:
                html_content = _page_html(page, page.panels)
                browser_page = await browser.new_page(
                    viewport={"width": comic.export_width, "height": comic.export_height}
                )
                await browser_page.set_content(html_content)
                image = await browser_page.screenshot(type="jpeg", quality=comic.export_quality, full_page=True)
                await browser_page.close()

                key = f"comics/{comic.id}/pages/{page.id}.jpg"
                url = storage.upload_bytes(key, image, "image/jpeg")
                page.rendered_image_url = url
                page.artifact_generated_at = dt.datetime.utcnow()
                db.add(page)
                generated += 1
        finally:
            await browser.close()

    db.commit()
    return generated
