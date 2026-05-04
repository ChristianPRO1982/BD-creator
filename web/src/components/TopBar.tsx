import { useI18n } from "../contexts/LanguageContext";
import { useTheme } from "../contexts/ThemeContext";

export function TopBar() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();

  return (
    <header className="topbar">
      <h1>{t("app_title")}</h1>
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
