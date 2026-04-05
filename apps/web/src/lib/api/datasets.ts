import { api } from "../api";

export interface DatasetResponse {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentResponse {
  id: string;
  dataset_id: string;
  filename: string;
  content_type: string;
  size: number;
  status: "uploaded" | "indexing" | "ready" | "failed";
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetDetailResponse extends DatasetResponse {
  documents: DocumentResponse[];
}

export function createDataset(name: string, description?: string) {
  return api.post<DatasetResponse>("/v1/datasets", { name, description });
}

export function listDatasets() {
  return api.get<DatasetResponse[]>("/v1/datasets");
}

export function getDataset(id: string) {
  return api.get<DatasetDetailResponse>(`/v1/datasets/${id}`);
}

export function deleteDataset(id: string) {
  return api.delete(`/v1/datasets/${id}`);
}

export function getDocument(id: string) {
  return api.get<DocumentResponse>(`/v1/documents/${id}`);
}

export function deleteDocument(id: string) {
  return api.delete(`/v1/documents/${id}`);
}

export function indexDocument(id: string) {
  return api.post<{ status: string; job_id: string }>(`/v1/documents/${id}/index`);
}

export interface ChunkResponse {
  id: string;
  chunk_index: number;
  content: string;
  content_preview: string;
}

export interface ChunksPageResponse {
  total: number;
  page: number;
  page_size: number;
  chunks: ChunkResponse[];
}

export function getDocumentChunks(docId: string, page = 1, pageSize = 20) {
  return api.get<ChunksPageResponse>(`/v1/documents/${docId}/chunks?page=${page}&page_size=${pageSize}`);
}

export function updateChunk(chunkId: string, content: string) {
  return api.patch<ChunkResponse & { re_embedded: boolean }>(`/v1/chunks/${chunkId}`, { content });
}
