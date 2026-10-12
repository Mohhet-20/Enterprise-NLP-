import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceChip } from "@/components/playground/ConfidenceChip";

describe("ConfidenceChip", () => {
  it("renders the label text", () => {
    render(<ConfidenceChip label="POSITIVE" score={0.87} />);
    expect(screen.getByText("POSITIVE")).toBeInTheDocument();
  });

  it("renders the score as a rounded percentage", () => {
    render(<ConfidenceChip label="POSITIVE" score={0.874} />);
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("rounds correctly at the boundary", () => {
    render(<ConfidenceChip label="NEGATIVE" score={0.995} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("sets the CSS custom property driving the confidence fill", () => {
    const { container } = render(<ConfidenceChip label="POSITIVE" score={0.6} />);
    const chip = container.querySelector(".confidence-chip") as HTMLElement;
    expect(chip.style.getPropertyValue("--fill")).toBe("60%");
  });
});
