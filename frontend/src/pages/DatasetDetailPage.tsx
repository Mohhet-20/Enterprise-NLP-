import { useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  Archive,
  ArchiveRestore,
  AlertTriangle,
  CheckCircle2,
  GitBranch,
  Upload as UploadIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import {
  useArchiveDataset,
  useCreateDatasetVersion,
  useDataset,
  useDatasetPreview,
  useDatasetProfile,
  useDatasetValidationReport,
  useDatasetVersionHistory,
  useRestoreDataset,
  useUploadDatasetCsv,
} from "@/hooks/useDatasets";
import { useAuthStore } from "@/stores/useAuthStore";
import { hasPermission } from "@/lib/permissions";

const ISSUE_LABELS: Record<string, string> = {
  encoding_errors: "Encoding errors",
  duplicates: "Duplicates",
  empty_documents: "Empty documents",
  very_short_text: "Very short text",
  very_long_text: "Very long text",
  missing_labels: "Missing labels",
  invalid_labels: "Invalid labels",
  class_imbalance: "Class imbalance",
};

export function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const role = useAuthStore((s) => s.user?.role);
  const canWrite = hasPermission(role, "dataset:write");

  const { data: dataset, isLoading } = useDataset(id);
  const { data: preview } = useDatasetPreview(id);
  const { data: validationReport } = useDatasetValidationReport(id);
  const { data: profile } = useDatasetProfile(id);
  const { data: versions } = useDatasetVersionHistory(id);

  const upload = useUploadDatasetCsv();
  const archive = useArchiveDataset();
  const restore = useRestoreDataset();
  const createVersion = useCreateDatasetVersion();
  const [applyCleaning, setApplyCleaning] = useState(true);

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !id) return;
    try {
      const result = await upload.mutateAsync({ datasetId: id, file, applyCleaning });
      toast.success(
        `Uploaded ${result.dataset.row_count} rows — ${result.validation_report.is_valid ? "validated" : "has blocking issues"}`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-4 h-48 w-full" />
      </div>
    );
  }

  if (!dataset) {
    return <div className="p-8 text-center text-sm text-muted-foreground">Dataset not found.</div>;
  }

  const labelChartData = profile
    ? Object.entries(profile.label_distribution).map(([label, count]) => ({ label, count }))
    : [];
  const wordChartData = profile ? profile.top_words.slice(0, 10).map(([word, count]) => ({ word, count })) : [];

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-semibold tracking-tight">{dataset.name}</h1>
            <Badge variant="outline">v{dataset.version}</Badge>
            {dataset.is_archived && <Badge variant="secondary">Archived</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {dataset.description || "No description"} · {dataset.row_count.toLocaleString()} rows · task:{" "}
            <span className="font-mono">{dataset.task}</span>
          </p>
        </div>
        {canWrite && (
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <input
                type="checkbox"
                className="h-3.5 w-3.5 rounded border-input accent-primary"
                checked={applyCleaning}
                onChange={(e) => setApplyCleaning(e.target.checked)}
              />
              Clean text on upload
            </label>
            <input ref={fileInputRef} type="file" accept=".csv" hidden onChange={handleFileSelected} />
            <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={upload.isPending}>
              <UploadIcon className="h-3.5 w-3.5" /> {upload.isPending ? "Uploading…" : "Upload CSV"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => createVersion.mutateAsync(id!).then((v) => navigate(`/datasets/${v.id}`))}
            >
              <GitBranch className="h-3.5 w-3.5" /> New version
            </Button>
            {dataset.is_archived ? (
              <Button variant="outline" size="sm" onClick={() => restore.mutate(id!)}>
                <ArchiveRestore className="h-3.5 w-3.5" /> Restore
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={() => archive.mutate(id!)}>
                <Archive className="h-3.5 w-3.5" /> Archive
              </Button>
            )}
          </div>
        )}
      </div>

      <Tabs defaultValue="preview">
        <TabsList>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
        </TabsList>

        <TabsContent value="preview">
          <Card>
            <CardContent className="p-0">
              {!preview || preview.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No records yet — upload a CSV to add some.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Text</TableHead>
                      <TableHead>Label</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell className="max-w-lg truncate">{record.text}</TableCell>
                        <TableCell>
                          {record.label ? <Badge variant="outline">{record.label}</Badge> : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="validation">
          {!validationReport ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {validationReport.is_valid ? (
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                  )}
                  {validationReport.is_valid ? "No blocking issues" : "Blocking issues found"}
                </CardTitle>
                <CardDescription>
                  {validationReport.total_records} records checked — duplicates, empty/short/long text, and
                  class imbalance are warnings; encoding errors and empty documents block validation.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {validationReport.issues.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No issues detected.</p>
                ) : (
                  validationReport.issues.map((issue) => (
                    <div key={issue.kind} className="flex items-start gap-2 rounded-md border border-border p-3 text-sm">
                      <Badge variant="outline">{ISSUE_LABELS[issue.kind] ?? issue.kind}</Badge>
                      <span className="text-muted-foreground">{issue.message}</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="profile">
          {!profile ? (
            <Card>
              <CardContent className="p-8 text-center text-sm text-muted-foreground">
                No profile available yet — upload records first.
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Sequence length</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-muted-foreground">Min words</p>
                    <p className="font-display text-lg font-semibold">{profile.sequence_length.min_words}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Max words</p>
                    <p className="font-display text-lg font-semibold">{profile.sequence_length.max_words}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Mean words</p>
                    <p className="font-display text-lg font-semibold">{profile.sequence_length.mean_words}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Vocabulary size</p>
                    <p className="font-display text-lg font-semibold">{profile.vocabulary_size.toLocaleString()}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Label distribution</CardTitle>
                </CardHeader>
                <CardContent className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={labelChartData}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                      <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }}
                      />
                      <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Top words</CardTitle>
                  <CardDescription>Common stopwords excluded.</CardDescription>
                </CardHeader>
                <CardContent className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={wordChartData} layout="vertical" margin={{ left: 8 }}>
                      <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                      <YAxis
                        type="category"
                        dataKey="word"
                        width={90}
                        tick={{ fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
                        stroke="hsl(var(--muted-foreground))"
                      />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", fontSize: 12 }}
                      />
                      <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} barSize={14} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="versions">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Version</TableHead>
                    <TableHead>Rows</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(versions ?? []).map((v) => (
                    <TableRow key={v.id} className={v.id === id ? "bg-secondary/50" : ""}>
                      <TableCell>
                        <a href={`/datasets/${v.id}`} className="hover:underline">
                          v{v.version} {v.id === id && <span className="text-muted-foreground">(current)</span>}
                        </a>
                      </TableCell>
                      <TableCell>{v.row_count.toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{v.status}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(v.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
