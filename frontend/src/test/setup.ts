import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement matchMedia — useThemeStore reads it at
// module-init time (system dark-mode detection), so any test importing
// that store needs this mock present before the import happens.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom doesn't implement ResizeObserver either — Recharts' ResponsiveContainer
// subscribes to one on mount. A no-op is enough: tests assert on data, not layout.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
