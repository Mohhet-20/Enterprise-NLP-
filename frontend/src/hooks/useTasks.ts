import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { NotServedTask, TaskInfo } from "@/types/api";

export function useTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: () => apiRequest<{ tasks: TaskInfo[]; not_served?: NotServedTask[] }>("/tasks", { auth: false }),
    staleTime: 5 * 60_000,
  });
}
