import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ClipboardList, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TaskSelector } from "@/components/playground/TaskSelector";
import { useEvaluationRuns, useRunEvaluation } from "@/hooks/useEvaluations";
import { useAuthStore } from "@/stores/useAuthStore";
import { hasPermission } from "@/lib/permissions";
import { ApiError } from "@/lib/api";
import type { NLPTask } from "@/types/api";

export function EvaluationsPage() {
  const [task, setTask] = useState<NLPTask>("sentiment_analysis");
  const role = useAuthStore((s) => s.user?.role);
  const canRun = hasPermission(role, "experiment:write");

  const { data: runs, isLoading } = useEvaluationRuns();
  const runEvaluation = useRunEvaluation();

  async function handleRun() {
    try {
      const result = await runEvaluation.mutateAsync(task);
      toast.success(`Evaluation complete — ${(result.accuracy * 100).toFixed(1)}% accuracy on ${result.num_samples} samples`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Evaluation failed");
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Evaluation & Error Analysis</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Real metrics (scikit-learn) and error analysis against the platform's registered baselines.
        </p>
      </div>

      {canRun && (
        <Card>
          <CardContent className="flex items-end gap-3 pt-5">
            <div className="w-64">
              <TaskSelector value={task} onChange={setTask} />
            </div>
            <Button onClick={handleRun} disabled={runEvaluation.isPending}>
              <Play className="h-4 w-4" /> {runEvaluation.isPending ? "Running…" : "Run evaluation"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col gap-3 p-5">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !runs || runs.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-12 text-center text-sm text-muted-foreground">
              <ClipboardList className="h-6 w-6" />
              <p>No evaluation runs yet.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Accuracy</TableHead>
                  <TableHead>Samples</TableHead>
                  <TableHead>Run at</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell>
                      <Link to={`/evaluations/${run.run_id}`} className="font-medium hover:underline">
                        {run.task}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{run.model_name}</TableCell>
                    <TableCell>
                      <Badge variant={run.accuracy >= 0.8 ? "default" : run.accuracy >= 0.6 ? "secondary" : "destructive"}>
                        {(run.accuracy * 100).toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell>{run.num_samples}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(run.created_at).toLocaleString()}
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
