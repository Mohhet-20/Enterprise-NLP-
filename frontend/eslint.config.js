import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsparser,
      parserOptions: { ecmaFeatures: { jsx: true } },
      // Real fix for a real gap: the previous config declared no
      // environment globals at all, so eslint's no-undef rule flagged
      // legitimate browser globals (window, document, crypto) and React's
      // ambient JSX namespace as undefined — 38 false-positive errors,
      // caught only once lint was actually wired into CI as a blocking
      // gate rather than left unused.
      globals: { ...globals.browser, React: "readonly" },
    },
    plugins: { "@typescript-eslint": tseslint },
    rules: {
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-unused-vars": "off",
    },
  },
  {
    files: ["*.config.{js,ts}", "vite.config.ts", "tailwind.config.ts", "postcss.config.js"],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
  { ignores: ["dist/**", "node_modules/**", ".tsbuild/**"] },
];
