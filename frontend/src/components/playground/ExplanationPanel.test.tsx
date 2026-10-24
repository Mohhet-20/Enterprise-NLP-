import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExplanationPanel, normaliseAttributions } from "@/components/playground/ExplanationPanel";
import { parseBatchInput } from "@/components/playground/BatchPanel";
import { parseLabels } from "@/pages/PlaygroundPage";
import type { ExplainResponse } from "@/types/api";

const explanation: ExplainResponse = {
  task: "sentiment_analysis",
  model_name: "distilbert-sst2",
  method: "integrated_gradients",
  label: "NEGATIVE",
  target_score: 0.98,
  baseline_score: 0.41,
  convergence_delta: 0.0031,
  attributions: [
    { token: "the", importance: 0.01 },
    { token: "acting", importance: 0.04 },
    { token: "was", importance: -0.02 },
    { token: "terrible", importance: 0.52 },
  ],
  latency_ms: 210,
};

describe("normaliseAttributions", () => {
  it("scales by the largest magnitude, keeping sign", () => {
    expect(normaliseAttributions([0.5, -1, 0.25])).toEqual([0.5, -1, 0.25]);
    expect(normaliseAttributions([2, -1])).toEqual([1, -0.5]);
  });

  it("does not divide by zero on all-zero input", () => {
    expect(normaliseAttributions([0, 0])).toEqual([0, 0]);
  });
});

describe("ExplanationPanel", () => {
  it("renders every word of the input in order", () => {
    render(<ExplanationPanel explanation={explanation} />);
    expect(screen.getByTestId("attribution-text").textContent?.replace(/\s+/g, " ").trim()).toBe(
      "the acting was terrible",
    );
  });

  it("ranks the most influential word first", () => {
    render(<ExplanationPanel explanation={explanation} />);
    const ranked = screen.getAllByText(/^[+-]\d\.\d{3}$/);
    expect(ranked[0].textContent).toBe("+0.520");
  });

  it("surfaces the completeness check", () => {
    render(<ExplanationPanel explanation={explanation} />);
    expect(screen.getByText(/within 0\.0031/)).toBeInTheDocument();
  });
});

describe("input parsing", () => {
  it("splits batch input on lines and drops blanks", () => {
    expect(parseBatchInput("a\n\n  b  \n")).toEqual(["a", "b"]);
  });

  it("splits zero-shot labels on commas and trims", () => {
    expect(parseLabels(" billing, shipping ,, refund ")).toEqual(["billing", "shipping", "refund"]);
  });
});
