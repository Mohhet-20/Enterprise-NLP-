import { History, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfidenceChip } from "@/components/playground/ConfidenceChip";
import { usePredictionHistoryStore } from "@/stores/usePredictionHistoryStore";

export function PredictionHistory() {
  const entries = usePredictionHistoryStore((s) => s.entries);
  const clear = usePredictionHistoryStore((s) => s.clear);

  if (entries.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center text-sm text-muted-foreground">
        <History className="h-5 w-5" />
        <p>Predictions you run will appear here for this session.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-1">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-medium text-muted-foreground">{entries.length} this session</span>
        <Button variant="ghost" size="sm" onClick={clear}>
          <Trash2 className="h-3.5 w-3.5" /> Clear
        </Button>
      </div>
      {entries.map((entry) => (
        <div key={entry.id} className="rounded-md border border-border p-3">
          <p className="mb-2 line-clamp-2 text-sm">{entry.text}</p>
          <div className="flex items-center justify-between">
            {entry.response.results[0] && (
              <ConfidenceChip label={entry.response.results[0].label} score={entry.response.results[0].score} />
            )}
            <span className="text-xs text-muted-foreground">
              {new Date(entry.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
