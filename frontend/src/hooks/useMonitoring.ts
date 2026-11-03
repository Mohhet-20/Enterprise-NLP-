import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { InferenceMetrics, SystemResources } from "@/types/api";

/** Per task:model inference counters from the in-process metrics registry (GET /metrics). */
export function useInferenceMetrics() {
  return useQuery({
    queryKey: ["inference-metrics"],
    queryFn: () => apiRequest<InferenceMetrics>("/metrics", { auth: false }),
    refetchInterval: 10_000,
  });
}

/** Host CPU, memory and disk usage (GET /system); "unavailable" when psutil is missing. */
export function useSystemResources() {
  return useQuery({
    queryKey: ["system-resources"],
    queryFn: () => apiRequest<SystemResources>("/system", { auth: false }),
    refetchInterval: 10_000,
  });
}
