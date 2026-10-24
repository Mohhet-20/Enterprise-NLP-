import { useState } from "react";
import { Microscope, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TaskSelector } from "@/components/playground/TaskSelector";
import { ResultPanel } from "@/components/playground/ResultPanel";
import { PredictionHistory } from "@/components/playground/PredictionHistory";
import { ExplanationPanel } from "@/components/playground/ExplanationPanel";
import { BatchPanel } from "@/components/playground/BatchPanel";
import { useExplain, useInference } from "@/hooks/useInference";
import { useTasks } from "@/hooks/useTasks";
import { usePredictionHistoryStore } from "@/stores/usePredictionHistoryStore";
import { ApiError } from "@/lib/api";
import type { NLPTask } from "@/types/api";

const EXAMPLES: Partial<Record<NLPTask, string>> = {
  sentiment_analysis: "I didn't expect much, but the second half was genuinely brilliant.",
  emotion_detection: "I can't believe they cancelled the show after that cliffhanger.",
  toxicity_detection: "Nobody asked for your opinion, you clown.",
  topic_classification: "The striker's late goal sent the club into the cup final.",
  language_detection: "Je voudrais réserver une table pour deux personnes ce soir.",
  zero_shot_classification: "My card was charged twice for the same order.",
  semantic_similarity: "The battery easily lasts a full day.",
};

export function parseLabels(raw: string): string[] {
  return raw
    .split(",")
    .map((l) => l.trim())
    .filter(Boolean);
}

export function PlaygroundPage() {
  const [text, setText] = useState("");
  const [textPair, setTextPair] = useState("");
  const [labelsRaw, setLabelsRaw] = useState("billing, shipping, technical issue, account access");
  const [task, setTask] = useState<NLPTask>("sentiment_analysis");
  const inference = useInference();
  const explain = useExplain();
  const { data: taskData } = useTasks();
  const addEntry = usePredictionHistoryStore((s) => s.addEntry);

  const taskInfo = taskData?.tasks.find((t) => t.task === task);
  const isZeroShot = task === "zero_shot_classification";
  const isSimilarity = task === "semantic_similarity";
  const labels = parseLabels(labelsRaw);
  const canRun =
    !!text.trim() && (!isZeroShot || labels.length >= 2) && (!isSimilarity || !!textPair.trim());

  function handleTaskChange(next: NLPTask) {
    setTask(next);
    inference.reset();
    explain.reset();
  }

  async function handleRun() {
    if (!canRun) return;
    explain.reset();
    try {
      const response = await inference.mutateAsync({
        task,
        text: text.trim(),
        candidate_labels: isZeroShot ? labels : undefined,
        text_pair: isSimilarity ? textPair.trim() : undefined,
      });
      addEntry(text.trim(), response);
    } catch {
      toast.error("Prediction failed — see details below.");
    }
  }

  async function handleExplain() {
    try {
      await explain.mutateAsync({ task, text: text.trim(), target_label: inference.data?.results[0]?.label });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Explanation failed");
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Inference Playground</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Run live predictions against the transformer models the backend serves, and see why the model decided.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Predict</CardTitle>
              <CardDescription>
                {taskInfo ? (
                  <>
                    {taskInfo.description} <span className="font-mono text-xs">{taskInfo.default_model}</span>
                  </>
                ) : (
                  "Pick a task, enter text, and run it against the live backend."
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Task</label>
                <TaskSelector value={task} onChange={handleTaskChange} />
              </div>

              {isZeroShot && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium" htmlFor="labels">
                    Candidate labels — comma separated
                  </label>
                  <Input id="labels" value={labelsRaw} onChange={(e) => setLabelsRaw(e.target.value)} />
                </div>
              )}

              <Tabs defaultValue="single">
                <TabsList>
                  <TabsTrigger value="single">Single Text</TabsTrigger>
                  <TabsTrigger value="batch" disabled={isSimilarity}>
                    Batch
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="single" className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">{isSimilarity ? "Text A" : "Text"}</label>
                      {EXAMPLES[task] && (
                        <button
                          type="button"
                          className="text-xs text-primary hover:underline"
                          onClick={() => {
                            setText(EXAMPLES[task]!);
                            if (isSimilarity) setTextPair("You won't need to charge it until bedtime.");
                          }}
                        >
                          Try an example
                        </button>
                      )}
                    </div>
                    <Textarea
                      placeholder="Paste or type the text you want analyzed…"
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      rows={isSimilarity ? 3 : 6}
                    />
                  </div>

                  {isSimilarity && (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-sm font-medium">Text B</label>
                      <Textarea value={textPair} onChange={(e) => setTextPair(e.target.value)} rows={3} />
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2">
                    <Button onClick={handleRun} disabled={!canRun || inference.isPending}>
                      <Sparkles className="h-4 w-4" />
                      {inference.isPending ? "Running…" : "Run prediction"}
                    </Button>
                    {taskInfo?.explainable && inference.data && (
                      <Button variant="outline" onClick={handleExplain} disabled={explain.isPending}>
                        <Microscope className="h-4 w-4" />
                        {explain.isPending ? "Attributing…" : "Explain this prediction"}
                      </Button>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="batch">
                  <BatchPanel task={task} candidateLabels={isZeroShot ? labels : undefined} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <ResultPanel response={inference.data} error={inference.error} isPending={inference.isPending} />
          {explain.data && <ExplanationPanel explanation={explain.data} />}
        </div>

        <Card className="h-fit lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle>History</CardTitle>
            <CardDescription>Predictions from this browser session.</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[32rem] overflow-y-auto">
            <PredictionHistory />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
