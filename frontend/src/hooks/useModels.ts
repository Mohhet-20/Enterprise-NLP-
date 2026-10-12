import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { ModelLifecycleStage, ModelRegistryEntry } from "@/types/api";

export function useModels(params: { task?: string; stage?: string } = {}) {
  const search = new URLSearchParams();
  if (params.task) search.set("task", params.task);
  if (params.stage) search.set("stage", params.stage);

  return useQuery({
    queryKey: ["models", params],
    queryFn: () => apiRequest<ModelRegistryEntry[]>(`/models?${search.toString()}`),
  });
}

export function useModel(id: string | undefined) {
  return useQuery({
    queryKey: ["models", id],
    queryFn: () => apiRequest<ModelRegistryEntry>(`/models/${id}`),
    enabled: !!id,
  });
}

export function useRegisterModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      name: string;
      task: string;
      architecture: string;
      version: string;
      model_name_or_path: string;
      notes?: string;
    }) => apiRequest<ModelRegistryEntry>("/models", { method: "POST", body: payload }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

function useModelAction(action: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body?: unknown }) =>
      apiRequest<ModelRegistryEntry>(`/models/${id}/${action}`, { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

export function useApproveModel() {
  return useModelAction("approve");
}

export function useRejectModel() {
  return useModelAction("reject");
}

export function usePromoteModel() {
  const mutation = useModelAction("promote");
  return {
    ...mutation,
    mutate: (params: { id: string; stage: ModelLifecycleStage }) =>
      mutation.mutate({ id: params.id, body: { stage: params.stage } }),
    mutateAsync: (params: { id: string; stage: ModelLifecycleStage }) =>
      mutation.mutateAsync({ id: params.id, body: { stage: params.stage } }),
  };
}

export function useDeployModel() {
  return useModelAction("deploy");
}

export function useRollbackModel() {
  return useModelAction("rollback");
}

export function useSetChampion() {
  return useModelAction("set-champion");
}

export function useCompareModels(idA: string | undefined, idB: string | undefined) {
  return useQuery({
    queryKey: ["models", "compare", idA, idB],
    queryFn: () => apiRequest(`/models/compare/${idA}/${idB}`),
    enabled: !!idA && !!idB && idA !== idB,
  });
}
