import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api, uploadComicAsset } from "../services/api";
import { resolveMediaUrl } from "../services/media";
import { Asset, Comic } from "../types";

export function ComicAssetsPage() {
  const { comicId } = useParams<{ comicId: string }>();
  const { t } = useI18n();
  const [comic, setComic] = useState<Comic | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load(currentSearch?: string) {
    if (!comicId) return;
    const query = currentSearch?.trim() ? `?search=${encodeURIComponent(currentSearch.trim())}` : "";
    const [comicData, assetData] = await Promise.all([
      api.get<Comic>(`/api/comics/${comicId}`),
      api.get<Asset[]>(`/api/comics/${comicId}/assets${query}`),
    ]);
    setComic(comicData);
    setAssets(assetData);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [comicId]);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!comicId) return;
    const form = new FormData(e.currentTarget);
    const file = form.get("file");
    const name = String(form.get("name") || "").trim();
    if (!(file instanceof File)) return;

    try {
      await uploadComicAsset(comicId, file, name || file.name);
      e.currentTarget.reset();
      await load(search);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section className="card">
      <h2>{t("assets_bank")}</h2>
      <p>{comic?.name}</p>
      <div className="row wrap">
        {comicId ? <Link to={`/comics/${comicId}`}>{t("back_to_comic")}</Link> : null}
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <form className="row wrap" onSubmit={onUpload}>
        <input name="file" type="file" required />
        <input name="name" placeholder={t("name")} />
        <button>{t("upload")}</button>
      </form>

      <form
        className="row wrap"
        onSubmit={(e) => {
          e.preventDefault();
          load(search).catch((err) => setError(err instanceof Error ? err.message : String(err)));
        }}
      >
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("search_assets")} />
        <button>{t("search")}</button>
      </form>

      <div className="asset-gallery">
        {assets.map((asset) => (
          <article key={asset.id} className="asset-card">
            <img src={resolveMediaUrl(asset.file_path)} alt={asset.name} loading="lazy" />
            <p>{asset.name}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
