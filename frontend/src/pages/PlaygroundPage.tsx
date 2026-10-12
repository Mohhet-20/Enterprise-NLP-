import { useState } from "react";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { TaskSelector } from "@/components/playground/TaskSelector";
import { ResultPanel } from "@/components/playground/ResultPanel";
import { PredictionHistory } from "@/components/playground/PredictionHistory";
import { useInference } from "@/hooks/useInference";
import { usePredictionHistoryStore } from "@/stores/usePredictionHistoryStore";
import type { NLPTask } from "@/types/api";

export function PlaygroundPage() {
  const [text, setText] = useState("");
  const [task, setTask] = useState<NLPTask>("sentiment_analysis");
  const inference = useInference();
  const addEntry = usePredictionHistoryStore((s) => s.addEntry);

  async function handleRun() {
    if (!text.trim()) return;
    try {
      const response = await inference.mutateAsync({ task, text: text.trim() });
      addEntry(text.trim(), response);
    } catch {
      toast.error("Prediction failed — see details below.");
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Inference Playground</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Run live predictions against models registered in the backend's plugin registry.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Single text prediction</CardTitle>
              <CardDescription>Pick a task, enter text, and run it against the live backend.</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="single">
                <TabsList>
                  <TabsTrigger value="single">Single Text</TabsTrigger>
                  <TabsTrigger value="batch" disabled>
                    Batch <Badge variant="outline" className="ml-1.5 px-1 py-0 text-[10px]">soon</Badge>
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="single" className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium">Task</label>
                    <TaskSelector value={task} onChange={setTask} />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium">Text</label>
                    <Textarea
                      placeholder="Paste or type the text you want analyzed…"
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      rows={6}
                    />
                    <span className="self-end text-xs text-muted-foreground">{text.length.toLocaleString()} characters</span>
                  </div>

                  <Button onClick={handleRun} disabled={!text.trim() || inference.isPending} className="self-start">
                    <Sparkles className="h-4 w-4" />
                    {inference.isPending ? "Running…" : "Run prediction"}
                  </Button>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <ResultPanel
            response={inference.data}
            error={inference.error}
            isPending={inference.isPending}
          />
        </div>

        <Card className="h-fit lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle>History</CardTitle>
            <CardDescription>This session only — not yet persisted server-side.</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[32rem] overflow-y-auto">
            <PredictionHistory />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
