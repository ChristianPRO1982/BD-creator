import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { api } from "../services/api";
import { Comic } from "../types";

export function ComicsPage() {
  const { t } = useI18n();
  const [comics, setComics] = useState<Comic[]>([]);
  const [name, setName] = useState("");

  async function load() {
    setComics(await api.get<Comic[]>("/api/comics"));
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await api.post("/api/comics", { name });
    setName("");
    await load();
  }

  return (
    <section className="card">
      <h2>{t("comics")}</h2>
      <form onSubmit={onSubmit} className="row">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("name")} required />
        <button>{t("create")}</button>
      </form>
      <ul className="list">
        {comics.map((comic) => (
          <li key={comic.id}>
            <Link to={`/comics/${comic.id}`} state={{ comicId: comic.id, comicName: comic.name }}>
              {comic.name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
