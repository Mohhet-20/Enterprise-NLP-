import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTasks } from "@/hooks/useTasks";
import type { NLPTask } from "@/types/api";

interface TaskSelectorProps {
  value: NLPTask;
  onChange: (task: NLPTask) => void;
}

const TASK_LABELS: Record<string, string> = {
  sentiment_analysis: "Sentiment Analysis",
  emotion_detection: "Emotion Detection",
  topic_classification: "Topic Classification",
  toxicity_detection: "Toxicity Detection",
  hate_speech_detection: "Hate Speech Detection",
  fake_news_detection: "Fake News Detection",
  language_detection: "Language Detection",
  intent_classification: "Intent Classification",
  multi_label_classification: "Multi-label Classification",
  zero_shot_classification: "Zero-shot Classification",
  semantic_similarity: "Semantic Similarity",
  text_embeddings: "Text Embeddings",
};

export function TaskSelector({ value, onChange }: TaskSelectorProps) {
  const { data, isLoading } = useTasks();
  const registeredTasks = data?.tasks ?? [];

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
