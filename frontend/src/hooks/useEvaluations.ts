import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/useAuthStore";
import type { EvaluationRunResult, EvaluationRunSummary, NLPTask } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function useEvaluationRuns() {
  return useQuery({
    queryKey: ["evaluations"],
    queryFn: () => apiRequest<EvaluationRunSummary[]>("/evaluation/runs"),
  });
}

export function useEvaluationRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["evaluations", runId],
    queryFn: () => apiRequest<EvaluationRunResult>(`/evaluation/runs/${runId}`),
    enabled: !!runId,
  });
}

export function useRunEvaluation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (task: NLPTask) =>
      apiRequest<EvaluationRunResult>("/evaluation/run", { method: "POST", body: { task } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evaluations"] }),
  });
}

/** Triggers a real browser download for an authenticated endpoint — a
 * plain <a href> can't attach an Authorization header, so this fetches
 * the file as a blob first and then simulates a click on an object URL. */
async function downloadAuthenticated(path: string, filename: string) {
  const token = useAuthStore.getState().accessToken;
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error(`Download failed with status ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function useDownloadEvaluationReport() {
  return useMutation({
    mutationFn: (runId: string) =>
      downloadAuthenticated(`/evaluation/runs/${runId}/report`, `evaluation-report-${runId}.md`),
  });
}

export function useDownloadMisclassifiedCsv() {
  return useMutation({
    mutationFn: (runId: string) =>
      downloadAuthenticated(`/evaluation/runs/${runId}/misclassified.csv`, `misclassified-${runId}.csv`),
  });
}
