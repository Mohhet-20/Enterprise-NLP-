import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
  build: {
    rollupOptions: {
      output: {
        // Function form: Vite 8 (rolldown) no longer accepts the object form.
        manualChunks(id: string) {
          const path = id.split("\\").join("/");
          const inPkg = (...names: string[]) => names.some((n) => path.includes(`/node_modules/${n}/`));
          if (inPkg("recharts", "victory-vendor") || path.includes("/node_modules/d3-")) return "charts";
          if (inPkg("framer-motion", "motion-dom", "motion-utils")) return "motion";
          if (inPkg("react", "react-dom", "react-router", "react-router-dom", "scheduler")) return "vendor";
          return undefined;
        },
      },
    },
  },
});
