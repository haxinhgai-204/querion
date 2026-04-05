import { api } from "../api";

export interface AppResponse {
  id: string;
  name: string;
  workflow_id: string | null;
  dataset_id: string | null;
  model_config_json: Record<string, any> | null;
  system_prompt: string | null;
  api_key: string;
  description: string | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface RunResponse {
  id: string;
  app_id: string | null;
  workflow_id: string | null;
  conversation_id: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  latency_ms: number | null;
}

export interface RunStepResponse {
  id: string;
  node_id: string;
  node_type: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  input_json: Record<string, any> | null;
  output_json: Record<string, any> | null;
}

export function createApp(data: { name: string; workflow_id?: string; model_config_json?: Record<string, any>; system_prompt?: string }) {
  return api.post<AppResponse>("/v1/apps", data);
}

export function listApps() {
  return api.get<AppResponse[]>("/v1/apps");
}

export function getApp(id: string) {
  return api.get<AppResponse>(`/v1/apps/${id}`);
}

export function updateApp(id: string, data: { name?: string; workflow_id?: string; dataset_id?: string; model_config_json?: Record<string, any>; system_prompt?: string; description?: string; is_published?: boolean }) {
  return api.patch<AppResponse>(`/v1/apps/${id}`, data);
}

export function deleteApp(id: string) {
  return api.delete(`/v1/apps/${id}`);
}

export function regenerateApiKey(id: string) {
  return api.post<AppResponse>(`/v1/apps/${id}/regenerate-key`);
}

export function listRuns(appId: string) {
  return api.get<RunResponse[]>(`/v1/apps/${appId}/runs`);
}

export function getRunSteps(runId: string) {
  return api.get<RunStepResponse[]>(`/v1/runs/${runId}/steps`);
}
