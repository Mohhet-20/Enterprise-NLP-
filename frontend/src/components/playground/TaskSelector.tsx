import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTasks } from "@/hooks/useTasks";
import type { NLPTask } from "@/types/api";

interface TaskSelectorProps {
  value: NLPTask;
  onChange: (task: NLPTask) => void;
}

export const TASK_LABELS: Record<NLPTask, string> = {
  sentiment_analysis: "Sentiment Analysis",
  emotion_detection: "Emotion Detection",
  topic_classification: "Topic Classification",
  toxicity_detection: "Toxicity Detection",
  language_detection: "Language Detection",
  zero_shot_classification: "Zero-shot Classification",
  semantic_similarity: "Semantic Similarity",
  text_embeddings: "Text Embeddings",
};

export function TaskSelector({ value, onChange }: TaskSelectorProps) {
  const { data, isLoading } = useTasks();
  // Raw vectors aren't meaningful to eyeball; /embed serves them to API clients.
  const registeredTasks = (data?.tasks ?? []).filter((t) => t.task !== "text_embeddings");

  return (
    <Select value={value} onValueChange={(v) => onChange(v as NLPTask)}>
      <SelectTrigger>
        <SelectValue placeholder={isLoading ? "Loading tasks…" : "Select a task"} />
      </SelectTrigger>
      <SelectContent>
        {registeredTasks.map((t) => (
          <SelectItem key={t.task} value={t.task}>
            {TASK_LABELS[t.task] ?? t.task}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
