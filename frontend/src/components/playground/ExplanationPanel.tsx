import { Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExplainResponse } from "@/types/api";

interface ExplanationPanelProps {
  explanation: ExplainResponse;
}

/** Scale attributions to [-1, 1] by the largest magnitude so the strongest
 * word is always fully saturated, whichever direction it pushes. */
export function normaliseAttributions(values: number[]): number[] {
  const max = Math.max(...values.map((v) => Math.abs(v)), 1e-9);
  return values.map((v) => v / max);
}

export function ExplanationPanel({ explanation }: ExplanationPanelProps) {
  const weights = normaliseAttributions(explanation.attributions.map((a) => a.importance));
  const ranked = explanation.attributions
    .map((a, i) => ({ ...a, weight: weights[i] }))
    .sort((a, b) => Math.abs(b.importance) - Math.abs(a.importance))
    .slice(0, 5);
  const gap = explanation.target_score - explanation.baseline_score;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Why “{explanation.label}”?</CardTitle>
        <CardDescription>
          Integrated Gradients: each word's contribution to the model's {explanation.label} score.
          Green pushes toward it, red pushes away.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-base leading-9" data-testid="attribution-text">
          {explanation.attributions.map((a, i) => {
            const w = weights[i];
            const hue = w >= 0 ? "var(--attr-positive)" : "var(--attr-negative)";
            return (
              <span key={i}>
                <span
                  title={`${a.importance >= 0 ? "+" : ""}${a.importance.toFixed(4)}`}
                  className="rounded px-1 py-0.5"
                  style={{ background: `hsl(${hue} / ${(Math.abs(w) * 0.6).toFixed(3)})` }}
                >
                  {a.token}
                </span>{" "}
              </span>
            );
          })}
        </p>

        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Most influential words</span>
          {ranked.map((a) => (
            <div key={a.token + a.importance} className="flex items-center gap-3 text-sm">
              <span className="w-28 truncate font-mono text-xs">{a.token}</span>
              <div className="relative h-2 flex-1 rounded bg-muted">
                <div
                  className="absolute top-0 h-2 rounded"
                  style={{
                    width: `${Math.abs(a.weight) * 50}%`,
                    left: a.weight >= 0 ? "50%" : `${50 - Math.abs(a.weight) * 50}%`,
                    background: `hsl(${a.weight >= 0 ? "var(--attr-positive)" : "var(--attr-negative)"})`,
                  }}
                />
              </div>
              <span className="w-16 text-right font-mono text-xs tabular-nums">
                {a.importance >= 0 ? "+" : ""}
                {a.importance.toFixed(3)}
              </span>
            </div>
          ))}
        </div>

        <div className="flex items-start gap-2 rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Score moved {explanation.baseline_score.toFixed(3)} → {explanation.target_score.toFixed(3)} (Δ{" "}
            {gap.toFixed(3)}) from an all-[PAD] baseline. Attributions sum to that Δ within{" "}
            {Math.abs(explanation.convergence_delta).toFixed(4)} (completeness check) · {explanation.latency_ms}ms
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
