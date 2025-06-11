// server.ts
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import { createServer as createViteServer } from 'vite';

import { connectDB } from './server/src/database.js';
import apiRouter from './server/src/api.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function createServer() {
  const app = express();

  // Connect to Database
  await connectDB();

  // Create Vite server in development mode
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'custom',
    root: path.join(__dirname, 'client'), // Point to client directory
  });
  app.use(vite.middlewares);

  // Middleware
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // API routes
  app.use('/api', apiRouter);

  // Serve static images from the root data folder
  app.use('/static/images', express.static(path.join(__dirname, 'data', 'images')));

  // SSR logic
  app.use('*', async (req, res, next) => {
    const url = req.originalUrl;

    try {
      let template = await fs.readFile(path.join(__dirname, 'client/index.html'), 'utf-8');
      template = await vite.transformIndexHtml(url, template);

      const { render } = await vite.ssrLoadModule('/src/entry-server.tsx');

      const { appHtml, router } = await render(url);

      // On the server, we can check the loader data. If a loader returns a 404 response, we can use that status code.
      const loaderData = router.state.loaderData[router.state.location.pathname];
      if (loaderData && loaderData.status === 404) {
        res.status(404);
      }

      const html = template.replace(`<!--ssr-outlet-->`, appHtml);

      res.status(200).set({ 'Content-Type': 'text/html' }).end(html);
    } catch (e) {
      if (e instanceof Error) {
        vite.ssrFixStacktrace(e);
      }
      next(e);
    }
  });

  app.listen(5173, () => {
    console.log('Server running at http://localhost:5173');
  });
}

createServer();
