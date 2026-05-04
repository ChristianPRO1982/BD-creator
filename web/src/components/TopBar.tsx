import { Link, useLocation, useMatch } from "react-router-dom";
import { useI18n } from "../contexts/LanguageContext";
import { useTheme } from "../contexts/ThemeContext";

type BreadcrumbState = {
  comicId?: string;
  comicName?: string;
};

export function TopBar() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const location = useLocation();
  const isComicRoute = useMatch("/comics/:comicId");
  const isPageRoute = useMatch("/pages/:pageId");
  const state = (location.state as BreadcrumbState | null) ?? null;
  const comicId = state?.comicId ?? isComicRoute?.params.comicId;
  const comicLabel = state?.comicName ?? t("comics");

  const crumbs: { label: string; to: string | null }[] = [{ label: t("home"), to: "/" }];
  if (isComicRoute || isPageRoute) {
    crumbs.push({ label: comicLabel, to: isPageRoute && comicId ? `/comics/${comicId}` : null });
  }
  if (isPageRoute) {
    crumbs.push({ label: t("pages"), to: null });
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1>{t("app_title")}</h1>
        <nav className="topbar-nav" aria-label="Breadcrumb">
          {crumbs.map((crumb, index) => {
            const isLast = index === crumbs.length - 1;
            return (
              <span key={`${crumb.label}-${index}`} className="crumb-wrap">
                {crumb.to && !isLast && location.pathname !== crumb.to ? (
                  <Link className="crumb-link" to={crumb.to}>{crumb.label}</Link>
                ) : (
                  <span className={isLast ? "crumb-current" : "crumb-link"}>{crumb.label}</span>
                )}
                {!isLast ? <span className="crumb-separator">/</span> : null}
              </span>
            );
          })}
        </nav>
      </div>
      <div className="controls">
        <div className="dropdown-group">
          <label htmlFor="theme-select">{t("theme")}</label>
          <select id="theme-select" value={theme} onChange={(event) => setTheme(event.target.value as "white" | "black" | "system")}>
            <option value="white">{t("theme_white")}</option>
            <option value="black">{t("theme_black")}</option>
            <option value="system">{t("theme_system")}</option>
          </select>
        </div>
        <div className="dropdown-group">
          <label htmlFor="language-select">{t("language")}</label>
          <select id="language-select" value={lang} onChange={(event) => setLang(event.target.value as "fr" | "en")}>
            <option value="fr">FR</option>
            <option value="en">EN</option>
          </select>
        </div>
        <a className="logout" href="/logout">{t("logout")}</a>
      </div>
    </header>
  );
}
