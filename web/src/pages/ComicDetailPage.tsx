import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api } from "../services/api";
import { resolveMediaUrl } from "../services/media";
import { Comic, Page, Template } from "../types";

type ComicRouteState = {
  comicId?: string;
  comicName?: string;
};

export function ComicDetailPage() {
  const { comicId } = useParams<{ comicId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = (location.state as ComicRouteState | null) ?? null;
  const { t } = useI18n();
  const [pages, setPages] = useState<Page[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [comicName, setComicName] = useState<string>(routeState?.comicName ?? "");
  const [selectedParentGroupId, setSelectedParentGroupId] = useState<number | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [deleteToken, setDeleteToken] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function load() {
    const [pageData, templateData, comicData] = await Promise.all([
      api.get<Page[]>(`/api/comics/${comicId}/pages`),
      api.get<Template[]>("/api/templates"),
      api.get<Comic>(`/api/comics/${comicId}`),
    ]);
    setPages(pageData);
    setTemplates(templateData);
    setComicName(comicData.name);
    const first = templateData[0];
    if (first) {
      setSelectedParentGroupId(first.parent_group_id);
      setSelectedGroupId(first.group_id);
      setTemplateId(first.id);
    }
  }

  useEffect(() => {
    load();
  }, [comicId]);

  async function onCreatePage(e: FormEvent) {
    e.preventDefault();
    if (templateId === null) return;
    await api.post(`/api/comics/${comicId}/pages`, { template_id: templateId, page_number: pageNumber });
    setPageNumber(pageNumber + 1);
    await load();
  }

  const parentGroups = Array.from(
    new Map(
      templates
        .filter((tpl) => tpl.parent_group_id !== null)
        .map((tpl) => [tpl.parent_group_id as number, { id: tpl.parent_group_id as number, name: tpl.parent_group_name || "" }])
    ).values()
  );
  const subgroups = Array.from(
    new Map(
      templates
        .filter((tpl) => tpl.parent_group_id === selectedParentGroupId)
        .map((tpl) => [tpl.group_id, { id: tpl.group_id, name: tpl.group_name }])
    ).values()
  );
  const filteredTemplates = templates.filter(
    (tpl) => tpl.parent_group_id === selectedParentGroupId && tpl.group_id === selectedGroupId
  );

  async function onRender() {
    await api.post(`/api/render/comics/${comicId}/generate-missing`);
    await load();
  }

  async function onDeleteComic() {
    if (!comicId) return;
    setDeleteError(null);
    if (deleteToken !== "delete") {
      setDeleteError("Type exactement: delete");
      return;
    }
    const confirmed = window.confirm(`delete "${comicName || comicId}" ?`);
    if (!confirmed) return;
    await api.del(`/api/comics/${comicId}`);
    navigate("/");
  }

  return (
    <section className="card">
      <h2>{t("pages")}</h2>
      <form onSubmit={onCreatePage} className="row wrap">
        <select
          value={selectedParentGroupId ?? ""}
          onChange={(e) => {
            const nextParent = Number(e.target.value);
            setSelectedParentGroupId(nextParent);
            const nextSubgroup = Array.from(
              new Map(
                templates
                  .filter((tpl) => tpl.parent_group_id === nextParent)
                  .map((tpl) => [tpl.group_id, tpl.group_id])
              ).values()
            )[0] ?? null;
            setSelectedGroupId(nextSubgroup);
            const nextTemplate = templates.find((tpl) => tpl.parent_group_id === nextParent && tpl.group_id === nextSubgroup);
            setTemplateId(nextTemplate?.id ?? null);
          }}
        >
          {parentGroups.map((group) => (
            <option key={group.id} value={group.id}>{group.name}</option>
          ))}
        </select>
        <select
          value={selectedGroupId ?? ""}
          onChange={(e) => {
            const nextGroup = Number(e.target.value);
            setSelectedGroupId(nextGroup);
            const nextTemplate = templates.find((tpl) => tpl.parent_group_id === selectedParentGroupId && tpl.group_id === nextGroup);
            setTemplateId(nextTemplate?.id ?? null);
          }}
        >
          {subgroups.map((group) => (
            <option key={group.id} value={group.id}>{group.name}</option>
          ))}
        </select>
        <select value={templateId ?? ""} onChange={(e) => setTemplateId(Number(e.target.value))}>
          {filteredTemplates.map((template) => (
            <option key={template.id} value={template.id}>{template.name}</option>
          ))}
        </select>
        <input type="number" value={pageNumber} onChange={(e) => setPageNumber(Number(e.target.value))} min={1} />
        <button disabled={templateId === null}>{t("new_page")}</button>
        <button type="button" onClick={onRender}>{t("render_missing")}</button>
        <Link to={`/comics/${comicId}/assets`}>{t("assets_bank")}</Link>
        <Link to="/templates">{t("template_management")}</Link>
      </form>
      <ul className="list">
        {pages.map((page) => (
          <li key={page.id}>
            <Link to={`/pages/${page.id}`} state={{ comicId, comicName }}>
              #{page.page_number} - {page.status}
            </Link>
            {page.rendered_image_url ? <a href={resolveMediaUrl(page.rendered_image_url)} target="_blank">JPEG</a> : null}
          </li>
        ))}
      </ul>
      <hr />
      <div className="row wrap">
        <strong>{t("delete_comic")}</strong>
        <span>{t("delete_comic_hint")}</span>
      </div>
      <div className="row wrap">
        <input value={deleteToken} onChange={(e) => setDeleteToken(e.target.value)} placeholder="delete" />
        <button type="button" onClick={onDeleteComic}>{t("delete_comic")}</button>
      </div>
      {deleteError ? <p className="error-text">{deleteError}</p> : null}
    </section>
  );
}
