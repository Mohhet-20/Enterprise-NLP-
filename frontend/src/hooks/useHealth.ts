import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiRequest<HealthResponse>("/health", { auth: false }),
    refetchInterval: 30_000,
    retry: 1,
  });
}
