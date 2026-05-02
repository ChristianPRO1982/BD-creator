import { createContext, useContext, useEffect, useMemo, useState } from "react";

type Theme = "white" | "black" | "system";

const ThemeContext = createContext<{ theme: Theme; setTheme: (theme: Theme) => void } | null>(null);

function initialTheme(): Theme {
  const saved = localStorage.getItem("bd_theme");
  if (saved === "white" || saved === "black" || saved === "system") return saved;
  return "system";
}

function resolvedTheme(theme: Theme): "white" | "black" {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "black" : "white";
  }
  return theme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(initialTheme());
  useEffect(() => {
    localStorage.setItem("bd_theme", theme);
    document.documentElement.setAttribute("data-theme", resolvedTheme(theme));
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => {
      if (theme === "system") {
        document.documentElement.setAttribute("data-theme", resolvedTheme("system"));
      }
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [theme]);

  const value = useMemo(() => ({ theme, setTheme: setThemeState }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("ThemeContext missing");
  return ctx;
}
