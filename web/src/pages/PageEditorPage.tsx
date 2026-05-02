import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api, uploadAsset } from "../services/api";
import { Asset, Page, Panel, Template, TextBlock } from "../types";

export function PageEditorPage() {
  const { pageId } = useParams<{ pageId: string }>();
  const { t } = useI18n();
  const [page, setPage] = useState<Page | null>(null);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [template, setTemplate] = useState<Template | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [activePanel, setActivePanel] = useState<Panel | null>(null);
  const [texts, setTexts] = useState<TextBlock[]>([]);

  async function load() {
    const p = await api.get<Page>(`/api/pages/${pageId}`);
    const [panelData, templates, assetData] = await Promise.all([
      api.get<Panel[]>(`/api/pages/${pageId}/panels`),
      api.get<Template[]>("/api/templates"),
      api.get<Asset[]>("/api/assets"),
    ]);
    setPage(p);
    setPanels(panelData);
    setTemplate(templates.find((tpl) => tpl.id === p.template_id) || null);
    setAssets(assetData);
  }

  useEffect(() => {
    load();
  }, [pageId]);

  async function openPanel(panel: Panel) {
    setActivePanel(panel);
    setTexts(await api.get<TextBlock[]>(`/api/panels/${panel.id}/text-blocks`));
  }

  async function onSelectAsset(assetId: string) {
    if (!activePanel) return;
    await api.patch(`/api/panels/${activePanel.id}`, {
      image_asset_id: assetId,
      crop_zoom: activePanel.crop_zoom,
      crop_offset_x: activePanel.crop_offset_x,
      crop_offset_y: activePanel.crop_offset_y,
    });
    await load();
    await openPanel({ ...activePanel, image_asset_id: assetId });
  }

  async function onUpload(file: File) {
    await uploadAsset(file, file.name);
    await load();
  }

  async function onAddText(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activePanel) return;
    const form = new FormData(e.currentTarget);
    await api.post(`/api/panels/${activePanel.id}/text-blocks`, {
      content: String(form.get("content") || ""),
      x: Number(form.get("x") || 0.1),
      y: Number(form.get("y") || 0.1),
      width: Number(form.get("width") || 0.5),
      height: Number(form.get("height") || 0.2),
      font_size: Number(form.get("font_size") || 16),
      bubble_style: String(form.get("bubble_style") || "speech"),
    });
    e.currentTarget.reset();
    setTexts(await api.get<TextBlock[]>(`/api/panels/${activePanel.id}/text-blocks`));
    await load();
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

  return (
    <section className="card">
      <h2>{t("pages")} #{page?.page_number}</h2>
      <div className="row">
        <button onClick={onValidate}>{t("validate")}</button>
        <button onClick={onUnvalidate}>{t("unvalidate")}</button>
      </div>
      <div
        className="page-grid"
        style={{
          gridTemplateColumns: `repeat(${template?.columns || 1}, 1fr)`,
          gridTemplateRows: `repeat(${template?.rows || 1}, 220px)`,
        }}
      >
        {panels.map((panel) => {
          const slot = template?.slots.find((s) => s.id === panel.slot_id);
          const image = assets.find((asset) => asset.id === panel.image_asset_id);
          return (
            <button
              key={panel.id}
              className="panel"
              style={{
                gridColumn: `${slot?.col_start || 1} / span ${slot?.col_span || 1}`,
                gridRow: `${slot?.row_start || 1} / span ${slot?.row_span || 1}`,
                backgroundImage: image ? `url(${image.file_path})` : undefined,
              }}
              onClick={() => openPanel(panel)}
            >
              {panel.reading_order}
            </button>
          );
        })}
      </div>

      {activePanel ? (
        <div className="modal-backdrop" onClick={() => setActivePanel(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{t("edit_panel")}</h3>
            <p>{t("assets")}</p>
            <input
              type="file"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f);
              }}
            />
            <div className="asset-grid">
              {assets.map((asset) => (
                <button key={asset.id} onClick={() => onSelectAsset(asset.id)}>{asset.name}</button>
              ))}
            </div>
            <p>{t("text_blocks")}</p>
            <ul className="list">
              {texts.map((tb) => (
                <li key={tb.id}>{tb.content}</li>
              ))}
            </ul>
            <form className="row wrap" onSubmit={onAddText}>
              <input name="content" placeholder="content" required />
              <input name="x" type="number" step="0.01" defaultValue={0.1} min={0} max={1} />
              <input name="y" type="number" step="0.01" defaultValue={0.1} min={0} max={1} />
              <input name="width" type="number" step="0.01" defaultValue={0.5} min={0.01} max={1} />
              <input name="height" type="number" step="0.01" defaultValue={0.2} min={0.01} max={1} />
              <input name="font_size" type="number" defaultValue={16} min={8} max={72} />
              <input name="bubble_style" defaultValue="speech" />
              <button>{t("add_text")}</button>
            </form>
            <button onClick={() => setActivePanel(null)}>{t("close")}</button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
