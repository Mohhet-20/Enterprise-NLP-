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
