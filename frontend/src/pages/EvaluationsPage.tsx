import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ClipboardList, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TASK_LABELS } from "@/components/playground/TaskSelector";
import { useEvaluationRuns, useRunEvaluation } from "@/hooks/useEvaluations";
import { useDatasets } from "@/hooks/useDatasets";
import { useAuthStore } from "@/stores/useAuthStore";
import { hasPermission } from "@/lib/permissions";
import { ApiError } from "@/lib/api";
import type { EvaluationModelKind, EvaluationRunRequest, NLPTask } from "@/types/api";

// Tasks with one gold label per text — the only ones accuracy is defined for.
const EVALUABLE_TASKS: NLPTask[] = [
  "sentiment_analysis",
  "emotion_detection",
  "language_detection",
  "zero_shot_classification",
];

const BUILTIN_SETS = {
  challenge_set: "Challenge set — 48 hard cases (negation, sarcasm)",
  sst2_validation: "SST-2 validation — 872 sentences",
} as const;

export function EvaluationsPage() {
  const [source, setSource] = useState<string>("challenge_set");
  const [model, setModel] = useState<EvaluationModelKind>("served");
  const role = useAuthStore((s) => s.user?.role);
  const canRun = hasPermission(role, "experiment:write");
  const canReadDatasets = hasPermission(role, "dataset:read");

  const { data: runs, isLoading } = useEvaluationRuns();
  const { data: datasets } = useDatasets();
  const runEvaluation = useRunEvaluation();

  const evaluableDatasets = canReadDatasets
    ? (datasets ?? []).filter((d) => d.row_count > 0 && EVALUABLE_TASKS.includes(d.task as NLPTask))
    : [];
  const selectedDataset = evaluableDatasets.find((d) => `dataset:${d.id}` === source);
  const task: NLPTask = selectedDataset ? (selectedDataset.task as NLPTask) : "sentiment_analysis";
  const baselineAllowed = task === "sentiment_analysis";

  async function handleRun() {
    const request: EvaluationRunRequest = selectedDataset
      ? { task, model: baselineAllowed ? model : "served", dataset_id: selectedDataset.id }
      : { task, model, eval_set: source as keyof typeof BUILTIN_SETS };
    try {
      const result = await runEvaluation.mutateAsync(request);
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
          Score the served transformer, or the lexicon baseline it has to beat, on a benchmark or your own labelled data.
        </p>
      </div>

      {canRun && (
        <Card>
          <CardContent className="flex flex-wrap items-end gap-3 pt-5">
            <div className="flex w-80 flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">Evaluation data</label>
              <Select value={source} onValueChange={setSource}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(BUILTIN_SETS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                  {evaluableDatasets.map((d) => (
                    <SelectItem key={d.id} value={`dataset:${d.id}`}>
                      {d.name} — {TASK_LABELS[d.task as NLPTask]}, {d.row_count} rows
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex w-56 flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">Model</label>
              <Select value={baselineAllowed ? model : "served"} onValueChange={(v) => setModel(v as EvaluationModelKind)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="served">Served transformer</SelectItem>
                  {baselineAllowed && <SelectItem value="lexicon_baseline">Lexicon baseline</SelectItem>}
                </SelectContent>
              </Select>
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
                  <TableHead>Data</TableHead>
                  <TableHead>Accuracy</TableHead>
                  <TableHead>Macro F1</TableHead>
                  <TableHead>Samples</TableHead>
                  <TableHead>Run at</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell>
                      <Link to={`/evaluations/${run.run_id}`} className="font-medium hover:underline">
                        {TASK_LABELS[run.task] ?? run.task}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{run.model_name}</TableCell>
                    <TableCell className="text-xs">{run.eval_set}</TableCell>
                    <TableCell>
                      <Badge variant={run.accuracy >= 0.8 ? "default" : run.accuracy >= 0.6 ? "secondary" : "destructive"}>
                        {(run.accuracy * 100).toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {run.macro_f1 != null ? run.macro_f1.toFixed(3) : "—"}
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
