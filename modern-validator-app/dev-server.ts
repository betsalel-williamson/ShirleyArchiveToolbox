import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { createServer as createViteServer } from 'vite';

// DEV: Import directly from TypeScript source
import { setupDatabase } from './src/db';
import apiRouter from './src/api/api';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Constants
const port = process.env.PORT || 5173;
const base = process.env.BASE || '/';
const ABORT_DELAY = 10000;

async function createDevServer() {
  const app = express();

  // Set up the database
  await setupDatabase();

  // Create Vite server in middleware mode.
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'custom',
    base,
  });
  app.use(vite.middlewares);

  // Your specific middleware
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  app.use('/api', apiRouter);
  app.use('/static/images', express.static(path.join(__dirname, 'data', 'images')));

  // SSR logic
  app.use('*', async (req, res, next) => {
    // Pass to API routes if path matches
    if (req.originalUrl.startsWith('/api/') || req.originalUrl.startsWith('/static/')) {
      return next();
    }

    try {
      const url = req.originalUrl.replace(base, '');

      // Always read fresh template in development
      let template = await fs.readFile('./index.html', 'utf-8');
      template = await vite.transformIndexHtml(url, template);

      const { render } = await vite.ssrLoadModule('/src/entry-server.tsx');

      let didError = false;
      const { pipe, abort } = render(url, {
        onShellReady() {
          res.status(didError ? 500 : 200).setHeader('Content-type', 'text/html');
          const [htmlStart, htmlEnd] = template.split(`<!--app-html-->`);
          res.write(htmlStart);
          pipe(res);
        },
        onError(err) {
          didError = true;
          console.error(err);
        },
      });

      setTimeout(() => {
        abort();
      }, ABORT_DELAY);
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
