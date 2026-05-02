import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api } from "../services/api";
import { Page, Template } from "../types";

export function ComicDetailPage() {
  const { comicId } = useParams<{ comicId: string }>();
  const { t } = useI18n();
  const [pages, setPages] = useState<Page[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateId, setTemplateId] = useState<number>(1);
  const [pageNumber, setPageNumber] = useState<number>(1);

  async function load() {
    const [pageData, templateData] = await Promise.all([
      api.get<Page[]>(`/api/comics/${comicId}/pages`),
      api.get<Template[]>("/api/templates"),
    ]);
    setPages(pageData);
    setTemplates(templateData);
  }

  useEffect(() => {
    load();
  }, [comicId]);

  async function onCreatePage(e: FormEvent) {
    e.preventDefault();
    await api.post(`/api/comics/${comicId}/pages`, { template_id: templateId, page_number: pageNumber });
    setPageNumber(pageNumber + 1);
    await load();
  }

  async function onRender() {
    await api.post(`/api/render/comics/${comicId}/generate-missing`);
    await load();
  }

  return (
    <section className="card">
      <h2>{t("pages")}</h2>
      <form onSubmit={onCreatePage} className="row wrap">
        <select value={templateId} onChange={(e) => setTemplateId(Number(e.target.value))}>
          {templates.map((template) => (
            <option key={template.id} value={template.id}>{template.name}</option>
          ))}
        </select>
        <input type="number" value={pageNumber} onChange={(e) => setPageNumber(Number(e.target.value))} min={1} />
        <button>{t("new_page")}</button>
        <button type="button" onClick={onRender}>{t("render_missing")}</button>
      </form>
      <ul className="list">
        {pages.map((page) => (
          <li key={page.id}>
            <Link to={`/pages/${page.id}`}>#{page.page_number} - {page.status}</Link>
            {page.rendered_image_url ? <a href={page.rendered_image_url} target="_blank">JPEG</a> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
