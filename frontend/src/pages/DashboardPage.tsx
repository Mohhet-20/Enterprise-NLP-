import { Link } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Boxes, Database, ClipboardList, Lock, Server } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useDatasets } from "@/hooks/useDatasets";
import { useModels } from "@/hooks/useModels";
import { useEvaluationRuns } from "@/hooks/useEvaluations";
import { useSystemStatus } from "@/hooks/useSystemStatus";
import { useAuthStore } from "@/stores/useAuthStore";
import { ApiError } from "@/lib/api";

function KpiCard({
  icon: Icon,
  label,
  value,
  isLoading,
  isForbidden,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  isLoading: boolean;
  isForbidden: boolean;
  href?: string;
}) {
  const content = (
    <Card className={href && !isForbidden ? "transition-colors hover:bg-secondary/30" : ""}>
      <CardContent className="flex items-center gap-4 pt-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted">
          {isForbidden ? <Lock className="h-4 w-4 text-muted-foreground" /> : <Icon className="h-4 w-4 text-primary" />}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="mt-1 h-6 w-16" />
          ) : isForbidden ? (
            <p className="text-sm text-muted-foreground">No access</p>
          ) : (
            <p className="font-display text-xl font-semibold">{value}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return href && !isForbidden ? <Link to={href}>{content}</Link> : content;
}

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const datasets = useDatasets();
  const models = useModels();
  const evaluations = useEvaluationRuns();
  const status = useSystemStatus();

  const isForbidden = (error: unknown) => error instanceof ApiError && error.status === 403;

  const deployedModels = models.data?.filter((m) => m.deployment_status === "deployed").length ?? 0;
  const latestRun = evaluations.data?.[0];

  const accuracyTrend = (evaluations.data ?? [])
    .slice(0, 10)
    .reverse()
    .map((run, i) => ({ run: `#${i + 1}`, accuracy: Math.round(run.accuracy * 100) }));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Welcome back{user?.username ? `, ${user.username}` : ""}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Datasets, models, evaluations and service health at a glance.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          icon={Database}
          label="Datasets"
          value={datasets.data?.length ?? 0}
          isLoading={datasets.isLoading}
          isForbidden={isForbidden(datasets.error)}
          href="/datasets"
        />
        <KpiCard
          icon={Boxes}
          label="Registered Models"
          value={models.data?.length ?? 0}
          isLoading={models.isLoading}
          isForbidden={isForbidden(models.error)}
          href="/models"
        />
        <KpiCard
          icon={Activity}
          label="Deployed Models"
          value={deployedModels}
          isLoading={models.isLoading}
          isForbidden={isForbidden(models.error)}
          href="/models"
        />
        <KpiCard
          icon={ClipboardList}
          label="Evaluation Runs"
          value={evaluations.data?.length ?? 0}
          isLoading={evaluations.isLoading}
          isForbidden={isForbidden(evaluations.error)}
          href="/evaluations"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Accuracy trend</CardTitle>
            <CardDescription>Most recent evaluation runs, oldest to newest.</CardDescription>
          </CardHeader>
          <CardContent className="h-52">
            {evaluations.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : accuracyTrend.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No evaluation runs yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={accuracyTrend}>
                  <XAxis dataKey="run" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                  <Line type="monotone" dataKey="accuracy" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-4 w-4" /> System health
            </CardTitle>
            <CardDescription>Live from /api/v1/status.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {status.isLoading ? (
              <Skeleton className="h-32 w-full" />
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
          </CardContent>
        </Card>
      </div>

      {latestRun && (
        <Card>
          <CardHeader>
            <CardTitle>Latest evaluation</CardTitle>
          </CardHeader>
          <CardContent>
            <Link to={`/evaluations/${latestRun.run_id}`} className="flex items-center justify-between hover:underline">
              <span className="text-sm">
                {latestRun.task} · {latestRun.model_name} · {latestRun.num_samples} samples
              </span>
              <Badge>{(latestRun.accuracy * 100).toFixed(1)}% accuracy</Badge>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
