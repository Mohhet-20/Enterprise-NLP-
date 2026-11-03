import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { AuditLog } from "@/types/api";

export interface AuditLogFilters {
  action?: string;
  resourceType?: string;
  limit?: number;
}

/** GET /audit-logs — requires audit:read (Auditor, Admin, Super Admin); pass enabled=false for other roles. */
export function useAuditLogs(filters: AuditLogFilters, enabled: boolean) {
  const params = new URLSearchParams();
  if (filters.action) params.set("action", filters.action);
  if (filters.resourceType) params.set("resource_type", filters.resourceType);
  params.set("limit", String(filters.limit ?? 100));

  return useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => apiRequest<AuditLog[]>(`/audit-logs?${params.toString()}`),
    enabled,
  });
}
