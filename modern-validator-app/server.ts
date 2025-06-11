import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import compression from "compression";
import cors from "cors";
import { createServer as createViteServer } from "vite";
import apiRouter from "./src/server/api.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const isTest = process.env.NODE_ENV === "test";
const isProd = process.env.NODE_ENV === "production";

async function createServer() {
  const app = express();

  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: "custom",
    logLevel: isTest ? "error" : "info",
  });

  app.use(vite.middlewares);

  app.use(cors());
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // API routes
  app.use("/api", apiRouter);

  if (isProd) {
    app.use(compression());
    app.use(express.static(path.resolve(__dirname, "dist/client"), { index: false }));
  }

  // Serve static images from public directory
  app.use("/public", express.static(path.resolve(__dirname, "public")));

  app.use("*", async (req, res, next) => {
    const url = req.originalUrl;

    try {
      const template = await fs.readFile(
        isProd ? path.resolve(__dirname, "dist/client/index.html") : path.resolve(__dirname, "index.html"),
        "utf-8"
      );

      const transformedTemplate = await vite.transformIndexHtml(url, template);

      const { render } = await vite.ssrLoadModule(
        isProd
          ? "/dist/server/entry-server.js"
          : "/src/client/entry-server.tsx"
      );

      const appHtml = await render(url);

      const html = transformedTemplate.replace(`<!--app-html-->`, appHtml);

      res.status(200).set({ "Content-Type": "text/html" }).end(html);
    } catch (e) {
      if (e instanceof Error) {
        vite.ssrFixStacktrace(e);
        next(e);
      } else {
        next(new Error("Unknown error during SSR"));
      }
    }
  });

  const port = process.env.PORT || 7456;
  app.listen(Number(port), "0.0.0.0", () => {
    console.log(`✅ Server is listening on http://localhost:${port}`);
  });
}

// Create data directories on startup if they don't exist
const dataDirs = ['data_source', 'data_in_progress', 'data_validated'];
Promise.all(dataDirs.map(dir => fs.mkdir(dir, { recursive: true })))
  .then(() => {
    createServer();
  })
  .catch(err => {
    console.error("Failed to create data directories:", err);
    process.exit(1);
  });
