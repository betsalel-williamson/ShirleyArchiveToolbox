// server/src/server.ts
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import { createServer as createViteServer } from 'vite';

import { setupDatabase } from './db';
import apiRouter from './api';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MONOREPO_ROOT = path.join(__dirname, '..', '..');

async function createServer() {
  const app = express();

  await setupDatabase();

  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'custom',
    root: path.join(MONOREPO_ROOT, 'client'),
  });
  app.use(vite.middlewares);

  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  app.use('/api', apiRouter);
  app.use('/static/images', express.static(path.join(MONOREPO_ROOT, 'data', 'images')));

  app.use('*', async (req, res, next) => {
    const url = req.originalUrl;
    try {
      let template = await fs.readFile(path.join(MONOREPO_ROOT, 'client/index.html'), 'utf-8');
      template = await vite.transformIndexHtml(url, template);

      const { render } = await vite.ssrLoadModule('/src/entry-server.tsx');
      // We no longer pass any data. The server just renders the shell.
      const { appHtml } = await render(url);

      const html = template.replace(`<!--ssr-outlet-->`, appHtml);

      res.status(200).set({ 'Content-Type': 'text/html' }).end(html);
    } catch (e) {
      if (e instanceof Error) vite.ssrFixStacktrace(e);
      next(e);
    }
  });

  app.listen(5173, () => {
    console.log('Server running at http://localhost:5173');
  });
}

createServer();
