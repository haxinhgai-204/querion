import { api } from "../api";

export interface WorkflowResponse {
  id: string;
  type: string;
  name: string;
  description: string | null;
  dataset_id: string | null;
  graph_json: GraphJSON;
  node_count: number;
  created_at: string;
  updated_at: string;
}

export interface GraphJSON {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
}

export interface RunResult {
  answer: string;
  extracted_params: Record<string, any>;
  retriever_resources: Array<{
    chunk_id: string;
    content_preview: string;
    chunk_index: number;
    document_id: string;
    dataset_id: string;
    filename: string;
    score: number;
  }>;
}

export function createWorkflow(name: string, type: string = "chatflow", description?: string, datasetId?: string) {
  return api.post<WorkflowResponse>("/v1/workflows", {
    name,
    type,
    description: description || "",
    dataset_id: datasetId || null,
    graph_json: { nodes: [], edges: [] },
  });
}

export function listWorkflows() {
  return api.get<WorkflowResponse[]>("/v1/workflows");
}

export function getWorkflow(id: string) {
  return api.get<WorkflowResponse>(`/v1/workflows/${id}`);
}

export function updateWorkflow(id: string, data: { name?: string; type?: string; description?: string; dataset_id?: string; graph_json?: GraphJSON }) {
  return api.patch<WorkflowResponse>(`/v1/workflows/${id}`, data);
}

export function deleteWorkflow(id: string) {
  return api.delete(`/v1/workflows/${id}`);
}

export function runWorkflow(id: string, query: string, inputs?: Record<string, any>) {
  return api.post<RunResult>(`/v1/workflows/${id}/run`, { query, inputs });
}
