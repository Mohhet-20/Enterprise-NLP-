import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (className merge utility)", () => {
  it("merges multiple class strings", () => {
    expect(cn("px-2", "py-4")).toBe("px-2 py-4");
  });

  it("resolves conflicting Tailwind classes, keeping the last one", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("drops falsy values", () => {
    expect(cn("px-2", false, null, undefined, "py-4")).toBe("px-2 py-4");
  });

  it("applies conditional classes correctly", () => {
    const isActive = true;
    expect(cn("base", isActive && "active")).toBe("base active");
    expect(cn("base", !isActive && "active")).toBe("base");
  });
});
