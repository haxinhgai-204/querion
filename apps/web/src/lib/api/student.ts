/**
 * Student API client — separate auth flow from admin.
 * Token stored under different localStorage keys.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const STUDENT_TOKEN_KEY = "querion-student-token";
const STUDENT_REFRESH_KEY = "querion-student-refresh";

export interface StudentInfo {
  id: string;
  email: string;
  name: string;
  student_id: string | null;
  must_change_password: boolean;
}

export interface PublishedApp {
  id: string;
  name: string;
  description: string | null;
}

export interface WorkspaceAppsGroup {
  workspace_name: string;
  apps: PublishedApp[];
}

// --- Token management ---
let accessToken: string | null = null;

export function setStudentToken(token: string | null) {
  accessToken = token;
}

export function getStudentToken() {
  return accessToken;
}

async function studentFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as Record<string, string> || {}) };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// --- Auth ---
export async function studentLogin(email: string, password: string) {
  const data = await studentFetch<{ access_token: string; refresh_token: string; student: StudentInfo }>("/v1/student/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  });
  accessToken = data.access_token;
  localStorage.setItem(STUDENT_TOKEN_KEY, data.access_token);
  localStorage.setItem(STUDENT_REFRESH_KEY, data.refresh_token);
  return data;
}

export async function studentRefresh(): Promise<boolean> {
  const rt = localStorage.getItem(STUDENT_REFRESH_KEY);
  if (!rt) return false;
  try {
    const data = await studentFetch<{ access_token: string }>("/v1/student/refresh", {
      method: "POST", body: JSON.stringify({ refresh_token: rt }),
    });
    accessToken = data.access_token;
    localStorage.setItem(STUDENT_TOKEN_KEY, data.access_token);
    return true;
  } catch { return false; }
}

export async function studentMe() {
  return studentFetch<StudentInfo>("/v1/student/me");
}

export async function studentChangePassword(newPassword: string) {
  return studentFetch<{ detail: string }>("/v1/student/change-password", {
    method: "POST", body: JSON.stringify({ new_password: newPassword }),
  });
}

export function studentLogout() {
  accessToken = null;
  localStorage.removeItem(STUDENT_TOKEN_KEY);
  localStorage.removeItem(STUDENT_REFRESH_KEY);
}

export function restoreStudentToken(): boolean {
  const t = localStorage.getItem(STUDENT_TOKEN_KEY);
  if (t) { accessToken = t; return true; }
  return false;
}

// --- Published apps ---
export async function listPublishedApps() {
  return studentFetch<WorkspaceAppsGroup[]>("/v1/student/apps");
}
