import { ChangeEvent, FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { PanelCanvas } from "../components/PanelCanvas";
import { api } from "../services/api";
import { Asset, Page, Panel, Template, TextBlock } from "../types";

type TextBlocksByPanelId = Record<string, TextBlock[]>;

type DragState = {
  textBlockId: string;
  panelId: string;
  startMouseX: number;
  startMouseY: number;
  startX: number;
  startY: number;
  width: number;
  height: number;
} | null;

type BubbleTail = "none" | "tail_top_left" | "tail_top_right" | "tail_bottom_left" | "tail_bottom_right";

function parseBubbleStyle(style: string): { thought: boolean; tail: BubbleTail } {
  const raw = (style || "none").trim();
  const parts = raw.split("|").map((p) => p.trim()).filter(Boolean);
  const thought = parts.includes("thought");
  const tail = (
    parts.find((p) =>
      ["tail_top_left", "tail_top_right", "tail_bottom_left", "tail_bottom_right"].includes(p)
    ) || (["tail_top_left", "tail_top_right", "tail_bottom_left", "tail_bottom_right"].includes(raw) ? raw : "none")
  ) as BubbleTail;
  return { thought, tail };
}

function makeBubbleStyle(thought: boolean, tail: BubbleTail): string {
  const parts: string[] = [];
  if (thought) parts.push("thought");
  if (tail !== "none") parts.push(tail);
  if (!parts.length) return "none";
  return parts.join("|");
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function shiftPanelCrop(panel: Panel, axis: "x" | "y", delta: number) {
  if (axis === "x") {
    return { ...panel, crop_offset_x: clamp(panel.crop_offset_x + delta, -1, 1) };
  }
  return { ...panel, crop_offset_y: clamp(panel.crop_offset_y + delta, -1, 1) };
}

export function PageEditorPage() {
  const { pageId } = useParams<{ pageId: string }>();
  const { t } = useI18n();
  const [page, setPage] = useState<Page | null>(null);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [template, setTemplate] = useState<Template | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetSearch, setAssetSearch] = useState("");
  const [assetsExpanded, setAssetsExpanded] = useState(false);
  const [activePanelId, setActivePanelId] = useState<string | null>(null);
  const [textBlocksByPanelId, setTextBlocksByPanelId] = useState<TextBlocksByPanelId>({});
  const [dragState, setDragState] = useState<DragState>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePanelSize, setActivePanelSize] = useState<{ width: number; height: number } | null>(null);
  const gridRef = useRef<HTMLDivElement | null>(null);

  const activePanel = useMemo(
    () => panels.find((panel) => panel.id === activePanelId) || null,
    [panels, activePanelId]
  );
  const activeSlot = useMemo(
    () => (activePanel ? template?.slots.find((s) => s.id === activePanel.slot_id) || null : null),
    [activePanel, template]
  );
  const activePanelAspectRatio = useMemo(() => {
    if (!activeSlot || !template) return undefined;
    const widthUnits = activeSlot.col_span / template.columns;
    const heightUnits = activeSlot.row_span / template.rows;
    if (heightUnits <= 0) return undefined;
    return widthUnits / heightUnits;
  }, [activeSlot, template]);

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    if (!q) return assets;
    return assets.filter((a) => a.name.toLowerCase().includes(q));
  }, [assets, assetSearch]);

  async function load() {
    if (!pageId) return;
    const p = await api.get<Page>(`/api/pages/${pageId}`);
    const [panelData, templateData, assetData, textBlocks] = await Promise.all([
      api.get<Panel[]>(`/api/pages/${pageId}/panels`),
      api.get<Template[]>("/api/templates"),
      api.get<Asset[]>(`/api/comics/${p.comic_id}/assets`),
      api.get<TextBlock[]>(`/api/pages/${pageId}/text-blocks`),
    ]);

    const grouped: TextBlocksByPanelId = {};
    for (const tb of textBlocks) {
      grouped[tb.panel_id] = grouped[tb.panel_id] || [];
      grouped[tb.panel_id].push(tb);
    }

    setPage(p);
    setPanels(panelData);
    setTemplate(templateData.find((tpl) => tpl.id === p.template_id) || null);
    setAssets(assetData);
    setTextBlocksByPanelId(grouped);
    setActivePanelId((prev) => prev || panelData[0]?.id || null);
  }

  async function loadAssets(search?: string) {
    if (!page) return;
    const query = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
    const data = await api.get<Asset[]>(`/api/comics/${page.comic_id}/assets${query}`);
    setAssets(data);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [pageId]);

  useEffect(() => {
    function syncActivePanelSize() {
      if (!gridRef.current || !activePanelId) {
        setActivePanelSize(null);
        return;
      }
      const selected = gridRef.current.querySelector<HTMLElement>(`[data-panel-id="${activePanelId}"]`);
      if (!selected) {
        setActivePanelSize(null);
        return;
      }
      const rect = selected.getBoundingClientRect();
      setActivePanelSize({ width: Math.round(rect.width), height: Math.round(rect.height) });
    }

    syncActivePanelSize();
    window.addEventListener("resize", syncActivePanelSize);
    return () => window.removeEventListener("resize", syncActivePanelSize);
  }, [activePanelId, panels, template]);

  useEffect(() => {
    if (!dragState) return;
    const state = dragState;

    function onMove(event: globalThis.MouseEvent) {
      setTextBlocksByPanelId((prev) => {
        const panelTexts = prev[state.panelId] || [];
        const next = panelTexts.map((tb) => {
          if (tb.id !== state.textBlockId) return tb;
          const nextX = clamp(state.startX + (event.clientX - state.startMouseX) / 320, 0, 1 - state.width);
          const nextY = clamp(state.startY + (event.clientY - state.startMouseY) / 320, 0, 1 - state.height);
          return { ...tb, x: nextX, y: nextY };
        });
        return { ...prev, [state.panelId]: next };
      });
    }

    async function onUp() {
      setDragState(null);
      const dragged = (textBlocksByPanelId[state.panelId] || []).find((tb) => tb.id === state.textBlockId);
      if (!dragged || !page || page.status === "validated") return;
      try {
        await api.patch<TextBlock>(`/api/panels/${state.panelId}/text-blocks/${state.textBlockId}`, {
          x: dragged.x,
          y: dragged.y,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        await load();
      }
    }

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp, { once: true });

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragState, textBlocksByPanelId, page]);

  async function updatePanel(panelId: string, patch: Partial<Panel>) {
    if (!page || page.status === "validated") return;
    const panel = panels.find((p) => p.id === panelId);
    if (!panel) return;

    const body = {
      image_asset_id: Object.prototype.hasOwnProperty.call(patch, "image_asset_id")
        ? patch.image_asset_id
        : panel.image_asset_id,
      crop_zoom: patch.crop_zoom ?? panel.crop_zoom,
      crop_offset_x: patch.crop_offset_x ?? panel.crop_offset_x,
      crop_offset_y: patch.crop_offset_y ?? panel.crop_offset_y,
    };

    await api.patch(`/api/panels/${panelId}`, body);
    await load();
  }

  async function onSelectAsset(assetId: string) {
    if (!activePanel) return;
    try {
      await updatePanel(activePanel.id, { image_asset_id: assetId });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onAddText(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activePanel || !page || page.status === "validated") return;

    const form = new FormData(e.currentTarget);
    const bubbleTail = String(form.get("bubble_tail") || "none") as BubbleTail;
    const bubbleKind = String(form.get("bubble_kind") || "normal");
    try {
      await api.post(`/api/panels/${activePanel.id}/text-blocks`, {
        content: String(form.get("content") || ""),
        x: Number(form.get("x") || 0.1),
        y: Number(form.get("y") || 0.1),
        width: Number(form.get("width") || 0.5),
        height: Number(form.get("height") || 0.2),
        font_size: Number(form.get("font_size") || 16),
        bubble_style: makeBubbleStyle(bubbleKind === "thought", bubbleTail),
        text_color: String(form.get("text_color") || "#000000"),
        background_color: String(form.get("background_color") || "#ffffff"),
        background_opacity: Number(form.get("background_opacity") || 1),
      });
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onUpdateText(textBlockId: string) {
    if (!activePanel || !page || page.status === "validated") return;
    const current = (textBlocksByPanelId[activePanel.id] || []).find((tb) => tb.id === textBlockId);
    if (!current) return;

    const body = {
      content: current.content,
      x: current.x,
      y: current.y,
      width: current.width,
      height: current.height,
      font_size: current.font_size,
      bubble_style: current.bubble_style,
      text_color: current.text_color,
      background_color: current.background_color,
      background_opacity: current.background_opacity,
    };

    try {
      await api.patch(`/api/panels/${activePanel.id}/text-blocks/${textBlockId}`, body);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onDeleteText(textBlockId: string) {
    if (!activePanel || !page || page.status === "validated") return;
    try {
      await api.del(`/api/panels/${activePanel.id}/text-blocks/${textBlockId}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onValidate() {
    if (!page) return;
    await api.post(`/api/pages/${page.id}/validate`);
    await load();
  }

  async function onUnvalidate() {
    if (!page) return;
    await api.post(`/api/pages/${page.id}/unvalidate`);
    await load();
  }

  async function onCrop(action: "zoom_in" | "zoom_out" | "left" | "right" | "up" | "down" | "reset") {
    if (!activePanel || !page || page.status === "validated") return;

    if (action === "reset") {
      await updatePanel(activePanel.id, {
        crop_zoom: 1,
        crop_offset_x: 0,
        crop_offset_y: 0,
      });
      return;
    }

    if (action === "zoom_in") {
      await updatePanel(activePanel.id, { crop_zoom: clamp(activePanel.crop_zoom + 0.1, 0.2, 5) });
      return;
    }

    if (action === "zoom_out") {
      await updatePanel(activePanel.id, { crop_zoom: clamp(activePanel.crop_zoom - 0.1, 0.2, 5) });
      return;
    }

    if (action === "left") {
      await updatePanel(activePanel.id, shiftPanelCrop(activePanel, "x", -0.05));
      return;
    }

    if (action === "right") {
      await updatePanel(activePanel.id, shiftPanelCrop(activePanel, "x", 0.05));
      return;
    }

    if (action === "up") {
      await updatePanel(activePanel.id, shiftPanelCrop(activePanel, "y", -0.05));
      return;
    }

    await updatePanel(activePanel.id, shiftPanelCrop(activePanel, "y", 0.05));
  }

  function onTextFieldChange(textBlockId: string, field: keyof TextBlock, value: string | number) {
    if (!activePanel) return;
    setTextBlocksByPanelId((prev) => ({
      ...prev,
      [activePanel.id]: (prev[activePanel.id] || []).map((tb) =>
        tb.id === textBlockId ? { ...tb, [field]: value } : tb
      ),
    }));
  }

  function onBubbleThoughtChange(textBlockId: string, thought: boolean) {
    if (!activePanel) return;
    const current = (textBlocksByPanelId[activePanel.id] || []).find((tb) => tb.id === textBlockId);
    if (!current) return;
    const parsed = parseBubbleStyle(current.bubble_style);
    onTextFieldChange(textBlockId, "bubble_style", makeBubbleStyle(thought, parsed.tail));
  }

  function onBubbleTailChange(textBlockId: string, tail: BubbleTail) {
    if (!activePanel) return;
    const current = (textBlocksByPanelId[activePanel.id] || []).find((tb) => tb.id === textBlockId);
    if (!current) return;
    const parsed = parseBubbleStyle(current.bubble_style);
    onTextFieldChange(textBlockId, "bubble_style", makeBubbleStyle(parsed.thought, tail));
  }

  function onDragStart(textBlock: TextBlock, event: MouseEvent<HTMLDivElement>) {
    if (!activePanel || !page || page.status === "validated") return;
    setDragState({
      textBlockId: textBlock.id,
      panelId: activePanel.id,
      startMouseX: event.clientX,
      startMouseY: event.clientY,
      startX: textBlock.x,
      startY: textBlock.y,
      width: textBlock.width,
      height: textBlock.height,
    });
  }

  const activeTextBlocks = activePanel ? textBlocksByPanelId[activePanel.id] || [] : [];

  return (
    <section className="card">
      <h2>
        {t("pages")} #{page?.page_number}
      </h2>
      <div className="row">
        <button onClick={onValidate} disabled={!page || page.status === "validated"}>
          {t("validate")}
        </button>
        <button onClick={onUnvalidate} disabled={!page || page.status === "draft"}>
          {t("unvalidate")}
        </button>
        {page ? <Link to={`/comics/${page.comic_id}/assets`}>{t("assets_bank")}</Link> : null}
        <span>{page?.status === "validated" ? t("validated") : t("draft")}</span>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <div className="editor-layout">
        <div
          ref={gridRef}
          className="page-grid"
          style={{
            gridTemplateColumns: `repeat(${template?.columns || 1}, 1fr)`,
            gridTemplateRows: `repeat(${template?.rows || 1}, minmax(180px, 220px))`,
          }}
        >
          {panels.map((panel) => {
            const slot = template?.slots.find((s) => s.id === panel.slot_id);
            const image = assets.find((asset) => asset.id === panel.image_asset_id);
            return (
              <PanelCanvas
                key={panel.id}
                panel={panel}
                slot={slot}
                asset={image}
                textBlocks={textBlocksByPanelId[panel.id] || []}
                mode="preview"
                active={panel.id === activePanelId}
                onSelect={() => setActivePanelId(panel.id)}
              />
            );
          })}
        </div>

        <aside className="editor-sidebar">
          {page?.status === "validated" ? (
            <p>{t("validated_lock")}</p>
          ) : activePanel ? (
            <>
              <h3>{t("edit_panel")}</h3>
              <div className="editor-preview">
                <PanelCanvas
                  panel={activePanel}
                  aspectRatio={activePanelAspectRatio}
                  style={
                    activePanelSize
                      ? {
                          width: `${activePanelSize.width}px`,
                          height: `${activePanelSize.height}px`,
                        }
                      : undefined
                  }
                  asset={assets.find((asset) => asset.id === activePanel.image_asset_id)}
                  textBlocks={activeTextBlocks}
                  mode="edit"
                  onTextDragStart={onDragStart}
                />
              </div>
              <div className="editor-controls-scroll">
                <p>{t("assets")}</p>
                <form
                  className="row"
                  onSubmit={(e) => {
                    e.preventDefault();
                    loadAssets(assetSearch).catch((err) => setError(err instanceof Error ? err.message : String(err)));
                  }}
                >
                  <input
                    value={assetSearch}
                    onChange={(e) => setAssetSearch(e.target.value)}
                    placeholder={t("search_assets")}
                  />
                  <button>{t("search")}</button>
                </form>
                <div className={`asset-list ${assetsExpanded ? "expanded" : "collapsed"}`}>
                  {filteredAssets.map((asset) => (
                    <div key={asset.id} className="asset-list-row">
                      <button onClick={() => onSelectAsset(asset.id)}>
                        {asset.name}
                      </button>
                    </div>
                  ))}
                </div>
                <div className="row">
                  <button type="button" onClick={() => setAssetsExpanded((prev) => !prev)}>
                    {assetsExpanded ? t("shrink") : t("expand")}
                  </button>
                </div>
                <div className="row">
                  <button onClick={() => activePanel && updatePanel(activePanel.id, { image_asset_id: null })}>
                    {t("remove_image")}
                  </button>
                </div>

                <p>{t("crop_controls")}</p>
                <div className="row wrap">
                  <button onClick={() => onCrop("zoom_in")}>Zoom +</button>
                  <button onClick={() => onCrop("zoom_out")}>Zoom -</button>
                  <button onClick={() => onCrop("left")}>◀</button>
                  <button onClick={() => onCrop("right")}>▶</button>
                  <button onClick={() => onCrop("up")}>▲</button>
                  <button onClick={() => onCrop("down")}>▼</button>
                  <button onClick={() => onCrop("reset")}>{t("reset")}</button>
                </div>

                <p>{t("text_blocks")}</p>
                <div className="text-block-list">
                  {activeTextBlocks.map((tb) => (
                    <div className="text-block-editor" key={tb.id}>
                      <textarea
                        value={tb.content}
                        onChange={(e) => onTextFieldChange(tb.id, "content", e.target.value)}
                      />
                      <div className="row wrap">
                        <input type="number" step="0.01" value={tb.x} onChange={(e) => onTextFieldChange(tb.id, "x", Number(e.target.value))} />
                        <input type="number" step="0.01" value={tb.y} onChange={(e) => onTextFieldChange(tb.id, "y", Number(e.target.value))} />
                        <input type="number" step="0.01" min={0.01} max={1} value={tb.width} onChange={(e) => onTextFieldChange(tb.id, "width", Number(e.target.value))} />
                        <input type="number" step="0.01" min={0.01} max={1} value={tb.height} onChange={(e) => onTextFieldChange(tb.id, "height", Number(e.target.value))} />
                        <input type="number" min={8} max={72} value={tb.font_size} onChange={(e) => onTextFieldChange(tb.id, "font_size", Number(e.target.value))} />
                        <select
                          value={parseBubbleStyle(tb.bubble_style).tail}
                          onChange={(e) => onBubbleTailChange(tb.id, e.target.value as BubbleTail)}
                        >
                          <option value="none">Sans flèche</option>
                          <option value="tail_top_left">Flèche coin haut gauche</option>
                          <option value="tail_top_right">Flèche coin haut droit</option>
                          <option value="tail_bottom_left">Flèche coin bas gauche</option>
                          <option value="tail_bottom_right">Flèche coin bas droit</option>
                        </select>
                        <select
                          value={parseBubbleStyle(tb.bubble_style).thought ? "thought" : "normal"}
                          onChange={(e) => onBubbleThoughtChange(tb.id, e.target.value === "thought")}
                        >
                          <option value="normal">Bulle normale</option>
                          <option value="thought">Pensée (pointillé)</option>
                        </select>
                        <input value={tb.text_color} onChange={(e) => onTextFieldChange(tb.id, "text_color", e.target.value)} />
                        <input value={tb.background_color} onChange={(e) => onTextFieldChange(tb.id, "background_color", e.target.value)} />
                        <input type="number" step="0.1" min={0} max={1} value={tb.background_opacity} onChange={(e) => onTextFieldChange(tb.id, "background_opacity", Number(e.target.value))} />
                      </div>
                      <div className="row wrap">
                        <button onClick={() => onUpdateText(tb.id)}>{t("save")}</button>
                        <button onClick={() => onDeleteText(tb.id)}>{t("delete")}</button>
                      </div>
                    </div>
                  ))}
                </div>

                <form className="row wrap" onSubmit={onAddText}>
                  <input name="content" placeholder="content" required />
                  <input name="x" type="number" step="0.01" defaultValue={0.1} min={0} max={1} />
                  <input name="y" type="number" step="0.01" defaultValue={0.1} min={0} max={1} />
                  <input name="width" type="number" step="0.01" defaultValue={0.5} min={0.01} max={1} />
                  <input name="height" type="number" step="0.01" defaultValue={0.2} min={0.01} max={1} />
                  <input name="font_size" type="number" defaultValue={16} min={8} max={72} />
                  <select name="bubble_tail" defaultValue="none">
                    <option value="none">Sans flèche</option>
                    <option value="tail_top_left">Flèche coin haut gauche</option>
                    <option value="tail_top_right">Flèche coin haut droit</option>
                    <option value="tail_bottom_left">Flèche coin bas gauche</option>
                    <option value="tail_bottom_right">Flèche coin bas droit</option>
                  </select>
                  <select name="bubble_kind" defaultValue="normal">
                    <option value="normal">Bulle normale</option>
                    <option value="thought">Pensée (pointillé)</option>
                  </select>
                  <input name="text_color" defaultValue="#000000" />
                  <input name="background_color" defaultValue="#ffffff" />
                  <input name="background_opacity" type="number" step="0.1" min={0} max={1} defaultValue={1} />
                  <button>{t("add_text")}</button>
                </form>
              </div>
            </>
          ) : (
            <p>{t("select_panel")}</p>
          )}
        </aside>
      </div>
    </section>
  );
}
