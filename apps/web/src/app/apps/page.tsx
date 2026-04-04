"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/components/providers/I18nProvider";
import { AppResponse, createApp, listApps, deleteApp } from "@/lib/api/apps";
import { WorkflowResponse, listWorkflows } from "@/lib/api/workflows";

export default function AppsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [apps, setApps] = useState<AppResponse[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createWorkflowId, setCreateWorkflowId] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [a, w] = await Promise.all([listApps(), listWorkflows()]);
      setApps(a);
      setWorkflows(w);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      const app = await createApp({ name: createName, workflow_id: createWorkflowId || undefined });
      router.push(`/apps/${app.id}`);
    } catch { /* silent */ }
    finally { setCreating(false); }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteApp(deleting);
      setApps((prev) => prev.filter((a) => a.id !== deleting));
    } catch { /* silent */ }
    finally { setDeleting(null); }
  };

  const deletingApp = apps.find((a) => a.id === deleting);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>Apps</h2>
          <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>Bind workflows to apps with API key access</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium"
          style={{ background: "var(--accent)", color: "#fff" }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          New App
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-current" style={{ borderTopColor: "transparent", color: "var(--accent)" }} />
        </div>
      ) : apps.length === 0 ? (
        <div className="text-center py-20">
          <div className="rounded-full p-4 mb-4 mx-auto w-fit" style={{ background: "var(--accent-glow)" }}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" style={{ color: "var(--accent)" }}>
              <rect x="5" y="5" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <rect x="17" y="5" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <rect x="5" y="17" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <rect x="17" y="17" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-1" style={{ color: "var(--foreground)" }}>No apps yet</h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>Create your first app to publish a workflow</p>
        </div>
      ) : (
        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
          {apps.map((app) => {
            const wf = workflows.find((w) => w.id === app.workflow_id);
            return (
              <div key={app.id} onClick={() => router.push(`/apps/${app.id}`)}
                className="rounded-xl p-4 cursor-pointer transition-all group"
                style={{ background: "var(--card)", border: "1px solid var(--border)" }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg p-1.5" style={{ background: "rgba(99,102,241,0.12)" }}>
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ color: "#6366f1" }}>
                        <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                        <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                        <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                        <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{app.name}</h3>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); setDeleting(app.id); }}
                    className="opacity-0 group-hover:opacity-100 rounded-lg p-1 transition-all"
                    style={{ color: "var(--muted)" }}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 4L10 10M4 10L10 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                  </button>
                </div>
                <div className="flex items-center gap-3 text-xs" style={{ color: "var(--muted)" }}>
                  <span>🔗 {wf?.name || "No workflow"}</span>
                  <span>·</span>
                  <span>{new Date(app.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="mt-2 text-[10px] font-mono truncate px-2 py-1 rounded"
                  style={{ background: "var(--background)", color: "var(--muted)" }}>
                  {app.api_key.slice(0, 20)}...
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
          onClick={() => setShowCreate(false)}>
          <div onClick={(e) => e.stopPropagation()} className="rounded-2xl p-6"
            style={{ background: "var(--card)", border: "1px solid var(--border)", width: 440 }}>
            <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Create New App</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>Name</label>
                <input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="My Chat App"
                  className="w-full text-sm rounded-lg px-3 py-2 outline-none" autoFocus
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </div>
              <div>
                <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>Workflow</label>
                <select value={createWorkflowId} onChange={(e) => setCreateWorkflowId(e.target.value)}
                  className="w-full text-sm rounded-lg px-3 py-2 outline-none"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
                  <option value="">None</option>
                  {workflows.map((wf) => <option key={wf.id} value={wf.id}>{wf.name}</option>)}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={handleCreate} disabled={creating || !createName.trim()}
                className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "var(--accent)", color: "#fff" }}>{creating ? "..." : "Create"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {deleting && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
          onClick={() => setDeleting(null)}>
          <div onClick={(e) => e.stopPropagation()} className="rounded-2xl p-6"
            style={{ background: "var(--card)", border: "1px solid var(--border)", width: 400 }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-full p-2" style={{ background: "rgba(239,68,68,0.1)" }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ color: "#ef4444" }}>
                  <path d="M10 6V10M10 14H10.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>Delete App</h3>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>Delete <strong>{deletingApp?.name}</strong>? Cannot be undone.</p>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleting(null)} className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={confirmDelete} className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "#ef4444", color: "#fff" }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
