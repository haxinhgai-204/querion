"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { translations, type Locale, type TranslationKey } from "@/lib/i18n/student";

type Theme = "dark" | "light";

interface StudentSettingsContextType {
  theme: Theme;
  toggleTheme: () => void;
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: TranslationKey) => string;
}

const StudentSettingsContext = createContext<StudentSettingsContextType | null>(null);

const THEME_KEY = "querion-student-theme";
const LOCALE_KEY = "querion-student-locale";

export function StudentSettingsProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");
  const [locale, setLocaleState] = useState<Locale>("vi");

  // Restore from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY) as Theme | null;
    if (saved === "light" || saved === "dark") setTheme(saved);
    const savedLocale = localStorage.getItem(LOCALE_KEY) as Locale | null;
    if (savedLocale === "en" || savedLocale === "vi") setLocaleState(savedLocale);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      return next;
    });
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(LOCALE_KEY, l);
  }, []);

  const t = useCallback(
    (key: TranslationKey) => translations[locale][key] || key,
    [locale],
  );

  return (
    <StudentSettingsContext.Provider value={{ theme, toggleTheme, locale, setLocale, t }}>
      {children}
    </StudentSettingsContext.Provider>
  );
}

export function useStudentSettings() {
  const ctx = useContext(StudentSettingsContext);
  if (!ctx) throw new Error("useStudentSettings must be within StudentSettingsProvider");
  return ctx;
}

// Theme CSS variables
export function getThemeVars(theme: Theme) {
  if (theme === "light") {
    return {
      "--s-bg": "#f8fafc",
      "--s-bg-secondary": "#ffffff",
      "--s-bg-tertiary": "#f1f5f9",
      "--s-bg-hover": "#e2e8f0",
      "--s-border": "rgba(0,0,0,0.08)",
      "--s-text": "#0f172a",
      "--s-text-secondary": "#475569",
      "--s-text-muted": "#94a3b8",
      "--s-accent": "#6366f1",
      "--s-accent-light": "rgba(99,102,241,0.1)",
      "--s-accent-text": "#4f46e5",
      "--s-user-bubble": "rgba(99,102,241,0.12)",
      "--s-user-text": "#4338ca",
      "--s-bot-bubble": "#ffffff",
      "--s-bot-text": "#1e293b",
      "--s-input-bg": "#ffffff",
      "--s-input-border": "rgba(0,0,0,0.12)",
    };
  }
  return {
    "--s-bg": "#0f172a",
    "--s-bg-secondary": "#1e293b",
    "--s-bg-tertiary": "rgba(255,255,255,0.03)",
    "--s-bg-hover": "rgba(255,255,255,0.06)",
    "--s-border": "rgba(255,255,255,0.06)",
    "--s-text": "#f1f5f9",
    "--s-text-secondary": "#94a3b8",
    "--s-text-muted": "#64748b",
    "--s-accent": "#6366f1",
    "--s-accent-light": "rgba(99,102,241,0.15)",
    "--s-accent-text": "#a5b4fc",
    "--s-user-bubble": "rgba(99,102,241,0.2)",
    "--s-user-text": "#c7d2fe",
    "--s-bot-bubble": "rgba(255,255,255,0.05)",
    "--s-bot-text": "#e2e8f0",
    "--s-input-bg": "rgba(255,255,255,0.05)",
    "--s-input-border": "rgba(255,255,255,0.1)",
  };
}
