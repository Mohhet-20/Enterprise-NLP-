import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/useAuthStore";
import type { Dataset, DatasetProfile, DatasetRecord, UploadResponse, ValidationReport } from "@/types/api";

interface ListDatasetsParams {
  query?: string;
  task?: string;
  tag?: string;
  includeArchived?: boolean;
}

export function useDatasets(params: ListDatasetsParams = {}) {
  const search = new URLSearchParams();
  if (params.query) search.set("query", params.query);
  if (params.task) search.set("task", params.task);
  if (params.tag) search.set("tag", params.tag);
  if (params.includeArchived) search.set("include_archived", "true");

  return useQuery({
    queryKey: ["datasets", params],
    queryFn: () => apiRequest<Dataset[]>(`/datasets?${search.toString()}`),
  });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: ["datasets", id],
    queryFn: () => apiRequest<Dataset>(`/datasets/${id}`),
    enabled: !!id,
  });
}

export function useDatasetPreview(id: string | undefined, limit = 20) {
  return useQuery({
    queryKey: ["datasets", id, "preview", limit],
    queryFn: () => apiRequest<DatasetRecord[]>(`/datasets/${id}/preview?limit=${limit}`),
    enabled: !!id,
  });
}

export function useDatasetValidationReport(id: string | undefined) {
  return useQuery({
    queryKey: ["datasets", id, "validation-report"],
    queryFn: () => apiRequest<ValidationReport>(`/datasets/${id}/validation-report`),
    enabled: !!id,
  });
}

export function useDatasetProfile(id: string | undefined) {
  return useQuery({
    queryKey: ["datasets", id, "profile"],
    queryFn: () => apiRequest<DatasetProfile>(`/datasets/${id}/profile`),
    enabled: !!id,
    retry: false, // an empty dataset 400s here — not worth retrying
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; task: string; description?: string; label_set?: string[] }) =>
      apiRequest<Dataset>("/datasets", { method: "POST", body: payload }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useUploadDatasetCsv() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      datasetId,
      file,
      applyCleaning,
    }: {
      datasetId: string;
      file: File;
      applyCleaning: boolean;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      // File uploads use multipart/form-data, which the shared apiRequest
      // helper doesn't build (it always sends JSON) — a direct fetch call
      // here, but still going through the same auth-token + refresh-retry
      // pattern would duplicate a lot of code for one endpoint, so this
      // does a simpler one-shot authenticated request instead.
      const token = useAuthStore.getState().accessToken;
      const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

      const response = await fetch(
        `${baseUrl}/datasets/${datasetId}/upload?apply_cleaning=${applyCleaning}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.error?.message ?? `Upload failed with status ${response.status}`);
      }
      return response.json() as Promise<UploadResponse>;
    },
    onSuccess: (_, { datasetId }) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      queryClient.invalidateQueries({ queryKey: ["datasets", datasetId] });
    },
  });
}

export function useArchiveDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest<Dataset>(`/datasets/${id}/archive`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useRestoreDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest<Dataset>(`/datasets/${id}/restore`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useUpdateDatasetTags() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, tags }: { id: string; tags: string[] }) =>
      apiRequest<Dataset>(`/datasets/${id}/tags`, { method: "PUT", body: { tags } }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      queryClient.invalidateQueries({ queryKey: ["datasets", id] });
    },
  });
}

export function useCreateDatasetVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest<Dataset>(`/datasets/${id}/version`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useDatasetVersionHistory(id: string | undefined) {
  return useQuery({
    queryKey: ["datasets", id, "versions"],
    queryFn: () => apiRequest<Dataset[]>(`/datasets/${id}/versions`),
    enabled: !!id,
  });
}
