import { create } from "zustand";
import type { InferenceResponse } from "@/types/api";

export interface HistoryEntry {
  id: string;
  text: string;
  response: InferenceResponse;
  timestamp: number;
}

interface PredictionHistoryState {
  entries: HistoryEntry[];
  addEntry: (text: string, response: InferenceResponse) => void;
  clear: () => void;
}

export const usePredictionHistoryStore = create<PredictionHistoryState>((set) => ({
  entries: [],
  addEntry: (text, response) =>
    set((s) => ({
      entries: [
        { id: crypto.randomUUID(), text, response, timestamp: Date.now() },
        ...s.entries,
      ].slice(0, 25),
    })),
  clear: () => set({ entries: [] }),
}));
