"use client";
import { useEffect, useState } from "react";

export type Theme = "system" | "light" | "dark";
const ORDER: Theme[] = ["system", "light", "dark"];
const GLYPH: Record<Theme, string> = { system: "◐", light: "☀", dark: "☾" };

export function applyTheme(t: Theme) {
  const root = document.documentElement;
  if (t === "system") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", t);
  try { localStorage.setItem("theme", t); } catch {}
}

export function readTheme(): Theme {
  try { const t = localStorage.getItem("theme"); return t === "light" || t === "dark" ? t : "system"; } catch { return "system"; }
}

/** Cycles system → light → dark. The initial attribute is set by an inline script in the layout before hydration. */
export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => { const t = setTimeout(() => setTheme(readTheme()), 0); return () => clearTimeout(t); }, []);
  const next = () => { const t = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]; setTheme(t); applyTheme(t); };
  return (
    <button type="button" onClick={next} title={`Theme: ${theme} (click to change)`} aria-label="Toggle color theme" className="pill" style={{ minWidth: 34, justifyContent: "center" }}>
      <span aria-hidden>{GLYPH[theme]}</span>{withLabel && <span className="capitalize">{theme}</span>}
    </button>
  );
}

export function ThemePicker() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => { const t = setTimeout(() => setTheme(readTheme()), 0); return () => clearTimeout(t); }, []);
  return (
    <div className="flex gap-1.5">
      {ORDER.map((t) => <button key={t} type="button" className="pill capitalize" style={theme === t ? { background: "var(--text)", color: "var(--bg)" } : {}} onClick={() => { setTheme(t); applyTheme(t); }}>{GLYPH[t]} {t}</button>)}
    </div>
  );
}
