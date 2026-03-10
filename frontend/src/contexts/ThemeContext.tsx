import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type ThemeColor = "blue" | "emerald" | "violet";
export type ThemeMode = "light" | "dark";

interface ThemeContextType {
  color: ThemeColor;
  mode: ThemeMode;
  setColor: (color: ThemeColor) => void;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

const STORAGE_KEY_COLOR = "faceid_theme_color";
const STORAGE_KEY_MODE = "faceid_theme_mode";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [color, setColorState] = useState<ThemeColor>(() => {
    return (localStorage.getItem(STORAGE_KEY_COLOR) as ThemeColor) || "blue";
  });
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(STORAGE_KEY_MODE) as ThemeMode;
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", color);
    localStorage.setItem(STORAGE_KEY_COLOR, color);
  }, [color]);

  useEffect(() => {
    const root = document.documentElement;
    if (mode === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem(STORAGE_KEY_MODE, mode);
  }, [mode]);

  const setColor = useCallback((c: ThemeColor) => setColorState(c), []);
  const setMode = useCallback((m: ThemeMode) => setModeState(m), []);
  const toggleMode = useCallback(() => {
    setModeState((prev) => (prev === "light" ? "dark" : "light"));
  }, []);

  return (
    <ThemeContext.Provider value={{ color, mode, setColor, setMode, toggleMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
