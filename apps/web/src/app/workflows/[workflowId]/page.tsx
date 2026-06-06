"use client";

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  useReactFlow,
  addEdge,
  Connection,
  Node,
  Edge,
  NodeTypes,
  Handle,
  Position,
  ReactFlowProvider,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

/* Override React Flow default node wrapper */
const rfOverrides = `
  .react-flow__node { background: transparent !important; border: none !important; border-radius: 0 !important; box-shadow: none !important; padding: 0 !important; }
  .react-flow__node.selected { box-shadow: none !important; }
`;
import {
  getWorkflow,
  updateWorkflow,
  runWorkflow,
  GraphJSON,
  RunResult,
} from "@/lib/api/workflows";
import { listDatasets } from "@/lib/api/datasets";

/* ═══════════════════════════════════════════
   NODE STYLES
   ═══════════════════════════════════════════ */

const NODE_STYLES: Record<string, { color: string; bg: string; icon: string; label: string }> = {
  input:             { color: "#22c55e", bg: "rgba(34,197,94,0.10)",  icon: "▶",  label: "Start" },
  retrieve:          { color: "#3b82f6", bg: "rgba(59,130,246,0.10)",  icon: "🔍", label: "Knowledge Retrieval" },
  compose_prompt:    { color: "#f59e0b", bg: "rgba(245,158,11,0.10)", icon: "📝", label: "Compose Prompt" },
  llm_generate:      { color: "#a855f7", bg: "rgba(168,85,247,0.10)", icon: "🤖", label: "LLM" },
  parameter_extract: { color: "#14b8a6", bg: "rgba(20,184,166,0.10)", icon: "📋", label: "Parameter Extract" },
  http_request:      { color: "#f97316", bg: "rgba(249,115,22,0.10)", icon: "🌐", label: "HTTP Request" },
  google_sheets:     { color: "#16a34a", bg: "rgba(22,163,74,0.10)",  icon: "📊", label: "Google Sheets" },
  code_execute:      { color: "#6366f1", bg: "rgba(99,102,241,0.10)", icon: "⚡", label: "Code Execute" },
  if_else:           { color: "#6b7280", bg: "rgba(107,114,128,0.10)", icon: "🔀", label: "If / Else" },
  answer:            { color: "#ec4899", bg: "rgba(236,72,153,0.10)", icon: "💬", label: "Answer" },
  output:            { color: "#ef4444", bg: "rgba(239,68,68,0.10)",  icon: "⏹",  label: "End" },
};

/* ═══════════════════════════════════════════
   CUSTOM NODE COMPONENT
   ═══════════════════════════════════════════ */

function WorkflowNode({ data, type, selected }: NodeProps) {
  const style = NODE_STYLES[type || "input"] || NODE_STYLES.input;
  const isIfElse = type === "if_else";
  const label = typeof data?.label === "string" ? data.label : "";

  return (
    <div
      style={{
        background: "var(--card)",
        border: `2px solid ${selected ? style.color : "rgba(255,255,255,0.08)"}`,
        borderRadius: 12,
        padding: "12px 18px",
        minWidth: 180,
        boxShadow: selected
          ? `0 0 0 3px ${style.bg}, 0 4px 16px rgba(0,0,0,0.3)`
          : "0 2px 8px rgba(0,0,0,0.25)",
        transition: "all 0.15s ease",
      }}
    >
      {type !== "input" && (
        <Handle type="target" position={Position.Top} style={{ background: style.color, width: 10, height: 10, border: "2px solid var(--card)" }} />
      )}
      <div className="flex items-center gap-2.5">
        <div
          className="flex items-center justify-center rounded-lg"
          style={{ width: 28, height: 28, background: style.bg, fontSize: 14, flexShrink: 0 }}
        >
          {style.icon}
        </div>
        <div className="min-w-0">
          <div className="text-[11px] font-bold tracking-wide" style={{ color: style.color }}>{style.label}</div>
          {label && label !== style.label && (
            <div className="text-[10px] mt-0.5 truncate" style={{ color: "var(--muted)", maxWidth: 120 }}>
              {label}
            </div>
          )}
        </div>
      </div>
      {type !== "output" && !isIfElse && (
        <Handle type="source" position={Position.Bottom} style={{ background: style.color, width: 10, height: 10, border: "2px solid var(--card)" }} />
      )}
      {isIfElse && (
        <>
          <div className="flex justify-between mt-2 text-[9px] font-bold" style={{ color: "var(--muted)" }}>
            <span style={{ color: "#22c55e" }}>TRUE</span>
            <span style={{ color: "#ef4444" }}>FALSE</span>
          </div>
          <Handle type="source" position={Position.Bottom} id="true" style={{ background: "#22c55e", width: 10, height: 10, border: "2px solid var(--card)", left: "30%" }} />
          <Handle type="source" position={Position.Bottom} id="false" style={{ background: "#ef4444", width: 10, height: 10, border: "2px solid var(--card)", left: "70%" }} />
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN
   ═══════════════════════════════════════════ */

export default function WorkflowCanvasPage() {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner />
    </ReactFlowProvider>
  );
}

function WorkflowCanvasInner() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.workflowId as string;
  const { screenToFlowPosition } = useReactFlow();

  const [workflowName, setWorkflowName] = useState("...");
  const [workflowType, setWorkflowType] = useState("chatflow");
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([] as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([] as Edge[]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [runModal, setRunModal] = useState(false);
  const [runQuery, setRunQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [datasets, setDatasets] = useState<Array<{ id: string; name: string }>>([]);
  const nodeIdCounter = useRef(1);

  const nodeTypes: NodeTypes = useMemo(
    () => Object.fromEntries(Object.keys(NODE_STYLES).map((t) => [t, WorkflowNode])),
    []
  );

  // Load
  useEffect(() => {
    (async () => {
      try {
        const wf = await getWorkflow(workflowId);
        setWorkflowName(wf.name);
        setWorkflowType(wf.type || "chatflow");
        const graph = wf.graph_json;
        if (graph.nodes?.length) {
          setNodes(graph.nodes.map((n) => ({ ...n, type: n.type, data: n.data || {} })) as Node[]);
          setEdges((graph.edges || []).map((e) => ({
            ...e, animated: true,
            style: { stroke: e.sourceHandle === "false" ? "#ef4444" : "var(--accent)", strokeWidth: 2 },
          })) as Edge[]);
          nodeIdCounter.current = Math.max(...graph.nodes.map((n) => parseInt(n.id.replace(/\D/g, "")) || 0)) + 1;
        }
      } catch { router.push("/workflows"); }
    })();
  }, [workflowId]); // eslint-disable-line

  useEffect(() => { listDatasets().then(setDatasets).catch(() => {}); }, []);

  const onConnect = useCallback((c: Connection) => {
    const isIfElseFalse = c.sourceHandle === "false";
    setEdges((eds) => addEdge({
      ...c, animated: true,
      style: { stroke: isIfElseFalse ? "#ef4444" : "var(--accent)", strokeWidth: 2 },
    }, eds));
  }, [setEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedNode(node), []);
  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const addNode = (type: string) => {
    const id = `node_${nodeIdCounter.current++}`;
    const style = NODE_STYLES[type];
    const d: Record<string, any> = { label: style?.label || type };
    if (type === "retrieve") { d.dataset_ids = []; d.top_k = 5; }
    if (type === "compose_prompt") { d.template = "{{system_prompt}}\n\nContext:\n{{context}}\n\nQuestion: {{query}}"; }
    if (type === "llm_generate") { d.model = ""; d.temperature = 0.7; d.max_tokens = 4096; }
    if (type === "parameter_extract") { d.schema = { name: "User's full name", email: "User's email address" }; }
    if (type === "http_request") { d.url = ""; d.method = "POST"; d.headers = { "Content-Type": "application/json" }; d.body_template = '{"name":"{{name}}","email":"{{email}}"}'; }
    if (type === "if_else") { d.variable = "extracted_params.name"; d.operator = "not_empty"; d.value = ""; }
    if (type === "answer") { d.template = ""; }
    if (type === "code_execute") { d.code = "def main(args):\n    # args: query, inputs, answer, extracted_params, retrieved_chunks, http_response\n    data = args['extracted_params']\n    return {'answer': f'Processed: {data}'}\n"; }

    // Place node at the center of the current viewport
    const canvasEl = document.querySelector('.react-flow');
    const w = canvasEl?.clientWidth ?? 800;
    const h = canvasEl?.clientHeight ?? 600;
    const center = screenToFlowPosition({ x: w / 2 + 170, y: h / 2 + 52 }); // offset for palette + toolbar

    setNodes((nds) => [...nds, { id, type, position: { x: center.x - 90, y: center.y - 20 + (nds.length % 3) * 80 }, data: d } as Node]);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const graph: GraphJSON = {
        nodes: nodes.map((n) => ({ id: n.id, type: n.type || "input", position: n.position, data: n.data as Record<string, any> })),
        edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle || undefined })),
      };
      await updateWorkflow(workflowId, { name: workflowName, type: workflowType, graph_json: graph });
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch (err: any) { alert(err?.message || "Save failed"); }
    finally { setSaving(false); }
  };

  const handleRun = async () => {
    setRunning(true); setRunResult(null);
    try { setRunResult(await runWorkflow(workflowId, runQuery)); }
    catch (err: any) { setRunResult({ answer: `Error: ${err?.message || "Failed"}`, extracted_params: {}, retriever_resources: [] }); }
    finally { setRunning(false); }
  };

  const updateNodeData = (key: string, value: any) => {
    if (!selectedNode) return;
    setNodes((nds) => nds.map((n) => {
      if (n.id === selectedNode.id) {
        const updated = { ...n, data: { ...n.data, [key]: value } };
        setSelectedNode(updated);
        return updated;
      }
      return n;
    }));
  };

  return (
    <div style={{ position: "fixed", inset: 0, display: "flex", flexDirection: "column", background: "var(--background)", zIndex: 50 }}>
      <style dangerouslySetInnerHTML={{ __html: rfOverrides }} />
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 gap-3"
        style={{ height: 52, borderBottom: "1px solid var(--border)", background: "var(--card)", flexShrink: 0 }}>
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/workflows")} className="rounded-lg p-1.5" style={{ color: "var(--muted)" }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M12 3L6 9L12 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
          <div className="group/title flex items-center gap-1.5 rounded-lg px-2 py-1 -ml-2 transition-all"
            style={{ border: "1px solid transparent" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--background)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "transparent"; e.currentTarget.style.background = "transparent"; }}>
            <input value={workflowName} onChange={(e) => setWorkflowName(e.target.value)}
              className="text-sm font-semibold bg-transparent border-none outline-none cursor-text"
              style={{ color: "var(--foreground)", width: 200 }} />
            <svg className="opacity-0 group-hover/title:opacity-50 transition-opacity" width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ color: "var(--muted)", flexShrink: 0 }}>
              <path d="M8.5 1.5L10.5 3.5M1 11L1.5 8.5L9 1L11 3L3.5 10.5L1 11Z" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
            style={{ background: workflowType === "chatflow" ? "rgba(236,72,153,0.12)" : "rgba(168,85,247,0.12)",
                     color: workflowType === "chatflow" ? "#ec4899" : "#a855f7" }}>
            {workflowType}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { setRunModal(true); setRunResult(null); }}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
            style={{ background: "rgba(34,197,94,0.12)", color: "#22c55e" }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 2L10 6L3 10V2Z" fill="currentColor" /></svg>
            Test Run
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
            style={{ background: "var(--accent)", color: "#fff" }}>
            {saving ? "..." : saved ? "✓ Saved" : "Save"}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Palette */}
        <div className="flex flex-col gap-1 p-2.5"
          style={{ width: 170, borderRight: "1px solid var(--border)", background: "var(--card)", overflowY: "auto", flexShrink: 0 }}>
          <p className="text-[10px] font-bold uppercase tracking-wider mb-1 px-1" style={{ color: "var(--muted)" }}>Nodes</p>
          {Object.entries(NODE_STYLES).map(([type, s]) => (
            <button key={type} onClick={() => addNode(type)}
              className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-[11px] font-medium text-left transition-all"
              style={{ background: s.bg, color: s.color, border: "1px solid transparent" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = s.color; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "transparent"; }}>
              <span style={{ fontSize: 12 }}>{s.icon}</span>{s.label}
            </button>
          ))}
        </div>

        {/* Canvas */}
        <div style={{ flex: 1 }}>
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            onConnect={onConnect} onNodeClick={onNodeClick} onPaneClick={onPaneClick}
            nodeTypes={nodeTypes} fitView colorMode="dark"
            defaultEdgeOptions={{ animated: true, style: { stroke: "var(--accent)", strokeWidth: 2 } }}>
            <Background variant={BackgroundVariant.Cross} gap={24} size={2} color="rgba(255,255,255,0.06)" />
            <Controls style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }} showInteractive={false} />
          </ReactFlow>
        </div>

        {/* Properties Panel */}
        {selectedNode && (
          <div className="flex flex-col gap-3 p-4"
            style={{ width: 280, borderLeft: "1px solid var(--border)", background: "var(--card)", overflowY: "auto", flexShrink: 0 }}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold flex items-center gap-1.5" style={{ color: NODE_STYLES[selectedNode.type || ""]?.color }}>
                {NODE_STYLES[selectedNode.type || ""]?.icon} {NODE_STYLES[selectedNode.type || ""]?.label}
              </h3>
              <button onClick={() => setSelectedNode(null)} className="text-xs rounded p-1" style={{ color: "var(--muted)" }}>✕</button>
            </div>
            <div style={{ borderBottom: "1px solid var(--border)" }} />

            {/* Common: Label */}
            <Field label="Label">
              <input value={(selectedNode.data?.label as string) || ""} onChange={(e) => updateNodeData("label", e.target.value)}
                className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
            </Field>

            {/* Retrieve */}
            {selectedNode.type === "retrieve" && (
              <>
                <Field label="Datasets">
                  <select multiple value={(selectedNode.data?.dataset_ids as string[]) || []}
                    onChange={(e) => updateNodeData("dataset_ids", Array.from(e.target.selectedOptions, (o) => o.value))}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)", minHeight: 72 }}>
                    {datasets.map((ds) => <option key={ds.id} value={ds.id}>{ds.name}</option>)}
                  </select>
                </Field>
                <Field label="Top K">
                  <input type="number" min={1} max={20} value={(selectedNode.data?.top_k as number) || 5}
                    onChange={(e) => updateNodeData("top_k", parseInt(e.target.value) || 5)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
              </>
            )}

            {/* Compose Prompt */}
            {selectedNode.type === "compose_prompt" && (
              <>
                <Field label="Template">
                  <textarea value={(selectedNode.data?.template as string) || ""} onChange={(e) => updateNodeData("template", e.target.value)}
                    rows={8} className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
                <p className="text-[10px] -mt-1" style={{ color: "var(--muted)" }}>{"{{query}} {{context}} {{system_prompt}}"}</p>
              </>
            )}

            {/* LLM */}
            {selectedNode.type === "llm_generate" && (
              <>
                <Field label="Model (empty = default)">
                  <input value={(selectedNode.data?.model as string) || ""} onChange={(e) => updateNodeData("model", e.target.value)}
                    placeholder="e.g. gemini-2.5-flash" className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
                <Field label={`Temperature: ${((selectedNode.data?.temperature as number) ?? 0.7).toFixed(1)}`}>
                  <input type="range" min={0} max={1} step={0.1} value={(selectedNode.data?.temperature as number) ?? 0.7}
                    onChange={(e) => updateNodeData("temperature", parseFloat(e.target.value))} className="w-full" />
                </Field>
                <Field label="Max Tokens">
                  <input type="number" min={100} max={16000} value={(selectedNode.data?.max_tokens as number) || 4096}
                    onChange={(e) => updateNodeData("max_tokens", parseInt(e.target.value) || 4096)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
              </>
            )}

            {/* Parameter Extract */}
            {selectedNode.type === "parameter_extract" && (
              <Field label="Schema (JSON: field → description)">
                <textarea value={JSON.stringify(selectedNode.data?.schema || {}, null, 2)}
                  onChange={(e) => { try { updateNodeData("schema", JSON.parse(e.target.value)); } catch {} }}
                  rows={6} className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </Field>
            )}

            {/* HTTP Request */}
            {selectedNode.type === "http_request" && (
              <>
                <Field label="Method">
                  <select value={(selectedNode.data?.method as string) || "POST"}
                    onChange={(e) => updateNodeData("method", e.target.value)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
                    <option>GET</option><option>POST</option><option>PUT</option><option>DELETE</option>
                  </select>
                </Field>
                <Field label="URL">
                  <input value={(selectedNode.data?.url as string) || ""} onChange={(e) => updateNodeData("url", e.target.value)}
                    placeholder="https://api.example.com/..." className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
                <Field label="Body Template">
                  <textarea value={(selectedNode.data?.body_template as string) || ""} onChange={(e) => updateNodeData("body_template", e.target.value)}
                    rows={5} placeholder='{"name":"{{name}}"}' className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
              </>
            )}

            {/* If/Else */}
            {selectedNode.type === "if_else" && (
              <>
                <Field label="Variable (dot path)">
                  <input value={(selectedNode.data?.variable as string) || ""} onChange={(e) => updateNodeData("variable", e.target.value)}
                    placeholder="extracted_params.name" className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
                <Field label="Operator">
                  <select value={(selectedNode.data?.operator as string) || "not_empty"} onChange={(e) => updateNodeData("operator", e.target.value)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
                    <option value="exists">exists</option>
                    <option value="not_empty">not empty</option>
                    <option value="equals">equals</option>
                    <option value="contains">contains</option>
                  </select>
                </Field>
                {["equals", "contains"].includes((selectedNode.data?.operator as string) || "") && (
                  <Field label="Compare Value">
                    <input value={(selectedNode.data?.value as string) || ""} onChange={(e) => updateNodeData("value", e.target.value)}
                      className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                      style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                  </Field>
                )}
              </>
            )}

            {/* Answer */}
            {selectedNode.type === "answer" && (
              <Field label="Response Template (empty = use LLM output)">
                <textarea value={(selectedNode.data?.template as string) || ""} onChange={(e) => updateNodeData("template", e.target.value)}
                  rows={5} placeholder="Thank you {{name}}! Your data has been saved."
                  className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </Field>
            )}

            {/* Code Execute */}
            {selectedNode.type === "code_execute" && (
              <>
                <Field label="Python Code">
                  <textarea value={(selectedNode.data?.code as string) || ""} onChange={(e) => updateNodeData("code", e.target.value)}
                    rows={12} spellCheck={false}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                    style={{ background: "var(--background)", color: "#6366f1", border: "1px solid var(--border)", lineHeight: 1.6 }} />
                </Field>
                <p className="text-[10px] -mt-1" style={{ color: "var(--muted)" }}>
                  Define main(args) → dict. Args: query, answer, extracted_params, etc.
                </p>
              </>
            )}

            {/* Google Sheets */}
            {selectedNode.type === "google_sheets" && (
              <>
                {/* ── Credentials ── */}
                <div className="rounded-lg p-2.5" style={{ background: "rgba(22,163,74,0.06)", border: "1px solid rgba(22,163,74,0.2)" }}>
                  <p className="text-[10px] font-semibold mb-1.5" style={{ color: "#16a34a" }}>🔑 Google Service Account</p>
                  <textarea
                    value={(selectedNode.data?.service_account_json as string) || ""}
                    onChange={(e) => updateNodeData("service_account_json", e.target.value)}
                    rows={5}
                    placeholder={'{\n  "type": "service_account",\n  "client_email": "...",\n  "private_key": "-----BEGIN RSA PRIVATE KEY-----\\n..."\n}'}
                    className="w-full text-[10px] rounded-lg px-2 py-1.5 outline-none resize-y font-mono"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}
                  />
                  <p className="text-[9px] mt-1" style={{ color: "var(--muted)" }}>
                    Dán Service Account JSON từ Google Cloud Console. Để trống nếu đã cấu hình trong App Settings.
                  </p>
                </div>

                <Field label="Operation">
                  <select value={(selectedNode.data?.operation as string) || "append_row"}
                    onChange={(e) => updateNodeData("operation", e.target.value)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
                    <option value="find_row">Find Row (check duplicate)</option>
                    <option value="append_row">Append Row (write data)</option>
                  </select>
                </Field>
                <Field label="Spreadsheet ID">
                  <input value={(selectedNode.data?.spreadsheet_id as string) || ""}
                    onChange={(e) => updateNodeData("spreadsheet_id", e.target.value)}
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjg..."
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none font-mono"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>
                <Field label="Sheet Name">
                  <input value={(selectedNode.data?.sheet_name as string) || "Sheet1"}
                    onChange={(e) => updateNodeData("sheet_name", e.target.value)}
                    className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                    style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                </Field>

                {/* find_row fields */}
                {(selectedNode.data?.operation as string) === "find_row" && (<>
                  <Field label="Search Column (0=A, 1=B…)">
                    <input type="number" min={0} value={(selectedNode.data?.search_column as number) ?? 0}
                      onChange={(e) => updateNodeData("search_column", parseInt(e.target.value) || 0)}
                      className="w-full text-xs rounded-lg px-3 py-2 outline-none"
                      style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                  </Field>
                  <Field label="Search Value">
                    <input value={(selectedNode.data?.search_value as string) || ""}
                      onChange={(e) => updateNodeData("search_value", e.target.value)}
                      placeholder="{{student_id}}"
                      className="w-full text-xs rounded-lg px-3 py-2 outline-none font-mono"
                      style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                  </Field>
                  <div className="rounded-lg p-2 text-[10px]" style={{ background: "rgba(20,184,166,0.06)", color: "#14b8a6", border: "1px solid rgba(20,184,166,0.2)" }}>
                    Output: <code>google_sheets_found</code> = &quot;true&quot; / &quot;false&quot;<br/>
                    → dùng trong <strong>if_else</strong>: variable = <code>google_sheets_found</code>, operator = equals, value = true
                  </div>
                </>)}

                {/* append_row fields */}
                {((selectedNode.data?.operation as string) === "append_row" || !(selectedNode.data?.operation)) && (<>
                  <Field label="Row Mapping (JSON: header → value)">
                    <textarea
                      value={JSON.stringify(selectedNode.data?.row_mapping || {}, null, 2)}
                      onChange={(e) => { try { updateNodeData("row_mapping", JSON.parse(e.target.value)); } catch {} }}
                      rows={8} className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y font-mono"
                      style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
                  </Field>
                  <p className="text-[10px] -mt-1" style={{ color: "var(--muted)" }}>
                    Keys = column headers. Values support {"{{placeholders}}"} and <code>NOW()</code>.
                  </p>
                </>)}
              </>
            )}

            {/* Delete */}
            <div style={{ marginTop: "auto", paddingTop: 12 }}>
              <button onClick={() => {
                  setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
                  setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
                  setSelectedNode(null);
                }}
                className="w-full text-xs rounded-lg px-3 py-2 font-medium"
                style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.15)" }}>
                Delete Node
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Run Modal */}
      {runModal && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
          onClick={() => setRunModal(false)}>
          <div onClick={(e) => e.stopPropagation()} className="rounded-2xl p-6"
            style={{ background: "var(--card)", border: "1px solid var(--border)", width: 520, maxHeight: "80vh", overflow: "auto" }}>
            <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>🚀 Test Run</h3>
            <Field label="Query">
              <textarea value={runQuery} onChange={(e) => setRunQuery(e.target.value)} rows={3} placeholder="Enter your message..."
                className="w-full text-sm rounded-lg px-3 py-2 outline-none resize-none"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
            </Field>
            <button onClick={handleRun} disabled={running || !runQuery.trim()}
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium mt-2 mb-4"
              style={{ background: running ? "var(--border)" : "var(--accent)", color: "#fff" }}>
              {running ? <><div className="animate-spin rounded-full h-3 w-3 border-2 border-current" style={{ borderTopColor: "transparent" }} /> Running...</> : "Run"}
            </button>
            {runResult && (
              <div className="space-y-3">
                <Field label="Answer">
                  <div className="text-sm p-3 rounded-lg" style={{ background: "var(--background)", color: "var(--foreground)", whiteSpace: "pre-wrap" }}>
                    {runResult.answer}
                  </div>
                </Field>
                {Object.keys(runResult.extracted_params || {}).length > 0 && (
                  <Field label="Extracted Parameters">
                    <pre className="text-xs p-3 rounded-lg font-mono" style={{ background: "var(--background)", color: "#14b8a6" }}>
                      {JSON.stringify(runResult.extracted_params, null, 2)}
                    </pre>
                  </Field>
                )}
                {runResult.retriever_resources.length > 0 && (
                  <Field label={`Sources (${runResult.retriever_resources.length})`}>
                    <div className="flex flex-wrap gap-1.5">
                      {runResult.retriever_resources.map((r, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 rounded-md" style={{ background: "var(--accent-glow)", color: "var(--accent)" }}>
                          📄 {r.filename || "doc"} §{r.chunk_index}
                        </span>
                      ))}
                    </div>
                  </Field>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* Helper */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>{label}</label>
      {children}
    </div>
  );
}
