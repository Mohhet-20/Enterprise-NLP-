import { motion } from "framer-motion";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Clock, Cpu, Hash } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceChip } from "@/components/playground/ConfidenceChip";
import type { InferenceResponse } from "@/types/api";
import { ApiError } from "@/lib/api";

interface ResultPanelProps {
  response?: InferenceResponse;
  error?: unknown;
  isPending: boolean;
}

export function ResultPanel({ response, error, isPending }: ResultPanelProps) {
  if (isPending) {
    return (
      <Card>
        <CardContent className="flex h-48 items-center justify-center text-sm text-muted-foreground">
          Running inference…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    const isApiError = error instanceof ApiError;
    return (
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">
            {isApiError ? error.code : "Prediction failed"}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <p>{isApiError ? error.message : "Something went wrong reaching the API."}</p>
          {isApiError && error.code === "ModelLoadError" && (
            <p className="text-muted-foreground">
              The server couldn't load this model. Check that the ML extras are installed
              (requirements-ml.txt) and the model cache is reachable.
            </p>
          )}
          {isApiError && error.requestId && (
            <p className="font-mono text-xs text-muted-foreground">request_id: {error.requestId}</p>
          )}
        </CardContent>
      </Card>
    );
  }

  if (!response) {
    return (
      <Card>
        <CardContent className="flex h-48 flex-col items-center justify-center gap-1 text-center text-sm text-muted-foreground">
          <p>No prediction yet.</p>
          <p>Type some text and run it to see results here.</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = Object.entries(response.results[0]?.raw_scores ?? {}).map(([label, score]) => ({
    label,
    score: Math.round(score * 1000) / 10,
  }));
  const top = response.results[0];
  const isSimilarity = response.task === "semantic_similarity";
  const isMultiLabel = response.results.length > 1;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {isSimilarity && top ? (
            <div className="flex flex-col gap-2">
              <span className="font-display text-3xl font-semibold tabular-nums">{top.score.toFixed(3)}</span>
              <span className="text-xs text-muted-foreground">
                Cosine similarity of the two sentence embeddings (1 = same meaning, ~0 = unrelated).
              </span>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              {response.results.map((r, i) => (
                <ConfidenceChip key={r.label} label={r.label} score={r.score} emphasis={i === 0} />
              ))}
              {isMultiLabel && (
                <span className="text-xs text-muted-foreground">multi-label: every label above 50%</span>
              )}
            </div>
          )}

          {!isSimilarity && chartData.length > 1 && (
            <div className="h-40 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" stroke="hsl(var(--muted-foreground))" />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={110}
                    tick={{ fontSize: 11, fontFamily: "IBM Plex Mono, monospace" }}
                    stroke="hsl(var(--muted-foreground))"
                  />
                  <Tooltip
                    cursor={{ fill: "hsl(var(--muted))" }}
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "var(--radius)",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="score" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} barSize={16} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-4 border-t border-border pt-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5" /> {response.model_name}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" /> {response.latency_ms}ms
            </span>
            <span className="flex items-center gap-1.5">
              <Hash className="h-3.5 w-3.5" /> {response.task}
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
