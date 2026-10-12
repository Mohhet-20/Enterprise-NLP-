import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { TaskInfo } from "@/types/api";

export function useTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: () => apiRequest<{ tasks: TaskInfo[] }>("/tasks", { auth: false }),
    staleTime: 5 * 60_000,
  });
}
