import { cn } from "@/lib/utils";

interface ConfidenceChipProps {
  label: string;
  score: number;
  emphasis?: boolean;
}

export function ConfidenceChip({ label, score, emphasis }: ConfidenceChipProps) {
  const pct = Math.round(score * 100);
  return (
    <span
      className={cn("confidence-chip", emphasis && "border-primary/40")}
      style={{ "--fill": `${pct}%` } as React.CSSProperties}
    >
      <span className={cn(emphasis ? "font-semibold text-foreground" : "text-foreground/80")}>{label}</span>
      <span className="text-muted-foreground">{pct}%</span>
    </span>
  );
}
