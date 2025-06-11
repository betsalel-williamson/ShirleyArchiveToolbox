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
  // The 'server' block with proxy settings has been removed.
  // In our integrated SSR development setup, the Express server (server.ts)
  // handles all requests, including API calls. The Vite server runs in
  // middleware mode and does not need to proxy requests. This was causing
  // the ECONNREFUSED error.
  build: {
    minify: false,
  },
  test: vitestConfig.test,
});
