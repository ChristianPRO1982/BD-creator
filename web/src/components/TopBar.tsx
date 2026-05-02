import { useI18n } from "../contexts/LanguageContext";
import { useTheme } from "../contexts/ThemeContext";

export function TopBar() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();

  return (
    <header className="topbar">
      <h1>{t("app_title")}</h1>
      <div className="controls">
        <div className="switch-group">
          <button className={theme === "white" ? "active" : ""} onClick={() => setTheme("white")}>{t("theme_white")}</button>
          <button className={theme === "black" ? "active" : ""} onClick={() => setTheme("black")}>{t("theme_black")}</button>
          <button className={theme === "system" ? "active" : ""} onClick={() => setTheme("system")}>{t("theme_system")}</button>
        </div>
        <div className="switch-group">
          <button className={lang === "fr" ? "active" : ""} onClick={() => setLang("fr")}>FR</button>
          <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button>
        </div>
        <a className="logout" href="/logout">{t("logout")}</a>
      </div>
    </header>
  );
}
