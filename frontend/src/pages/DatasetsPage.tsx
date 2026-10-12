import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Database, Lock, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TaskSelector } from "@/components/playground/TaskSelector";
import { useCreateDataset, useDatasets } from "@/hooks/useDatasets";
import { useAuthStore } from "@/stores/useAuthStore";
import { hasPermission } from "@/lib/permissions";
import { ApiError } from "@/lib/api";
import type { DatasetStatus, NLPTask } from "@/types/api";

const STATUS_VARIANT: Record<DatasetStatus, "default" | "secondary" | "outline"> = {
  validated: "default",
  draft: "secondary",
  archived: "outline",
};

function CreateDatasetDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [task, setTask] = useState<NLPTask>("sentiment_analysis");
  const [description, setDescription] = useState("");
  const [labelSetText, setLabelSetText] = useState("POSITIVE, NEGATIVE");
  const createDataset = useCreateDataset();

  async function handleCreate() {
    if (!name.trim()) return;
    try {
      const label_set = labelSetText
        .split(",")
        .map((l) => l.trim())
        .filter(Boolean);
      await createDataset.mutateAsync({ name: name.trim(), task, description: description.trim() || undefined, label_set });
      toast.success(`Dataset "${name.trim()}" created`);
      setOpen(false);
      setName("");
      setDescription("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create dataset");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> New Dataset
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create dataset</DialogTitle>
          <DialogDescription>
            Creates an empty dataset shell — upload a CSV afterward to add records.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ds-name">Name</Label>
            <Input id="ds-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="customer-reviews" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Task</Label>
            <TaskSelector value={task} onChange={setTask} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ds-labels">Label set (comma-separated)</Label>
            <Input id="ds-labels" value={labelSetText} onChange={(e) => setLabelSetText(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ds-desc">Description (optional)</Label>
            <Textarea id="ds-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </div>
          <Button onClick={handleCreate} disabled={!name.trim() || createDataset.isPending} className="self-start">
            {createDataset.isPending ? "Creating…" : "Create dataset"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function DatasetsPage() {
  const [query, setQuery] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const role = useAuthStore((s) => s.user?.role);
  const canWrite = hasPermission(role, "dataset:write");
  const canRead = hasPermission(role, "dataset:read");

  const { data: datasets, isLoading, error } = useDatasets({ query: query || undefined, includeArchived });

  if (!canRead) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md text-center">
          <CardContent className="flex flex-col items-center gap-3 pt-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Lock className="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 className="font-display text-lg font-semibold">No dataset access</h2>
            <p className="text-sm text-muted-foreground">
              Your role ({role?.replace(/_/g, " ")}) doesn't include dataset access. Ask an admin to grant
              the ML Engineer, NLP Engineer, or Data Scientist role to view and manage datasets.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">Datasets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload, validate, and version datasets for training and evaluation.
          </p>
        </div>
        {canWrite && <CreateDatasetDialog />}
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search datasets…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button
          variant={includeArchived ? "secondary" : "outline"}
          size="sm"
          onClick={() => setIncludeArchived((v) => !v)}
        >
          {includeArchived ? "Showing archived" : "Show archived"}
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col gap-3 p-5">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {error instanceof ApiError ? error.message : "Failed to load datasets."}
            </div>
          ) : !datasets || datasets.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-12 text-center text-sm text-muted-foreground">
              <Database className="h-6 w-6" />
              <p>No datasets yet.</p>
              {canWrite && <p>Create one to get started.</p>}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Task</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Rows</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {datasets.map((ds) => (
                  <TableRow key={ds.id} className="cursor-pointer">
                    <TableCell className="font-medium">
                      <Link to={`/datasets/${ds.id}`} className="hover:underline">
                        {ds.name}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{ds.task}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[ds.status]}>{ds.status}</Badge>
                    </TableCell>
                    <TableCell>{ds.row_count.toLocaleString()}</TableCell>
                    <TableCell>v{ds.version}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {ds.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-[10px]">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(ds.updated_at).toLocaleDateString()}
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
