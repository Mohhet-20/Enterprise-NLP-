import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Cpu, Gauge, Server } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { useInferenceMetrics, useSystemResources } from "@/hooks/useMonitoring";
import { useSystemStatus } from "@/hooks/useSystemStatus";
import { ApiError } from "@/lib/api";

function ResourceBar({ label, percent }: { label: string; percent: number | undefined }) {
  const value = percent ?? 0;
  const tone = value >= 90 ? "bg-destructive" : value >= 75 ? "bg-amber-500" : "bg-primary";
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{percent === undefined ? "—" : `${value.toFixed(0)}%`}</span>
      </div>
      <div
        className="h-2 rounded-full bg-muted"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

export function MonitoringPage() {
  const metrics = useInferenceMetrics();
  const system = useSystemResources();
  const status = useSystemStatus();

  const rows = Object.entries(metrics.data ?? {})
    .map(([key, s]) => {
      const [task, ...model] = key.split(":");
      return { key, task, model: model.join(":"), ...s };
    })
    .sort((a, b) => b.count - a.count);
  const totalRequests = rows.reduce((sum, r) => sum + r.count, 0);
  const weightedLatency = totalRequests ? rows.reduce((sum, r) => sum + r.avg_latency_ms * r.count, 0) / totalRequests : 0;
  const weightedErrors = totalRequests ? rows.reduce((sum, r) => sum + r.error_rate * r.count, 0) / totalRequests : 0;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Monitoring</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Live inference traffic, latency and error rates per model, plus host resources. Refreshes every 10 seconds.
          Counters are kept in this API process and reset when it restarts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: Activity, label: "Inference requests", value: totalRequests.toLocaleString() },
          { icon: Gauge, label: "Avg latency", value: totalRequests ? `${weightedLatency.toFixed(1)} ms` : "—" },
          { icon: Server, label: "Error rate", value: totalRequests ? `${(weightedErrors * 100).toFixed(2)}%` : "—" },
        ].map(({ icon: Icon, label, value }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-4 pt-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                {metrics.isLoading ? <Skeleton className="mt-1 h-6 w-16" /> : <p className="text-xl font-semibold">{value}</p>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Latency by model</CardTitle>
            <CardDescription>Average milliseconds per request, from /api/v1/metrics.</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            {metrics.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : rows.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No inference requests yet. Run a prediction in the Playground and it shows up here.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows}>
                  <XAxis dataKey="task" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis unit=" ms" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip
                    contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }}
                    formatter={(v: number) => [`${v.toFixed(1)} ms`, "Avg latency"]}
                    labelFormatter={(_, payload) => (payload?.[0]?.payload as { key?: string } | undefined)?.key ?? ""}
                  />
                  <Bar dataKey="avg_latency_ms" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-4 w-4" /> Host resources
            </CardTitle>
            <CardDescription>From /api/v1/system.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {system.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : system.data?.status !== "ok" ? (
              <p className="text-sm text-muted-foreground">{system.data?.detail ?? "Resource metrics are unavailable."}</p>
            ) : (
              <>
                <ResourceBar label="CPU" percent={system.data.cpu_percent} />
                <ResourceBar label="Memory" percent={system.data.memory_percent} />
                <ResourceBar label="Disk" percent={system.data.disk_percent} />
              </>
            )}
            <div className="mt-2 flex flex-col gap-2 border-t pt-4">
              {status.isLoading ? (
                <Skeleton className="h-20 w-full" />
              ) : (
                Object.entries(status.data?.checks ?? {}).map(([name, check]) => (
                  <div key={name} className="flex items-center justify-between text-sm">
                    <span className="capitalize text-muted-foreground">{name.replace(/_/g, " ")}</span>
                    <Badge variant={check.status === "ok" ? "default" : check.status === "not_implemented" ? "outline" : "destructive"}>
                      {check.status}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Per-model breakdown</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {metrics.error ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {metrics.error instanceof ApiError ? metrics.error.message : "Failed to load metrics."}
            </div>
          ) : rows.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No traffic recorded since the API started.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead className="text-right">Avg latency</TableHead>
                  <TableHead className="text-right">Error rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.key}>
                    <TableCell className="font-mono text-xs">{r.task}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{r.model}</TableCell>
                    <TableCell className="text-right">{r.count.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{r.avg_latency_ms.toFixed(1)} ms</TableCell>
                    <TableCell className="text-right">
                      <Badge variant={r.error_rate > 0.05 ? "destructive" : "secondary"}>{(r.error_rate * 100).toFixed(2)}%</Badge>
                    </TableCell>
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
