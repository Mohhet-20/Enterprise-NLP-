import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { InferenceRequest, InferenceResponse } from "@/types/api";

export function useInference() {
  return useMutation({
    mutationFn: (request: InferenceRequest) =>
      apiRequest<InferenceResponse>("/predict", { method: "POST", body: request }),
  });
}
