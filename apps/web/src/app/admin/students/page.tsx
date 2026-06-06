"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface StudentItem {
  id: string;
  email: string;
  name: string;
  student_id: string | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
}

export default function AdminStudentsPage() {
  const { user, isSuper } = useAuth();
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addName, setAddName] = useState("");
  const [addSid, setAddSid] = useState("");
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; skipped: number; errors: string[] } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  const fetchStudents = useCallback(async () => {
    try { setStudents(await api.get<StudentItem[]>("/v1/students")); }
    catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchStudents(); }, [fetchStudents]);

  const handleAdd = async () => {
    if (!addEmail.trim() || !addName.trim()) return;
    setCreating(true);
    try {
      const s = await api.post<StudentItem>("/v1/students", { email: addEmail, name: addName, student_id: addSid || null });
      setStudents((prev) => [s, ...prev]);
      setShowAdd(false);
      setAddEmail(""); setAddName(""); setAddSid("");
    } catch { /* silent */ }
    finally { setCreating(false); }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await api.upload<{ created: number; skipped: number; errors: string[] }>("/v1/students/import", formData);
      setImportResult(result);
      fetchStudents();
    } catch (err: any) {
      alert(err.message || "Failed to import file");
    }
    finally { setImporting(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const toggleActive = async (id: string, currentStatus: boolean) => {
    try {
      await api.patch(`/v1/students/${id}`, { is_active: !currentStatus });
      setStudents((prev) => prev.map((s) => s.id === id ? { ...s, is_active: !currentStatus } : s));
    } catch { /* silent */ }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/v1/students/${deleteTarget}`);
      setStudents((prev) => prev.filter((s) => s.id !== deleteTarget));
      setDeleteTarget(null);
    } catch (err: any) {
      alert(err.message || "Failed to delete student");
      setDeleteTarget(null);
    }
  };

  if (!isAdmin) return <div className="text-center py-20 text-sm" style={{ color: "var(--muted)" }}>Access denied</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>Students</h2>
          <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>Manage student accounts (default password: querion123)</p>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.docx" className="hidden" onChange={handleImport} />
          <button onClick={() => fileRef.current?.click()} disabled={importing}
            className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium"
            style={{ background: "var(--card)", color: "var(--foreground)", border: "1px solid var(--border)" }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1V10M3 6L7 10L11 6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            {importing ? "Importing..." : "Import File"}
          </button>
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium"
            style={{ background: "var(--accent)", color: "#fff" }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2V12M2 7H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            Add Student
          </button>
        </div>
      </div>

      {/* Import result */}
      {importResult && (
        <div className="rounded-xl px-4 py-3 mb-4 text-sm" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", color: "#22c55e" }}>
          ✅ Imported: {importResult.created} created, {importResult.skipped} skipped
          {importResult.errors.length > 0 && (
            <div className="mt-1 text-xs" style={{ color: "#f59e0b" }}>
              {importResult.errors.map((e, i) => <p key={i}>{e}</p>)}
            </div>
          )}
          <button onClick={() => setImportResult(null)} className="ml-3 text-xs underline">Dismiss</button>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-current" style={{ borderTopColor: "transparent", color: "var(--accent)" }} />
        </div>
      ) : students.length === 0 ? (
        <div className="text-center py-20">
          <h3 className="text-lg font-semibold mb-1" style={{ color: "var(--foreground)" }}>No students yet</h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>Create students or import from CSV, Excel, or Word</p>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "var(--card)" }}>
                <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Name</th>
                <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Email</th>
                <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Student ID</th>
                <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Status</th>
                <th className="text-left px-4 py-2.5 font-semibold" style={{ color: "var(--muted)" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="px-4 py-2.5 font-medium" style={{ color: "var(--foreground)" }}>{s.name}</td>
                  <td className="px-4 py-2.5" style={{ color: "var(--foreground)" }}>{s.email}</td>
                  <td className="px-4 py-2.5" style={{ color: "var(--muted)" }}>{s.student_id || "—"}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{
                      background: s.is_active ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)",
                      color: s.is_active ? "#22c55e" : "#ef4444",
                    }}>
                      {s.is_active ? (s.must_change_password ? "New" : "Active") : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleActive(s.id, s.is_active)}
                        className="text-[11px] px-2 py-1 rounded font-medium transition-colors"
                        style={{
                          color: s.is_active ? "#ef4444" : "#22c55e",
                          border: `1px solid ${s.is_active ? "rgba(239,68,68,0.2)" : "rgba(34,197,94,0.2)"}`,
                          background: "transparent"
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = s.is_active ? "rgba(239,68,68,0.05)" : "rgba(34,197,94,0.05)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                      >
                        {s.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        onClick={() => setDeleteTarget(s.id)}
                        className="text-[11px] px-2 py-1 rounded font-medium transition-colors"
                        style={{
                          color: "#ef4444",
                          border: "1px solid rgba(239,68,68,0.2)",
                          background: "transparent"
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = "rgba(239,68,68,0.05)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Modal */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
          onClick={() => setShowAdd(false)}>
          <div onClick={(e) => e.stopPropagation()} className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)", width: 440 }}>
            <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Add Student</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>Email *</label>
                <input value={addEmail} onChange={(e) => setAddEmail(e.target.value)} placeholder="student@university.edu" autoFocus
                  className="w-full text-sm rounded-lg px-3 py-2 outline-none"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </div>
              <div>
                <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>Name *</label>
                <input value={addName} onChange={(e) => setAddName(e.target.value)} placeholder="Student Name"
                  className="w-full text-sm rounded-lg px-3 py-2 outline-none"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </div>
              <div>
                <label className="text-[11px] font-semibold block mb-1" style={{ color: "var(--muted)" }}>Student ID (optional)</label>
                <input value={addSid} onChange={(e) => setAddSid(e.target.value)} placeholder="SV001"
                  className="w-full text-sm rounded-lg px-3 py-2 outline-none"
                  style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }} />
              </div>
            </div>
            <p className="text-[10px] mt-3" style={{ color: "var(--muted)" }}>Default password: <strong>querion123</strong></p>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowAdd(false)} className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={handleAdd} disabled={creating || !addEmail.trim() || !addName.trim()}
                className="rounded-lg px-4 py-2 text-xs font-medium"
                style={{ background: "var(--accent)", color: "#fff" }}>{creating ? "..." : "Add"}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        message="Are you sure you want to permanently delete this student?"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
