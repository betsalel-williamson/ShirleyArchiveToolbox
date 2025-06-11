import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { createServer as createViteServer } from 'vite';

import { setupDatabase } from './src/db';
import apiRouter from './src/api/api';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = 5173;

async function createDevServer() {
  const app = express();
  await setupDatabase();

  const vite = await createViteServer({
    server: { middlewareMode: true, hmr: { port } },
    appType: 'custom',
  });
  app.use(vite.middlewares);

  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  app.use('/api', apiRouter);
  app.use('/static/images', express.static(path.join(__dirname, 'data', 'images')));

  app.use('*', async (req, res, next) => {
    if (req.originalUrl.startsWith('/api/') || req.originalUrl.startsWith('/static/')) {
      return next();
    }
    try {
      const url = req.originalUrl;
      let template = await fs.readFile('./index.html', 'utf-8');
      template = await vite.transformIndexHtml(url, template);
      const { render } = await vite.ssrLoadModule('/src/entry-server.tsx');

      const { pipe } = render(url, {
        onShellReady() {
          res.status(200).setHeader('Content-type', 'text/html');
          const [htmlStart, htmlEnd] = template.split(`<!--app-html-->`);
          res.write(htmlStart);
          pipe(res);
        },
        onError(err) {
          console.error(err);
        },
      });
    } catch (e) {
      vite?.ssrFixStacktrace(e as Error);
      console.error(e);
      res.status(500).end((e as Error).stack);
    }
  });

  app.listen(port, () => {
    console.log(`✅ Development server started at http://localhost:${port}`);
  });
}

createDevServer();
