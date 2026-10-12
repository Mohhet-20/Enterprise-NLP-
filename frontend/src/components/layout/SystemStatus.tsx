import { cn } from "@/lib/utils";
import { useHealth } from "@/hooks/useHealth";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function SystemStatus() {
  const { data, isError, isLoading } = useHealth();

  const state = isLoading ? "checking" : isError ? "down" : data?.status === "ok" ? "up" : "down";

  const label =
    state === "checking"
      ? "Checking API status…"
      : state === "up"
        ? `API healthy · ${data?.environment}`
        : "API unreachable";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              state === "up" && "bg-primary",
              state === "down" && "bg-destructive",
              state === "checking" && "animate-pulse bg-muted-foreground"
            )}
          />
          <span className="hidden sm:inline">{state === "up" ? "Operational" : state === "down" ? "Offline" : "Checking"}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom">{label}</TooltipContent>
    </Tooltip>
  );
}
