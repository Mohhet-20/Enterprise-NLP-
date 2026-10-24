import { useState } from "react";
import { Layers } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfidenceChip } from "@/components/playground/ConfidenceChip";
import { useBatchInference } from "@/hooks/useInference";
import { ApiError } from "@/lib/api";
import type { NLPTask } from "@/types/api";

const MAX_TEXTS = 64;

interface BatchPanelProps {
  task: NLPTask;
  candidateLabels?: string[];
}

export function parseBatchInput(raw: string): string[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function BatchPanel({ task, candidateLabels }: BatchPanelProps) {
  const [raw, setRaw] = useState("");
  const batch = useBatchInference();
  const texts = parseBatchInput(raw);

  async function handleRun() {
    try {
      await batch.mutateAsync({ task, texts, candidate_labels: candidateLabels });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Batch prediction failed");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium">Texts — one per line</label>
        <Textarea
          rows={7}
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder={"Loved every minute of it.\nThe ending made no sense.\nIt was fine, I guess."}
        />
        <span className={`self-end text-xs ${texts.length > MAX_TEXTS ? "text-destructive" : "text-muted-foreground"}`}>
          {texts.length} / {MAX_TEXTS} texts
        </span>
      </div>
      <Button
        className="self-start"
        onClick={handleRun}
        disabled={texts.length === 0 || texts.length > MAX_TEXTS || batch.isPending}
      >
        <Layers className="h-4 w-4" />
        {batch.isPending ? "Running…" : `Run ${texts.length || ""} predictions`}
      </Button>

      {batch.data && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            {batch.data.items.length} texts in {batch.data.latency_ms}ms ·{" "}
            {batch.data.throughput_texts_per_second} texts/s · {batch.data.model_name}
          </p>
          <div className="max-h-80 overflow-auto rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Text</TableHead>
                  <TableHead className="w-48">Prediction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batch.data.items.map((item, i) => (
                  <TableRow key={i}>
                    <TableCell className="max-w-md truncate text-sm">{item.text}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {item.results.map((r) => (
                          <ConfidenceChip key={r.label} label={r.label} score={r.score} />
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
