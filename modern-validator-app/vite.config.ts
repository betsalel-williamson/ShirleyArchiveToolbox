import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import type { UserConfig as VitestUserConfigInterface } from "vitest/config";

const vitestConfig: VitestUserConfigInterface = {
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["src/__tests__/setupTests.ts"],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API requests to the backend server
    proxy: {
      "/api": {
        target: "http://localhost:7456",
        changeOrigin: true,
      },
      "/public": {
        target: "http://localhost:7456",
        changeOrigin: true,
      }
    },
  },
  build: {
    minify: false,
  },
  test: vitestConfig.test,
});
