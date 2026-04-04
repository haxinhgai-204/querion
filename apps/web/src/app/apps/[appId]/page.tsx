"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppResponse, getApp, updateApp, regenerateApiKey, listRuns, getRunSteps, RunResponse, RunStepResponse } from "@/lib/api/apps";
import { WorkflowResponse, listWorkflows } from "@/lib/api/workflows";
import { DatasetResponse, listDatasets } from "@/lib/api/datasets";

export default function AppDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params.appId as string;

  const [app, setApp] = useState<AppResponse | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [steps, setSteps] = useState<RunStepResponse[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<"config" | "runs">("config");

  // Form state
  const [name, setName] = useState("");
  const [workflowId, setWorkflowId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [description, setDescription] = useState("");
  const [isPublished, setIsPublished] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [a, w, d] = await Promise.all([getApp(appId), listWorkflows(), listDatasets()]);
        setApp(a);
        setWorkflows(w);
        setDatasets(d);
        setName(a.name);
        setWorkflowId(a.workflow_id || "");
        setDatasetId(a.dataset_id || "");
        setSystemPrompt(a.system_prompt || "");
        setDescription(a.description || "");
        setIsPublished(a.is_published);
      } catch { router.push("/apps"); }
    })();
  }, [appId]); // eslint-disable-line

  const fetchRuns = useCallback(async () => {
    try { setRuns(await listRuns(appId)); } catch { /* silent */ }
  }, [appId]);

  useEffect(() => { if (tab === "runs") fetchRuns(); }, [tab, fetchRuns]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateApp(appId, { name, workflow_id: workflowId || undefined, dataset_id: datasetId || undefined, system_prompt: systemPrompt, description, is_published: isPublished });
      setApp(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* silent */ }
    finally { setSaving(false); }
  };

  const handleRegenKey = async () => {
    if (!confirm("Regenerate API key? The old key will stop working.")) return;
    try {
      const updated = await regenerateApiKey(appId);
      setApp(updated);
    } catch { /* silent */ }
  };

  const copyKey = () => {
    if (app) {
      navigator.clipboard.writeText(app.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const viewSteps = async (runId: string) => {
    setSelectedRun(runId);
    try { setSteps(await getRunSteps(runId)); } catch { setSteps([]); }
  };

  if (!app) return (
    <div className="flex justify-center py-16">
      <div className="animate-spin rounded-full h-6 w-6 border-2 border-current" style={{ borderTopColor: "transparent", color: "var(--accent)" }} />
    </div>
  );

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.push("/apps")} className="rounded-lg p-1.5" style={{ color: "var(--muted)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M12 3L6 9L12 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
        <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>{app.name}</h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded-xl" style={{ background: "var(--card)", border: "1px solid var(--border)", width: "fit-content" }}>
        {(["config", "runs"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className="rounded-lg px-4 py-1.5 text-xs font-semibold capitalize transition-all"
            style={{ background: tab === t ? "var(--accent)" : "transparent", color: tab === t ? "#fff" : "var(--muted)" }}>
            {t === "config" ? "⚙️ Config" : `📊 Runs (${runs.length})`}
          </button>
        ))}
      </div>

      {tab === "config" && (
        <div className="space-y-5">
          {/* Name */}
          <Field label="App Name">
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="w-full text-sm rounded-lg px-3 py-2 outline-none"
              style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
          </Field>

          {/* Workflow */}
          <Field label="Bound Workflow">
            <select value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}
              className="w-full text-sm rounded-lg px-3 py-2 outline-none"
              style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
              <option value="">None</option>
              {workflows.map((wf) => <option key={wf.id} value={wf.id}>{wf.name} ({wf.type})</option>)}
            </select>
          </Field>

          {/* Dataset */}
          <Field label="Bound Dataset (RAG)">
            <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}
              className="w-full text-sm rounded-lg px-3 py-2 outline-none"
              style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
              <option value="">None</option>
              {datasets.map((ds) => <option key={ds.id} value={ds.id}>{ds.name}</option>)}
            </select>
          </Field>

          {/* System Prompt */}
          <Field label="System Prompt">
            <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={4}
              placeholder="You are a helpful assistant..."
              className="w-full text-sm rounded-lg px-3 py-2 outline-none resize-y"
              style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
          </Field>

          {/* Description */}
          <Field label="Description (visible to students)">
            <input value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="A brief description of what this app does"
              className="w-full text-sm rounded-lg px-3 py-2 outline-none"
              style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
          </Field>

          {/* Publish Toggle */}
          <Field label="Publishing">
            <div className="flex items-center gap-3">
              <button onClick={() => setIsPublished(!isPublished)}
                className="rounded-full transition-all" style={{ width: 44, height: 24, background: isPublished ? "#22c55e" : "rgba(255,255,255,0.15)", position: "relative" }}>
                <div className="rounded-full transition-all" style={{ width: 18, height: 18, background: "#fff", position: "absolute", top: 3, left: isPublished ? 23 : 3 }} />
              </button>
              <span className="text-sm" style={{ color: isPublished ? "#22c55e" : "var(--muted)" }}>
                {isPublished ? "Published — visible to students" : "Unpublished — hidden from students"}
              </span>
            </div>
          </Field>

          {/* API Key */}
          <Field label="API Key">
            <div className="flex gap-2">
              <div className="flex-1 text-xs font-mono px-3 py-2 rounded-lg truncate"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
                {app.api_key}
              </div>
              <button onClick={copyKey} className="rounded-lg px-3 py-2 text-xs font-medium flex-shrink-0"
                style={{ background: "var(--accent-glow)", color: "var(--accent)" }}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
              <button onClick={handleRegenKey} className="rounded-lg px-3 py-2 text-xs font-medium flex-shrink-0"
                style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444" }}>
                Regenerate
              </button>
            </div>
          </Field>

          {/* Save */}
          <button onClick={handleSave} disabled={saving}
            className="rounded-lg px-5 py-2.5 text-sm font-medium"
            style={{ background: "var(--accent)", color: "#fff" }}>
            {saving ? "..." : saved ? "✓ Saved" : "Save Changes"}
          </button>
        </div>
      )}

      {tab === "runs" && (
        <div>
          {runs.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-sm" style={{ color: "var(--muted)" }}>No runs yet. Chat with this app to generate run logs.</p>
            </div>
          ) : (
            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ background: "var(--card)" }}>
                    <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Status</th>
                    <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Started</th>
                    <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Latency</th>
                    <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="transition-colors"
                      style={{ borderTop: "1px solid var(--border)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = "var(--card)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                      <td className="px-4 py-2.5">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                          style={{
                            background: run.status === "completed" ? "rgba(34,197,94,0.12)" : run.status === "failed" ? "rgba(239,68,68,0.12)" : "rgba(245,158,11,0.12)",
                            color: run.status === "completed" ? "#22c55e" : run.status === "failed" ? "#ef4444" : "#f59e0b",
                          }}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-2.5" style={{ color: "var(--foreground)" }}>
                        {new Date(run.started_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5" style={{ color: "var(--foreground)" }}>
                        {run.latency_ms != null ? `${run.latency_ms}ms` : "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <button onClick={() => viewSteps(run.id)} className="text-xs font-medium"
                          style={{ color: "var(--accent)" }}>
                          View Steps
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Steps Modal */}
          {selectedRun && (
            <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
              onClick={() => setSelectedRun(null)}>
              <div onClick={(e) => e.stopPropagation()} className="rounded-2xl p-6"
                style={{ background: "var(--card)", border: "1px solid var(--border)", width: 600, maxHeight: "80vh", overflow: "auto" }}>
                <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>
                  🔍 Run Steps ({steps.length})
                </h3>
                {steps.length === 0 ? (
                  <p className="text-sm" style={{ color: "var(--muted)" }}>No steps recorded.</p>
                ) : (
                  <div className="space-y-2">
                    {steps.map((step, i) => (
                      <div key={step.id} className="rounded-lg p-3"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold rounded px-1.5 py-0.5"
                              style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1" }}>
                              {i + 1}
                            </span>
                            <span className="text-xs font-semibold" style={{ color: "var(--foreground)" }}>
                              {step.node_type}
                            </span>
                            <span className="text-[10px]" style={{ color: "var(--muted)" }}>
                              ({step.node_id})
                            </span>
                          </div>
                          <span className="text-xs font-mono" style={{ color: step.duration_ms != null && step.duration_ms > 1000 ? "#f59e0b" : "#22c55e" }}>
                            {step.duration_ms != null ? `${step.duration_ms}ms` : "..."}
                          </span>
                        </div>
                        {step.output_json && (
                          <pre className="text-[10px] mt-1 font-mono overflow-x-auto" style={{ color: "var(--muted)" }}>
                            {JSON.stringify(step.output_json, null, 2).slice(0, 300)}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[11px] font-semibold block mb-1.5" style={{ color: "var(--muted)" }}>{label}</label>
      {children}
    </div>
  );
}
