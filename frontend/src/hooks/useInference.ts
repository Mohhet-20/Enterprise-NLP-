import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type {
  BatchInferenceRequest,
  BatchInferenceResponse,
  ExplainRequest,
  ExplainResponse,
  InferenceRequest,
  InferenceResponse,
} from "@/types/api";

export function useInference() {
  return useMutation({
    mutationFn: (request: InferenceRequest) =>
      apiRequest<InferenceResponse>("/predict", { method: "POST", body: request }),
  });
}

export function useBatchInference() {
  return useMutation({
    mutationFn: (request: BatchInferenceRequest) =>
      apiRequest<BatchInferenceResponse>("/predict/batch", { method: "POST", body: request }),
  });
}

export function useExplain() {
  return useMutation({
    mutationFn: (request: ExplainRequest) =>
      apiRequest<ExplainResponse>("/explain", { method: "POST", body: request }),
  });
}
