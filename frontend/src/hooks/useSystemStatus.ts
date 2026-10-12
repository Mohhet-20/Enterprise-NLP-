import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { OverallStatus } from "@/types/api";

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: () => apiRequest<OverallStatus>("/status", { auth: false }),
    refetchInterval: 30_000,
  });
}
