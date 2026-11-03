import { useState } from "react";
import { Lock, ScrollText, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { useAuthStore } from "@/stores/useAuthStore";
import { hasPermission } from "@/lib/permissions";
import { ApiError } from "@/lib/api";

function summarize(details: Record<string, unknown>): string {
  const entries = Object.entries(details);
  if (entries.length === 0) return "—";
  return entries
    .slice(0, 3)
    .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}

export function AdminPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canRead = hasPermission(role, "audit:read");
  const [action, setAction] = useState("");
  const [resourceType, setResourceType] = useState("");
  const logs = useAuditLogs({ action: action.trim() || undefined, resourceType: resourceType.trim() || undefined }, canRead);

  if (!canRead) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md text-center">
          <CardContent className="flex flex-col items-center gap-3 pt-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Lock className="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 className="font-display text-lg font-semibold">No audit access</h2>
            <p className="text-sm text-muted-foreground">
              Your role ({role?.replace(/_/g, " ")}) can't read the audit trail. It is limited to the Auditor, Admin and
              Super Admin roles, and the API enforces this on every request.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every sign-in, dataset change, model promotion and evaluation run, newest first. Filter by exact action or
          resource type.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            aria-label="Filter by action"
            placeholder="Action, e.g. auth.login"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="pl-8"
          />
        </div>
        <Input
          aria-label="Filter by resource type"
          placeholder="Resource type, e.g. dataset"
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
          className="w-full max-w-xs"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {logs.isLoading ? (
            <div className="flex flex-col gap-3 p-5">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : logs.error ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {logs.error instanceof ApiError ? logs.error.message : "Failed to load the audit log."}
            </div>
          ) : !logs.data || logs.data.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-12 text-center text-sm text-muted-foreground">
              <ScrollText className="h-6 w-6" />
              <p>No audit entries match.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Details</TableHead>
                  <TableHead>IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.data.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">{log.actor_username ?? "system"}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-mono">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {log.resource_type ? `${log.resource_type}${log.resource_id ? `/${log.resource_id.slice(0, 8)}` : ""}` : "—"}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-xs text-muted-foreground" title={JSON.stringify(log.details)}>
                      {summarize(log.details)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{log.ip_address ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
