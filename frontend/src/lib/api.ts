import axios from "axios";
import type { Comparison, Metrics, Study, FileArtifact, UserAuth } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "/api").replace(/\/$/, "");

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => typeof item?.msg === "string" ? item.msg : "Invalid input.").join(" ");
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Unknown error";
}

const api = axios.create({
  baseURL: API_BASE
});

export async function registerUser(email: string, password: string) {
  return api.post<UserAuth>("auth/register", { email, password }).then((res) => res.data);
}

export async function loginUser(email: string, password: string) {
  return api.post<UserAuth>("auth/login", { email, password }).then((res) => res.data);
}

export async function fetchHealth() {
  return api.get<{ status: string }>("/health").then((res) => res.data);
}

export async function fetchStudies() {
  return api.get<Study[]>("/studies").then((res) => res.data);
}

export async function fetchStudy(id: string) {
  return api.get<Study>(`/studies/${id}`).then((res) => res.data);
}

export async function deleteStudy(id: string) {
  await api.delete(`/studies/${id}`);
}

export async function runStudy(id: string) {
  return api.post<{ status: string; metrics: Metrics }>(`/studies/${id}/run`).then((res) => res.data);
}

export async function fetchMetrics(id: string) {
  return api.get<Metrics>(`/studies/${id}/metrics`).then((res) => res.data);
}

export async function fetchFiles(id: string) {
  return api.get<FileArtifact[]>(`/studies/${id}/files`).then((res) => res.data);
}

export async function uploadStudy(formData: FormData) {
  return api.post<Study>("/studies/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  }).then((res) => res.data);
}

export async function compareStudies(study_a_id: string, study_b_id: string) {
  return api.post<Comparison>("/compare", { study_a_id, study_b_id }).then((res) => res.data);
}

export async function fetchStorageOverview() {
  return api.get<{ usage: Record<string, { bytes: number; files: number }>; auto_delete_days: number; auto_delete_enabled: boolean }>(
    "/admin/storage"
  ).then((res) => res.data);
}

export async function updateRetention(payload: { days: number; enabled: boolean }) {
  return api.post("/admin/retention", payload).then((res) => res.data);
}

export default api;
