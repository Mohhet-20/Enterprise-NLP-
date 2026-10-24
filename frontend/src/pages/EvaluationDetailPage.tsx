import { Fragment } from "react";
import { useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { ConfidenceChip } from "@/components/playground/ConfidenceChip";
import { TASK_LABELS } from "@/components/playground/TaskSelector";
import {
  useDownloadEvaluationReport,
  useDownloadMisclassifiedCsv,
  useEvaluationRun,
} from "@/hooks/useEvaluations";

export function EvaluationDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading } = useEvaluationRun(runId);
  const downloadReport = useDownloadEvaluationReport();
  const downloadCsv = useDownloadMisclassifiedCsv();

  if (isLoading || !run) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-4 h-64 w-full" />
      </div>
    );
  }

  const maxCellValue = Math.max(...run.confusion_matrix.flat());
  const calibrationData = run.calibration_bins.map((bin) => ({
    bucket: `${(bin.bucket_low * 100).toFixed(0)}-${(bin.bucket_high * 100).toFixed(0)}%`,
    confidence: Math.round(bin.avg_confidence * 100),
    accuracy: Math.round(bin.accuracy * 100),
  }));

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">{TASK_LABELS[run.task] ?? run.task}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {run.model_name} · {run.eval_set} · {run.num_samples} samples · {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => downloadReport.mutate(run.run_id)} disabled={downloadReport.isPending}>
            <FileText className="h-3.5 w-3.5" /> Report
          </Button>
          <Button variant="outline" size="sm" onClick={() => downloadCsv.mutate(run.run_id)} disabled={downloadCsv.isPending}>
            <Download className="h-3.5 w-3.5" /> Misclassified CSV
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Accuracy</p>
            <p className="font-display text-2xl font-semibold">{(run.accuracy * 100).toFixed(1)}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Macro F1</p>
            <p className="font-display text-2xl font-semibold">{run.macro_f1.toFixed(3)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Weighted F1</p>
            <p className="font-display text-2xl font-semibold">{run.weighted_f1.toFixed(3)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">ROC-AUC</p>
            <p className="font-display text-2xl font-semibold">{run.roc_auc != null ? run.roc_auc.toFixed(3) : "n/a"}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Confusion matrix</CardTitle>
            <CardDescription>Rows: actual · Columns: predicted</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className="grid gap-1"
              style={{ gridTemplateColumns: `auto repeat(${run.labels.length}, 1fr)` }}
            >
              <div />
              {run.labels.map((label) => (
                <div key={label} className="truncate px-1 text-center text-[10px] font-medium text-muted-foreground">
                  {label}
                </div>
              ))}
              {run.confusion_matrix.map((row, i) => (
                <Fragment key={run.labels[i]}>
                  <div className="flex items-center truncate pr-2 text-[10px] font-medium text-muted-foreground">
                    {run.labels[i]}
                  </div>
                  {row.map((value, j) => (
                    <div
                      key={`${i}-${j}`}
                      className="flex aspect-square items-center justify-center rounded-sm font-mono text-xs font-semibold"
                      style={{
                        backgroundColor: `hsl(var(--primary) / ${maxCellValue ? (0.1 + 0.7 * (value / maxCellValue)) : 0.1})`,
                        color: value / maxCellValue > 0.5 ? "hsl(var(--primary-foreground))" : "hsl(var(--foreground))",
                      }}
                    >
                      {value}
                    </div>
                  ))}
                </Fragment>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Calibration</CardTitle>
            <CardDescription>
              Confidence vs. actual accuracy per bucket — should track closely.
              {run.ece != null && (
                <>
                  {" "}
                  ECE <span className="font-mono">{run.ece.toFixed(3)}</span> (mean gap, lower is better).
                </>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="h-48">
            {calibrationData.length === 0 ? (
              <p className="text-sm text-muted-foreground">Not enough samples to compute calibration bins.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={calibrationData}>
                  <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 11 }} unit="%" stroke="hsl(var(--muted-foreground))" />
                  <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }} />
                  <Bar dataKey="confidence" fill="hsl(var(--muted-foreground))" radius={[3, 3, 0, 0]} name="Avg confidence" />
                  <Bar dataKey="accuracy" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} name="Actual accuracy" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Per-class metrics</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Label</TableHead>
                  <TableHead>Precision</TableHead>
                  <TableHead>Recall</TableHead>
                  <TableHead>F1</TableHead>
                  <TableHead>Support</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.per_class.map((pc) => (
                  <TableRow key={pc.label}>
                    <TableCell className="font-medium">{pc.label}</TableCell>
                    <TableCell>{pc.precision.toFixed(3)}</TableCell>
                    <TableCell>{pc.recall.toFixed(3)}</TableCell>
                    <TableCell>{pc.f1.toFixed(3)}</TableCell>
                    <TableCell>{pc.support}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Error summary</CardTitle>
            <CardDescription>
              {run.error_summary.total_errors} total errors · {run.error_summary.confidence_error_count} confidence
              errors (wrong despite high confidence) · {run.error_summary.hard_example_count} hard examples
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {run.error_summary.length_slices.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {run.error_summary.length_slices.map((slice) => (
                  <Badge key={slice.name} variant="outline">
                    {slice.name}: {(slice.accuracy * 100).toFixed(0)}% acc ({slice.count} samples)
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Misclassified samples</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {run.misclassified_samples.slice(0, 10).map((sample, i) => (
              <div key={i} className="rounded-md border border-border p-3 text-sm">
                <p className="mb-2 line-clamp-2">{sample.text}</p>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground">true: {sample.true_label}</span>
                  <ConfidenceChip label={sample.predicted_label} score={sample.confidence} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
