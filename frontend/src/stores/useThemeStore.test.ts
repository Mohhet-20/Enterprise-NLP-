import { beforeEach, describe, expect, it } from "vitest";
import { useThemeStore } from "@/stores/useThemeStore";

describe("useThemeStore", () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: "light" });
  });

  it("starts with the state it's initialized with", () => {
    expect(useThemeStore.getState().theme).toBe("light");
  });

  it("toggleTheme flips between light and dark", () => {
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("dark");

    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe("light");
  });

  it("setTheme sets an explicit value", () => {
    useThemeStore.getState().setTheme("dark");
    expect(useThemeStore.getState().theme).toBe("dark");
  });
});
