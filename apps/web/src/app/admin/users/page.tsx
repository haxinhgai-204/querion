"use client";

import { useAuth } from "@/components/providers/AuthProvider";
import { useI18n } from "@/components/providers/I18nProvider";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface UserItem {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  workspaces: { workspace_id: string; ws_role: string }[];
}

export default function AdminUsersPage() {
  const { isSuper } = useAuth();
  const { t } = useI18n();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const data = await api.get<UserItem[]>("/v1/users");
      setUsers(data);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/v1/users", form);
      setShowCreate(false);
      setForm({ email: "", password: "", name: "" });
      fetchUsers();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const toggleActive = async (userId: string, isActive: boolean) => {
    await api.patch(`/v1/users/${userId}`, { is_active: !isActive });
    fetchUsers();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/v1/users/${deleteTarget}`);
      setDeleteTarget(null);
      fetchUsers();
    } catch (err: any) {
      alert(err.message || "Failed to delete user");
      setDeleteTarget(null);
    }
  };

  if (!isSuper) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--muted)" }}>Access denied. Super admin only.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>
            Users Management
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Create and manage admin users
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white"
          style={{ background: "var(--accent)" }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          {t("buttons.create")} User
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="rounded-xl p-4 mb-6 flex flex-wrap gap-3 items-end"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          {error && <p className="w-full text-sm" style={{ color: "#ef4444" }}>{error}</p>}
          <input
            type="email" placeholder="Email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="flex-1 min-w-[200px] rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          />
          <input
            type="text" placeholder="Name" required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="flex-1 min-w-[150px] rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          />
          <input
            type="password" placeholder="Password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="flex-1 min-w-[150px] rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          />
          <button type="submit" className="rounded-lg px-4 py-2 text-sm font-medium text-white" style={{ background: "var(--accent)" }}>
            {t("buttons.create")}
          </button>
          <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm" style={{ color: "var(--muted)" }}>
            {t("buttons.cancel")}
          </button>
        </form>
      )}

      {/* Table */}
      <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "var(--card)" }}>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>Email</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>Name</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>Role</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>Status</th>
              <th className="text-right px-4 py-3 font-medium" style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} style={{ borderBottom: "1px solid var(--border)" }}
                className="transition-colors" onMouseEnter={(e) => { e.currentTarget.style.background = "var(--card-hover)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>{u.email}</td>
                <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>{u.name}</td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 rounded font-medium"
                    style={{
                      background: u.role === "super_admin" ? "rgba(239,68,68,0.15)" : "rgba(59,130,246,0.15)",
                      color: u.role === "super_admin" ? "#ef4444" : "#3b82f6",
                    }}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 rounded font-medium"
                    style={{
                      background: u.is_active ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                      color: u.is_active ? "#22c55e" : "#ef4444",
                    }}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {u.role !== "super_admin" && (
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => toggleActive(u.id, u.is_active)}
                        className="text-xs px-2 py-1 rounded transition-colors"
                        style={{
                          color: u.is_active ? "#ef4444" : "#22c55e",
                          border: `1px solid ${u.is_active ? "rgba(239,68,68,0.2)" : "rgba(34,197,94,0.2)"}`
                        }}
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        onClick={() => setDeleteTarget(u.id)}
                        className="text-xs px-2 py-1 rounded"
                        style={{ color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>Loading...</p>}
        {!loading && users.length === 0 && <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>No users found</p>}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        message="Are you sure you want to permanently delete this user?"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
