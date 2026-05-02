import { createContext, useContext, useMemo, useState } from "react";
import { Lang, messages } from "../i18n/messages";

type LanguageCtx = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
};

const LanguageContext = createContext<LanguageCtx | null>(null);

function detectLanguage(): Lang {
  const saved = localStorage.getItem("bd_lang");
  if (saved === "fr" || saved === "en") return saved;
  return navigator.language.startsWith("fr") ? "fr" : "en";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectLanguage());
  const setLang = (next: Lang) => {
    localStorage.setItem("bd_lang", next);
    setLangState(next);
  };
  const value = useMemo(
    () => ({ lang, setLang, t: (key: string) => messages[lang][key] || key }),
    [lang],
  );
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("LanguageContext missing");
  return ctx;
}
