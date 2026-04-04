"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { studentLogin } from "@/lib/api/student";
import { useStudentSettings, getThemeVars } from "@/components/providers/StudentSettingsProvider";

export default function StudentLoginPage() {
  const router = useRouter();
  const { theme, toggleTheme, locale, setLocale, t } = useStudentSettings();
  const vars = getThemeVars(theme);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await studentLogin(email, password);
      if (data.student.must_change_password) {
        router.replace("/student/change-password");
      } else {
        router.replace("/student/chat");
      }
    } catch (err: any) {
      setError(err.message || t("loginError"));
    } finally {
      setLoading(false);
    }
  };

  const bgGradient = theme === "dark"
    ? "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)"
    : "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #f8fafc 100%)";

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: bgGradient, transition: "background 0.3s" }}>
      <div className="rounded-2xl p-8 relative" style={{
        background: theme === "dark" ? "rgba(30,30,50,0.85)" : "rgba(255,255,255,0.9)",
        border: `1px solid ${vars["--s-border"]}`,
        width: 400, backdropFilter: "blur(20px)", transition: "background 0.3s"
      }}>
        {/* Theme + Language toggle */}
        <div className="absolute top-4 right-4 flex items-center gap-2">
          <button onClick={() => setLocale(locale === "vi" ? "en" : "vi")}
            className="text-[10px] font-bold uppercase rounded px-1.5 py-0.5"
            style={{ background: vars["--s-accent-light"], color: vars["--s-accent-text"] }}>
            {locale === "vi" ? "VI" : "EN"}
          </button>
          <button onClick={toggleTheme} className="rounded p-1" style={{ color: vars["--s-text-secondary"] }}>
            {theme === "dark" ? (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.2"/><path d="M8 2V3M8 13V14M2 8H3M13 8H14M3.75 3.75L4.5 4.5M11.5 11.5L12.25 12.25M12.25 3.75L11.5 4.5M4.5 11.5L3.75 12.25" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M14 9.32A6 6 0 016.68 2a6 6 0 107.32 7.32z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            )}
          </button>
        </div>

        <div className="text-center mb-6">
          <div className="rounded-full p-3 mx-auto w-fit mb-3" style={{ background: vars["--s-accent-light"] }}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" style={{ color: vars["--s-accent"] }}>
              <path d="M14 14C17 14 19.5 11.5 19.5 8.5S17 3 14 3 8.5 5.5 8.5 8.5 11 14 14 14Z" stroke="currentColor" strokeWidth="1.5" />
              <path d="M4 24C4 20 8 17 14 17S24 20 24 24" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-xl font-bold" style={{ color: vars["--s-text"] }}>{t("loginTitle")}</h1>
          <p className="text-sm mt-1" style={{ color: vars["--s-text-secondary"] }}>{t("loginSubtitle")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg px-3 py-2 text-xs" style={{ background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)" }}>
              {error}
            </div>
          )}

          <div>
            <label className="text-[11px] font-semibold block mb-1.5" style={{ color: vars["--s-text-secondary"] }}>{t("email")}</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus
              className="w-full text-sm rounded-lg px-3 py-2.5 outline-none transition-all"
              placeholder="student@university.edu"
              style={{ background: vars["--s-input-bg"], color: vars["--s-text"], border: `1px solid ${vars["--s-input-border"]}` }}
              onFocus={(e) => { e.target.style.borderColor = "#6366f1"; }}
              onBlur={(e) => { e.target.style.borderColor = vars["--s-input-border"]; }} />
          </div>

          <div>
            <label className="text-[11px] font-semibold block mb-1.5" style={{ color: vars["--s-text-secondary"] }}>{t("password")}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full text-sm rounded-lg px-3 py-2.5 outline-none transition-all"
              placeholder="••••••••"
              style={{ background: vars["--s-input-bg"], color: vars["--s-text"], border: `1px solid ${vars["--s-input-border"]}` }}
              onFocus={(e) => { e.target.style.borderColor = "#6366f1"; }}
              onBlur={(e) => { e.target.style.borderColor = vars["--s-input-border"]; }} />
          </div>

          <button type="submit" disabled={loading}
            className="w-full rounded-lg py-2.5 text-sm font-semibold transition-all"
            style={{ background: loading ? "#4338ca" : "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff" }}>
            {loading ? "..." : t("loginButton")}
          </button>
        </form>

        <div className="text-center mt-5">
          <a href="/login" className="text-xs" style={{ color: vars["--s-text-muted"] }}>Admin login →</a>
        </div>
      </div>
    </div>
  );
}
