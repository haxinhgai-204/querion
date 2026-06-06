"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useRouter } from "next/navigation";
import {
  restoreStudentToken, studentMe, studentLogout, studentRefresh,
  listPublishedApps, WorkspaceAppsGroup, PublishedApp, StudentInfo,
} from "@/lib/api/student";
import { useStudentSettings, getThemeVars } from "@/components/providers/StudentSettingsProvider";

interface Conversation { id: string; app_id: string; title: string; message_count: number; }
interface Source { content: string; filename?: string; score?: number; chunk_index?: number; }
interface ChatMessage { role: string; content: string; sources?: Source[]; }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const getToken = () => localStorage.getItem("querion-student-token");

// ---- Source Citations Component ----
function SourceCitations({ sources, vars }: { sources: Source[]; vars: Record<string, string> }) {
  const [open, setOpen] = useState(false);

  // Only show sources with score >= 0.5, deduplicated by filename
  const relevant = sources
    .filter((s) => s.score === undefined || s.score >= 0.5)
    .reduce<Source[]>((acc, src) => {
      const name = src.filename || "Tài liệu";
      if (!acc.find((a) => (a.filename || "Tài liệu") === name)) acc.push(src);
      return acc;
    }, []);

  if (!relevant.length) return null;

  return (
    <div className="mt-1 max-w-[70%]" style={{ fontSize: 11 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 transition-all"
        style={{ background: vars["--s-accent-light"], color: vars["--s-accent-text"] }}
      >
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <path d="M4 6h8M4 10h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        <span className="font-medium">{relevant.length} nguồn tài liệu</span>
        <svg
          width="10" height="10" viewBox="0 0 10 10" fill="none"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
        >
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="mt-1.5 space-y-1" style={{ maxWidth: 420 }}>
          {relevant.map((src, idx) => (
            <div key={idx} className="flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5"
              style={{ background: vars["--s-bg-tertiary"] || vars["--s-bg-secondary"], border: `1px solid ${vars["--s-border"]}` }}>
              <span className="font-medium truncate" style={{ color: vars["--s-accent-text"] }}>
                [{idx + 1}] {src.filename || "Tài liệu"}
              </span>
              {src.score !== undefined && (
                <span className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-mono"
                  style={{ background: vars["--s-accent-light"], color: vars["--s-text-muted"] }}>
                  {(src.score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function StudentChatPage() {
  const router = useRouter();
  const { theme, toggleTheme, locale, setLocale, t } = useStudentSettings();
  const vars = getThemeVars(theme);

  const [student, setStudent] = useState<StudentInfo | null>(null);
  const [groups, setGroups] = useState<WorkspaceAppsGroup[]>([]);
  const [selectedApp, setSelectedApp] = useState<PublishedApp | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      if (!restoreStudentToken()) { router.replace("/student/login"); return; }
      try {
        const me = await studentMe();
        if (me.must_change_password) { router.replace("/student/change-password"); return; }
        setStudent(me);
        setGroups(await listPublishedApps());
      } catch {
        const ok = await studentRefresh();
        if (!ok) { router.replace("/student/login"); return; }
        try {
          const me = await studentMe();
          setStudent(me);
          setGroups(await listPublishedApps());
        } catch { router.replace("/student/login"); }
      }
      setLoading(false);
    })();
  }, []); // eslint-disable-line

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const loadConversations = useCallback(async (appId: string) => {
    try {
      const res = await fetch(`${API_BASE}/v1/student/apps/${appId}/conversations`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) setConversations(await res.json());
    } catch { /* silent */ }
  }, []);

  const loadMessages = useCallback(async (convId: string) => {
    try {
      const res = await fetch(`${API_BASE}/v1/student/conversations/${convId}/messages`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const msgs = await res.json();
        setMessages(msgs.map((m: any) => ({
          role: m.role,
          content: m.content,
          sources: m.sources || undefined,
        })));
      }
    } catch { /* silent */ }
  }, []);

  const selectApp = async (app: PublishedApp) => {
    setSelectedApp(app);
    setActiveConvId(null);
    setMessages([]);
    await loadConversations(app.id);
  };

  const selectConversation = async (conv: Conversation) => {
    setActiveConvId(conv.id);
    await loadMessages(conv.id);
  };

  const startNewChat = () => { setActiveConvId(null); setMessages([]); };

  const deleteConversation = async (convId: string) => {
    try {
      await fetch(`${API_BASE}/v1/student/conversations/${convId}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${getToken()}` },
      });
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) { setActiveConvId(null); setMessages([]); }
    } catch { /* silent */ }
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedApp || sending) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setSending(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API_BASE}/v1/student/apps/${selectedApp.id}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ message: userMsg, conversation_id: activeConvId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Something went wrong" }));
        setMessages((prev) => {
          const u = [...prev]; u[u.length - 1] = { role: "assistant", content: `⚠️ ${err.detail}` }; return u;
        });
        setSending(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let pendingSources: Source[] = [];

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (!line.startsWith("data: ") || line.trim() === "data: [DONE]") continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "token") {
              accumulated += data.content;
              const tt = accumulated;
              setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: tt, sources: pendingSources.length ? pendingSources : undefined }; return u; });
            } else if (data.type === "sources") {
              pendingSources = data.sources || [];
            } else if (data.type === "conversation_id" && !activeConvId) {
              setActiveConvId(data.conversation_id);
            } else if (data.type === "title") {
              setConversations((prev) => prev.map((c) =>
                c.id === (activeConvId || data.conversation_id) ? { ...c, title: data.title } : c
              ));
            } else if (data.type === "error") {
              setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: `⚠️ ${data.content}` }; return u; });
            }
          } catch { /* skip */ }
        }
      }

      if (!accumulated) {
        setMessages((prev) => {
          const u = [...prev];
          if (!u[u.length - 1].content) u[u.length - 1] = { role: "assistant", content: t("noResponse") };
          return u;
        });
      }
      if (selectedApp) loadConversations(selectedApp.id);
    } catch {
      setMessages((prev) => { const u = [...prev]; u[u.length - 1] = { role: "assistant", content: t("connectionError") }; return u; });
    }
    setSending(false);
  };

  const handleLogout = () => { studentLogout(); router.replace("/student/login"); };

  if (loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: vars["--s-bg"] }}>
      <div className="animate-spin rounded-full h-6 w-6 border-2" style={{ borderColor: vars["--s-accent"], borderTopColor: "transparent" }} />
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", display: "flex", background: vars["--s-bg"], color: vars["--s-text"], transition: "background 0.3s, color 0.3s" }}>
      {/* Sidebar */}
      <div style={{ width: 280, borderRight: `1px solid ${vars["--s-border"]}`, display: "flex", flexDirection: "column", background: vars["--s-bg-secondary"], transition: "background 0.3s" }}>
        <div className="p-4" style={{ borderBottom: `1px solid ${vars["--s-border"]}` }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">{student?.name}</p>
              <p className="text-[10px]" style={{ color: vars["--s-text-muted"] }}>{student?.email}</p>
            </div>
            <button onClick={handleLogout} className="rounded-lg p-1.5" style={{ color: vars["--s-text-muted"] }} title={t("logout")}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 14H3.333C2.597 14 2 13.403 2 12.667V3.333C2 2.597 2.597 2 3.333 2H6M10.667 11.333L14 8L10.667 4.667M14 8H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          </div>
        </div>

        {/* Settings row: language + theme */}
        <div className="flex items-center justify-between px-4 py-2" style={{ borderBottom: `1px solid ${vars["--s-border"]}` }}>
          <button onClick={() => setLocale(locale === "vi" ? "en" : "vi")}
            className="text-[10px] font-bold uppercase rounded px-2 py-1 transition-all"
            style={{ background: vars["--s-accent-light"], color: vars["--s-accent-text"] }}>
            {locale === "vi" ? "🇻🇳 VI" : "🇬🇧 EN"}
          </button>
          <button onClick={toggleTheme} className="rounded-lg p-1.5 transition-all"
            style={{ color: vars["--s-text-secondary"] }}
            title={theme === "dark" ? t("lightMode") : t("darkMode")}>
            {theme === "dark" ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.2"/><path d="M8 2V3M8 13V14M2 8H3M13 8H14M3.75 3.75L4.5 4.5M11.5 11.5L12.25 12.25M12.25 3.75L11.5 4.5M4.5 11.5L3.75 12.25" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M14 9.32A6 6 0 016.68 2a6 6 0 107.32 7.32z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            )}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {groups.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: vars["--s-text-muted"] }}>{t("noApps")}</p>
          ) : groups.map((group) => (
            <div key={group.workspace_name}>
              <p className="text-[10px] font-bold uppercase tracking-wider px-2 mb-1.5" style={{ color: vars["--s-text-muted"] }}>
                {group.workspace_name}
              </p>
              <div className="space-y-1">
                {group.apps.map((app) => (
                  <button key={app.id} onClick={() => selectApp(app)}
                    className="w-full text-left rounded-lg px-3 py-2 text-sm transition-all"
                    style={{
                      background: selectedApp?.id === app.id ? vars["--s-accent-light"] : "transparent",
                      color: selectedApp?.id === app.id ? vars["--s-accent-text"] : vars["--s-text-secondary"],
                    }}>
                    <span className="font-medium">{app.name}</span>
                    {app.description && (
                      <p className="text-[10px] mt-0.5 truncate" style={{ color: vars["--s-text-muted"] }}>{app.description}</p>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {!selectedApp ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="rounded-full p-4 mx-auto w-fit mb-3" style={{ background: vars["--s-accent-light"] }}>
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" style={{ color: vars["--s-accent"] }}>
                  <path d="M8 10H24M8 16H20M8 22H16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold">{t("selectApp")}</h2>
              <p className="text-sm mt-1" style={{ color: vars["--s-text-muted"] }}>{t("selectAppSubtitle")}</p>
            </div>
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${vars["--s-border"]}`, background: vars["--s-bg-secondary"], transition: "background 0.3s" }}>
              <div className="flex items-center gap-3">
                <div className="rounded-lg p-1.5" style={{ background: vars["--s-accent-light"] }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color: vars["--s-accent"] }}>
                    <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                    <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                    <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                    <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{selectedApp.name}</h3>
                  {selectedApp.description && (
                    <p className="text-[10px]" style={{ color: vars["--s-text-muted"] }}>{selectedApp.description}</p>
                  )}
                </div>
              </div>
              <button onClick={startNewChat} className="rounded-lg px-3 py-1.5 text-xs font-medium"
                style={{ background: vars["--s-accent-light"], color: vars["--s-accent-text"] }}>
                {t("newChat")}
              </button>
            </div>

            {/* Conversation tabs */}
            {conversations.length > 0 && (
              <div className="flex gap-1 px-5 py-2 overflow-x-auto" style={{ borderBottom: `1px solid ${vars["--s-border"]}` }}>
                {conversations.map((conv) => (
                  <div key={conv.id} className="flex items-center gap-1 shrink-0">
                    <button onClick={() => selectConversation(conv)}
                      className="rounded-lg px-3 py-1 text-xs transition-all truncate"
                      style={{
                        maxWidth: 160,
                        background: activeConvId === conv.id ? vars["--s-accent-light"] : vars["--s-bg-tertiary"],
                        color: activeConvId === conv.id ? vars["--s-accent-text"] : vars["--s-text-muted"],
                        border: `1px solid ${activeConvId === conv.id ? vars["--s-accent"] + "30" : vars["--s-border"]}`,
                      }}>
                      {conv.title}
                    </button>
                    <button onClick={() => deleteConversation(conv.id)} className="text-[10px] px-1" style={{ color: vars["--s-text-muted"] }}>✕</button>
                  </div>
                ))}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center py-16">
                  <p className="text-sm" style={{ color: vars["--s-text-muted"] }}>{t("startConversation")} {selectedApp.name}</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className={`rounded-xl px-4 py-2.5 max-w-[72%] text-sm ${msg.role === "assistant" ? "chat-md-bubble" : ""}`}
                    style={{
                      background: msg.role === "user" ? vars["--s-user-bubble"] : vars["--s-bot-bubble"],
                      color: msg.role === "user" ? vars["--s-user-text"] : vars["--s-bot-text"],
                      transition: "background 0.3s, color 0.3s",
                      whiteSpace: msg.role === "user" ? "pre-wrap" : undefined,
                    }}
                  >
                    {msg.role === "user" ? (
                      msg.content
                    ) : (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => <p style={{ margin: "0.35em 0" }}>{children}</p>,
                          ul: ({ children }) => <ul style={{ paddingLeft: "1.25em", margin: "0.35em 0", listStyleType: "disc" }}>{children}</ul>,
                          ol: ({ children }) => <ol style={{ paddingLeft: "1.25em", margin: "0.35em 0", listStyleType: "decimal" }}>{children}</ol>,
                          li: ({ children }) => <li style={{ margin: "0.15em 0" }}>{children}</li>,
                          strong: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
                          em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                          h1: ({ children }) => <h1 style={{ fontSize: "1.2em", fontWeight: 700, margin: "0.6em 0 0.3em" }}>{children}</h1>,
                          h2: ({ children }) => <h2 style={{ fontSize: "1.1em", fontWeight: 700, margin: "0.5em 0 0.25em" }}>{children}</h2>,
                          h3: ({ children }) => <h3 style={{ fontSize: "1em", fontWeight: 700, margin: "0.4em 0 0.2em" }}>{children}</h3>,
                          code: ({ inline, children }: any) =>
                            inline ? (
                              <code style={{ background: vars["--s-bg-tertiary"] || "rgba(0,0,0,0.12)", borderRadius: 4, padding: "1px 5px", fontFamily: "monospace", fontSize: "0.88em" }}>{children}</code>
                            ) : (
                              <pre style={{ background: vars["--s-bg-tertiary"] || "rgba(0,0,0,0.12)", borderRadius: 8, padding: "10px 12px", overflowX: "auto", margin: "0.4em 0" }}>
                                <code style={{ fontFamily: "monospace", fontSize: "0.85em" }}>{children}</code>
                              </pre>
                            ),
                          blockquote: ({ children }) => (
                            <blockquote style={{ borderLeft: `3px solid ${vars["--s-accent"]}`, paddingLeft: "0.75em", margin: "0.4em 0", opacity: 0.8 }}>{children}</blockquote>
                          ),
                          hr: () => <hr style={{ border: "none", borderTop: `1px solid ${vars["--s-border"]}`, margin: "0.6em 0" }} />,
                          a: ({ href, children }) => (
                            <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: vars["--s-accent"], textDecoration: "underline" }}>{children}</a>
                          ),
                          table: ({ children }) => (
                            <div style={{ overflowX: "auto", margin: "0.5em 0" }}>
                              <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9em" }}>{children}</table>
                            </div>
                          ),
                          th: ({ children }) => <th style={{ border: `1px solid ${vars["--s-border"]}`, padding: "5px 10px", background: vars["--s-bg-tertiary"], fontWeight: 600, textAlign: "left" }}>{children}</th>,
                          td: ({ children }) => <td style={{ border: `1px solid ${vars["--s-border"]}`, padding: "5px 10px" }}>{children}</td>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    )}
                  </div>
                  {/* Source citations — only for assistant messages with sources */}
                  {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                    <SourceCitations sources={msg.sources} vars={vars} />
                  )}
                </div>
              ))}
              {sending && messages[messages.length - 1]?.content === "" && (
                <div className="flex justify-start">
                  <div className="rounded-xl px-4 py-2.5" style={{ background: vars["--s-bot-bubble"] }}>
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: vars["--s-accent"], animationDelay: "0ms" }} />
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: vars["--s-accent"], animationDelay: "150ms" }} />
                      <div className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: vars["--s-accent"], animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="px-5 py-3" style={{ borderTop: `1px solid ${vars["--s-border"]}` }}>
              <div className="flex gap-2">
                <input value={input} onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder={t("typeMessage")} autoFocus
                  className="flex-1 text-sm rounded-xl px-4 py-2.5 outline-none transition-all"
                  style={{ background: vars["--s-input-bg"], color: vars["--s-text"], border: `1px solid ${vars["--s-input-border"]}` }} />
                <button onClick={handleSend} disabled={sending || !input.trim()}
                  className="rounded-xl px-4 py-2.5 text-sm font-medium transition-all"
                  style={{ background: input.trim() ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : vars["--s-bg-tertiary"], color: input.trim() ? "#fff" : vars["--s-text-muted"] }}>
                  {t("send")}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
