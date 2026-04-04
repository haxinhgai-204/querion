"use client";

import { usePermission, type WorkspaceMembership } from "@/components/providers/AuthProvider";
import type { ReactNode } from "react";

interface PermissionGateProps {
  children: ReactNode;
  /** Minimum ws_role required to show children */
  wsRole?: "owner" | "editor" | "viewer";
  /** If true, only super_admin can see */
  superOnly?: boolean;
  /** Optional fallback when permission denied */
  fallback?: ReactNode;
}

export default function PermissionGate({
  children,
  wsRole,
  superOnly = false,
  fallback = null,
}: PermissionGateProps) {
  const { canEdit, canManageMembers, isOwner, isSuper } = usePermission();

  if (superOnly && !isSuper) return <>{fallback}</>;

  if (wsRole === "owner" && !isOwner) return <>{fallback}</>;
  if (wsRole === "editor" && !canEdit) return <>{fallback}</>;
  // viewer = everyone has access

  return <>{children}</>;
}
