"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useAuth, useWorkspace, usePermission } from "@/components/providers/AuthProvider";
import { useI18n } from "@/components/providers/I18nProvider";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface MemberItem {
  user_id: string;
  email: string;
  name: string;
  ws_role: string;
  created_at: string;
}

interface UserOption {
  id: string;
  email: string;
  name: string;
}

const roleBadge: Record<string, { bg: string; color: string }> = {
  owner: { bg: "rgba(34,197,94,0.15)", color: "#22c55e" },
  editor: { bg: "rgba(59,130,246,0.15)", color: "#3b82f6" },
  viewer: { bg: "rgba(168,85,247,0.15)", color: "#a855f7" },
};

export default function MembersPanel() {
  const { isSuper } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const { canManageMembers } = usePermission();
  const { t } = useI18n();
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ user_id: "", ws_role: "viewer" });
  const [error, setError] = useState("");
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; name: string } | null>(null);

  const wsId = activeWorkspace?.workspace_id;

  const fetchMembers = async () => {
    if (!wsId) return;
    setLoading(true);
    try {
      const data = await api.get<MemberItem[]>(`/v1/workspaces/${wsId}/members`);
      setMembers(data);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    if (!isSuper) return;
    try {
      const data = await api.get<UserOption[]>("/v1/users");
      setUsers(data.filter((u) => !members.some((m) => m.user_id === u.id)));
    } catch {}
  };

  useEffect(() => { fetchMembers(); }, [wsId]);
  useEffect(() => { if (showInvite) fetchUsers(); }, [showInvite, members]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post(`/v1/workspaces/${wsId}/members`, inviteForm);
      setShowInvite(false);
      setInviteForm({ user_id: "", ws_role: "viewer" });
      fetchMembers();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await api.patch(`/v1/workspaces/${wsId}/members/${userId}`, { ws_role: newRole });
      fetchMembers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRemoveConfirmed = async () => {
    if (!removeTarget) return;
    try {
      await api.delete(`/v1/workspaces/${wsId}/members/${removeTarget.userId}`);
      setRemoveTarget(null);
      fetchMembers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (!wsId) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-sm" style={{ color: "var(--muted)" }}>No workspace selected</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>
          Workspace Members
        </h3>
        {canManageMembers && (
          <button
            onClick={() => setShowInvite(!showInvite)}
            className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-white"
            style={{ background: "var(--accent)" }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 2V12M2 7H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            Invite
          </button>
        )}
      </div>

      {/* Invite form */}
      {showInvite && canManageMembers && (
        <form
          onSubmit={handleInvite}
          className="rounded-xl p-4 mb-4 flex flex-wrap gap-3 items-end"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          {error && <p className="w-full text-sm" style={{ color: "#ef4444" }}>{error}</p>}
          <select
            value={inviteForm.user_id} required
            onChange={(e) => setInviteForm({ ...inviteForm, user_id: e.target.value })}
            className="flex-1 min-w-[200px] rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          >
            <option value="">Select user...</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
            ))}
          </select>
          <select
            value={inviteForm.ws_role}
            onChange={(e) => setInviteForm({ ...inviteForm, ws_role: e.target.value })}
            className="rounded-lg px-3 py-2 text-sm outline-none"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="owner">Owner</option>
          </select>
          <button type="submit" className="rounded-lg px-4 py-2 text-sm font-medium text-white" style={{ background: "var(--accent)" }}>
            Invite
          </button>
          <button type="button" onClick={() => setShowInvite(false)} className="rounded-lg px-4 py-2 text-sm" style={{ color: "var(--muted)" }}>
            Cancel
          </button>
        </form>
      )}

      {/* Members list */}
      <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        {members.map((m, i) => (
          <div
            key={m.user_id}
            className="flex items-center justify-between px-4 py-3 transition-colors"
            style={{ borderBottom: i < members.length - 1 ? "1px solid var(--border)" : "none" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--card-hover)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          >
            <div className="flex items-center gap-3">
              <div
                className="flex items-center justify-center rounded-full text-xs font-bold"
                style={{
                  width: 32, height: 32,
                  background: "linear-gradient(135deg, var(--accent) 0%, #a855f7 100%)",
                  color: "#fff",
                }}
              >
                {m.name[0]?.toUpperCase() || "?"}
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{m.name}</p>
                <p className="text-xs" style={{ color: "var(--muted)" }}>{m.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {canManageMembers ? (
                <select
                  value={m.ws_role}
                  onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                  className="rounded px-2 py-1 text-xs font-medium outline-none cursor-pointer"
                  style={{
                    background: roleBadge[m.ws_role]?.bg || "var(--card)",
                    color: roleBadge[m.ws_role]?.color || "var(--foreground)",
                    border: "none",
                  }}
                >
                  <option value="owner">owner</option>
                  <option value="editor">editor</option>
                  <option value="viewer">viewer</option>
                </select>
              ) : (
                <span
                  className="text-xs px-2 py-0.5 rounded font-medium"
                  style={{
                    background: roleBadge[m.ws_role]?.bg,
                    color: roleBadge[m.ws_role]?.color,
                  }}
                >
                  {m.ws_role}
                </span>
              )}
              {canManageMembers && (
                <button
                  onClick={() => setRemoveTarget({ userId: m.user_id, name: m.name })}
                  className="rounded p-1 transition-colors"
                  style={{ color: "var(--muted)" }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = "#ef4444"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = "var(--muted)"; }}
                  title="Remove member"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M3 3L11 11M3 11L11 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>Loading...</p>}
        {!loading && members.length === 0 && (
          <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>No members</p>
        )}
      </div>

      <ConfirmDialog
        open={!!removeTarget}
        message={removeTarget ? `Remove ${removeTarget.name} from workspace?` : ""}
        variant="danger"
        onConfirm={handleRemoveConfirmed}
        onCancel={() => setRemoveTarget(null)}
      />
    </div>
  );
}
