Of course! This is an excellent project. Converting a classic Flask server-rendered application to a modern full-stack architecture with Vite, React (with SSR), Express, and a SQL database is a great way to showcase modern development practices.

Here is a complete, ready-to-run project that mirrors the functionality of your Python Flask app.

### Key Architectural Changes

1. **Backend:** Express.js (TypeScript) replaces Flask.
2. **Frontend:** React (TypeScript) with Vite replaces Jinja2 templates.
3. **Rendering:** Server-Side Rendering (SSR) is implemented for fast initial page loads, as requested.
4. **Database:** A file-based SQLite database (managed by the Sequelize ORM) replaces the file system logic (`data_source`, `data_in_progress`, etc.). This is a more robust and scalable solution.
5. **Data Flow:**
    * The frontend (React) makes API calls to the backend (Express).
    * The backend queries the SQLite database.
    * For the initial page load, the server renders the React app to HTML and sends it, including the necessary data.
6. **Project Structure:** A monorepo-style structure with a `server` and `client` directory is used for clear separation of concerns.

---

### Generated Project Structure

Here's the new project structure. You can create these files and directories.

```
modern-validator-app/
├── client/                      # Vite + React Frontend
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── BoundingBox.tsx
│   │   │   └── Controls.tsx
│   │   ├── routes/
│   │   │   ├── IndexPage.tsx
│   │   │   └── ValidatePage.tsx
│   │   ├── App.tsx
│   │   ├── entry-client.tsx
│   │   ├── entry-server.tsx
│   │   ├── main.css
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── data/                        # Source data and images
│   ├── images/
│   │   └── sample_image_1.png
│   └── source_json/
│       └── doc1.json
├── server/                      # Express + Sequelize Backend
│   ├── src/
│   │   ├── api.ts
│   │   ├── database.ts
│   │   ├── models/Document.ts
│   │   └── seed.ts
│   ├── package.json
│   └── tsconfig.json
├── .gitignore
├── README.md
├── package.json
└── server.ts                    # Main SSR server entrypoint
```

---

### Step 1: Root Project Setup

Create the main project directory and the root `package.json`.

**`./package.json`**

```json
{
  "name": "modern-validator-app",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "node --loader ts-node/esm --experimental-specifier-resolution=node ./server.ts",
    "build": "npm run build --prefix client && npm run build --prefix server",
    "start": "NODE_ENV=production node ./server/dist/server.js",
    "seed": "node --loader ts-node/esm --experimental-specifier-resolution=node ./server/src/seed.ts"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sequelize": "^6.35.2",
    "sqlite3": "^5.1.7",
    "vite": "^5.0.10"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^20.10.6",
    "concurrently": "^8.2.2",
    "ts-node": "^10.9.2",
    "typescript": "^5.3.3"
  }
}
```

**`./.gitignore`**

```
# Dependencies
node_modules/
/client/node_modules/
/server/node_modules/

# Build artifacts
dist/
/client/dist/
/server/dist/

# Data and logs
*.sqlite
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
```

---

### Step 2: Sample Data

Create the `data` directory to hold the source files.

**`./data/source_json/doc1.json`**

```json
{
  "image_source": "sample_image_1.png",
  "image_dimensions": {
    "width": 800,
    "height": 600
  },
  "lines": [
    {
      "words": [
        { "text": "QUICK", "bounding_box": { "x_min": 50, "y_min": 100, "x_max": 150, "y_max": 130 } },
        { "text": "BROWN", "bounding_box": { "x_min": 160, "y_min": 100, "x_max": 260, "y_max": 130 } },
        { "text": "FOX", "bounding_box": { "x_min": 270, "y_min": 100, "x_max": 340, "y_max": 130 } }
      ]
    },
    {
      "words": [
        { "text": "JUMPS", "bounding_box": { "x_min": 70, "y_min": 150, "x_max": 170, "y_max": 180 } },
        { "text": "OVER", "bounding_box": { "x_min": 180, "y_min": 150, "x_max": 270, "y_max": 180 } }
      ]
    }
  ]
}
```

*You will also need to place an image file at `./data/images/sample_image_1.png`. You can use any placeholder image.*

---

### Step 3: Backend Server (Express + Sequelize)

**`./server/package.json`**

```json
{
  "name": "validator-server",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc"
  },
  "devDependencies": {
    "@types/node": "^20.10.6",
    "typescript": "^5.3.3"
  }
}
```

**`./server/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "node",
    "outDir": "dist",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"]
}
```

**`./server/src/database.ts`**

```typescript
// server/src/database.ts
import { Sequelize } from 'sequelize';
import path from 'path';
import { fileURLToPath } from 'url';

// Resolve __dirname for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: path.join(__dirname, '..', '..', 'database.sqlite'), // Store db in root
  logging: false, // Set to console.log to see SQL queries
});

export const connectDB = async () => {
  try {
    await sequelize.authenticate();
    console.log('Database connection has been established successfully.');
    // Sync all models
    await sequelize.sync({ alter: true });
    console.log("All models were synchronized successfully.");
  } catch (error) {
    console.error('Unable to connect to the database:', error);
  }
};
```

**`./server/src/models/Document.ts`**

```typescript
// server/src/models/Document.ts
import { DataTypes, Model, Optional } from 'sequelize';
import { sequelize } from '../database.js';

interface DocumentAttributes {
  id: number;
  filename: string;
  imageSource: string;
  status: 'source' | 'in_progress' | 'validated';
  sourceData: object;
  currentData: object;
}

interface DocumentCreationAttributes extends Optional<DocumentAttributes, 'id'> {}

class Document extends Model<DocumentAttributes, DocumentCreationAttributes> implements DocumentAttributes {
  public id!: number;
  public filename!: string;
  public imageSource!: string;
  public status!: 'source' | 'in_progress' | 'validated';
  public sourceData!: object;
  public currentData!: object;
}

Document.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    filename: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
    },
    imageSource: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('source', 'in_progress', 'validated'),
      defaultValue: 'source',
      allowNull: false,
    },
    sourceData: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    currentData: {
      type: DataTypes.JSON,
      allowNull: false,
    },
  },
  {
    sequelize,
    tableName: 'documents',
  }
);

export default Document;
```

**`./server/src/api.ts`** (Replaces `routes/api.py` and parts of `utils.py`)

```typescript
// server/src/api.ts
import express, { Request, Response } from 'express';
import Document from './models/Document.js';
import { applyTransformationsToData } from './utils.js';

const router = express.Router();

// GET /api/documents - List all documents (replaces Flask index())
router.get('/documents', async (req: Request, res: Response) => {
  try {
    const documents = await Document.findAll({
      attributes: ['id', 'filename', 'status'],
      order: [['filename', 'ASC']],
    });
    res.json(documents);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch documents' });
  }
});

// GET /api/documents/:id - Get a single document's data for validation (replaces Flask validate())
router.get('/documents/:id', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    res.json(document);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch document' });
  }
});

// GET /api/documents/:id/source - Get original source data (replaces Flask get_source_data())
router.get('/documents/:id/source', async (req: Request, res: Response) => {
    try {
        const document = await Document.findByPk(req.params.id, {
            attributes: ['sourceData'],
        });
        if (!document) {
            return res.status(404).json({ error: 'Document not found' });
        }
        res.json(document.sourceData);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch source data' });
    }
});


// POST /api/documents/:id/autosave - (replaces Flask autosave())
router.post('/documents/:id/autosave', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    const transformedData = applyTransformationsToData(req.body);

    document.currentData = transformedData;
    if (document.status === 'source') {
      document.status = 'in_progress';
    }
    await document.save();

    res.json({ status: 'ok', message: 'Draft saved.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to save draft' });
  }
});

// POST /api/documents/:id/commit - (replaces Flask commit())
router.post('/documents/:id/commit', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    const transformedData = applyTransformationsToData(req.body);
    transformedData.validated = true;

    document.currentData = transformedData;
    document.status = 'validated';
    await document.save();

    // Find the next document that is not validated
    const nextDocument = await Document.findOne({
        where: { status: { [Op.ne]: 'validated' } },
        order: [['filename', 'ASC']],
        attributes: ['id'],
    });

    res.json({ status: 'ok', message: 'Committed successfully.', nextDocumentId: nextDocument?.id || null });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to commit changes' });
  }
});

// POST /api/documents/:id/revert - New endpoint to handle reverting to source
router.post('/documents/:id/revert', async (req: Request, res: Response) => {
    try {
        const document = await Document.findByPk(req.params.id);
        if (!document) {
            return res.status(404).json({ error: 'Document not found' });
        }
        document.currentData = document.sourceData;
        document.status = 'in_progress'; // Reverting puts it back in progress
        await document.save();
        res.json({ status: 'ok', message: 'Reverted to source.', data: document.currentData });
    } catch (error) {
        res.status(500).json({ error: 'Failed to revert document' });
    }
});


export default router;
```

**`./server/src/utils.ts`** (A direct port of the Python transformation logic)

```typescript
// server/src/utils.ts
interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

interface Word {
  id: string;
  text: string;
  bounding_box: BoundingBox;
}

interface Line {
  words: Word[];
}

interface Data {
  image_dimensions: { width: number; height: number };
  lines: Line[];
  [key: string]: any; // Allow other properties
}

interface FormData {
  json_data: string;
  offsetX: string;
  offsetY: string;
  rotation: string;
  scale: string;
  [key: string]: string; // For text fields like text_line_word
}

export function applyTransformationsToData(formData: FormData): Data {
  const data: Data = JSON.parse(formData.json_data);

  const offsetX = parseFloat(formData.offsetX || '0');
  const offsetY = parseFloat(formData.offsetY || '0');
  const rotationDeg = parseFloat(formData.rotation || '0');
  const scale = parseFloat(formData.scale || '1.0');

  const isTransformed = offsetX !== 0 || offsetY !== 0 || rotationDeg !== 0 || scale !== 1.0;

  let cosRad = 1, sinRad = 0;
  const cx = (data.image_dimensions?.width || 0) / 2;
  const cy = (data.image_dimensions?.height || 0) / 2;

  if (isTransformed) {
    const rotationRad = (rotationDeg * Math.PI) / 180;
    cosRad = Math.cos(rotationRad);
    sinRad = Math.sin(rotationRad);
  }

  const allWords = new Map<string, Word>();
  data.lines?.forEach(line => {
    line.words?.forEach(word => {
      if (word.id) {
        allWords.set(word.id, word);
      }
    });
  });

  for (const key in formData) {
    if (key.startsWith('text_')) {
      const wordId = key.replace('text_', '');
      const word = allWords.get(wordId);
      if (word) {
        word.text = formData[key];
      }
    }
  }

  if (isTransformed) {
    for (const word of allWords.values()) {
      if (!word.bounding_box) continue;
      const bbox = word.bounding_box;
      const corners = [
        { x: bbox.x_min, y: bbox.y_min },
        { x: bbox.x_max, y: bbox.y_min },
        { x: bbox.x_max, y: bbox.y_max },
        { x: bbox.x_min, y: bbox.y_max },
      ];

      const transformedCorners = corners.map(({ x, y }) => {
        const xScaled = cx + (x - cx) * scale;
        const yScaled = cy + (y - cy) * scale;
        const xRot = cx + (xScaled - cx) * cosRad - (yScaled - cy) * sinRad;
        const yRot = cy + (xScaled - cx) * sinRad + (yScaled - cy) * cosRad;
        return { x: xRot + offsetX, y: yRot + offsetY };
      });

      word.bounding_box = {
        x_min: Math.round(Math.min(...transformedCorners.map(p => p.x))),
        y_min: Math.round(Math.min(...transformedCorners.map(p => p.y))),
        x_max: Math.round(Math.max(...transformedCorners.map(p => p.x))),
        y_max: Math.round(Math.max(...transformedCorners.map(p => p.y))),
      };
    }
  }
  return data;
}

```

**`./server/src/seed.ts`** (Crucial script to populate the DB from source files)

```typescript
// server/src/seed.ts
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { connectDB, sequelize } from './database.js';
import Document from './models/Document.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SOURCE_DATA_DIR = path.join(__dirname, '..', '..', 'data', 'source_json');

async function seedDatabase() {
  console.log('Connecting to database...');
  await connectDB();

  console.log('Clearing existing documents...');
  await Document.destroy({ where: {}, truncate: true });

  console.log(`Reading from ${SOURCE_DATA_DIR}...`);
  const files = await fs.readdir(SOURCE_DATA_DIR);
  const jsonFiles = files.filter(f => f.endsWith('.json'));

  if (jsonFiles.length === 0) {
    console.log('No JSON files found in source directory. Nothing to seed.');
    return;
  }

  for (const filename of jsonFiles) {
    console.log(`Processing ${filename}...`);
    const filePath = path.join(SOURCE_DATA_DIR, filename);
    const fileContent = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    // Add unique IDs to the data if they don't exist
    let wordCounter = 0;
    data.lines.forEach((line: any, line_idx: number) => {
        line.words.forEach((word: any, word_idx: number) => {
            word.id = `${line_idx}_${word_idx}`;
            word.display_id = ++wordCounter;
        });
    });

    await Document.create({
      filename,
      imageSource: data.image_source,
      status: 'source',
      sourceData: data,
      currentData: data, // Initially, current data is the same as source
    });
    console.log(`  - Seeded ${filename} into the database.`);
  }

  console.log('Database seeding complete!');
  await sequelize.close();
}

seedDatabase().catch(error => {
  console.error('Seeding failed:', error);
  process.exit(1);
});
```

---

### Step 4: SSR Server Entrypoint

This is the main server file that runs everything.

**`./server.ts`**

```typescript
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
```

---

### Step 5: Frontend Client (Vite + React)

**`./client/package.json`**

```json
{
  "name": "validator-client",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build --ssrManifest && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

**`./client/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // This is not needed in dev because server.ts proxies, but is good for `vite preview`
  server: {
    proxy: {
      '/api': 'http://localhost:5173',
      '/static': 'http://localhost:5173'
    }
  }
})
```

**`./client/tsconfig.json`** (Standard Vite TS config)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**`./client/index.html`** (SSR template)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React SSR Validator</title>
  </head>
  <body>
    <div id="root"><!--ssr-outlet--></div>
    <script type="module" src="/src/entry-client.tsx"></script>
  </body>
</html>
```

**`./client/src/main.css`** (Copied from your `style.css`)
*Just copy the entire content of `validator_app/static/css/style.css` into this file.*

**`./client/src/entry-client.tsx`**

```tsx
// client/src/entry-client.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { routes } from './App';
import './main.css';

const router = createBrowserRouter(routes);

ReactDOM.hydrateRoot(
  document.getElementById('root')!,
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
```

**`./client/src/entry-server.tsx`**

```tsx
// client/src/entry-server.tsx
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import {
  createStaticHandler,
  createStaticRouter,
  StaticRouterProvider,
} from 'react-router-dom/server';
import { routes } from './App';
import './main.css';

export async function render(url: string) {
  const { query, dataRoutes } = createStaticHandler(routes);
  const context = await query(new Request(`http://localhost:5173${url}`));

  if (context instanceof Response) {
    throw context;
  }

  const router = createStaticRouter(dataRoutes, context);

  const appHtml = ReactDOMServer.renderToString(
    <React.StrictMode>
      <StaticRouterProvider router={router} context={context} />
    </React.StrictMode>
  );

  return { appHtml, router };
}
```

**`./client/src/App.tsx`** (Defines routes)

```tsx
// client/src/App.tsx
import { Outlet } from 'react-router-dom';
import IndexPage, { loader as indexLoader } from './routes/IndexPage';
import ValidatePage, { loader as validateLoader, action as validateAction } from './routes/ValidatePage';

export const routes = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        loader: indexLoader,
        element: <IndexPage />,
      },
      {
        path: 'validate/:id',
        loader: validateLoader,
        action: validateAction,
        element: <ValidatePage />,
      }
    ],
  },
];

function Layout() {
  return (
    <div className="app-container">
      <Outlet />
    </div>
  );
}
```

**`./client/src/routes/IndexPage.tsx`**

```tsx
// client/src/routes/IndexPage.tsx
import { useLoaderData, Link } from 'react-router-dom';

export interface DocumentInfo {
  id: number;
  filename: string;
  status: 'source' | 'in_progress' | 'validated';
}

export async function loader() {
  const res = await fetch('http://localhost:5173/api/documents');
  if (!res.ok) throw new Error('Failed to fetch documents');
  const documents: DocumentInfo[] = await res.json();
  return documents;
}

export default function IndexPage() {
  const files = useLoaderData() as DocumentInfo[];

  return (
    <div className="container">
      <h1>Transcription Validation</h1>
      <p>Select a file to validate. Status will be shown.</p>
      <ul>
        {files.length > 0 ? (
          files.map(file => (
            <li key={file.id}>
              <Link to={`/validate/${file.id}`}>{file.filename}</Link>
              {file.status === 'validated' && <span className="validated-check">Validated ✓</span>}
              {file.status === 'in_progress' && <span className="status-progress">In Progress...</span>}
            </li>
          ))
        ) : (
          <li>No JSON files found in the database.</li>
        )}
      </ul>
    </div>
  );
}
```

**`./client/src/routes/ValidatePage.tsx`**
*This is the most complex component, porting all the client-side logic from your `validate.html` to React.*

```tsx
// client/src/routes/ValidatePage.tsx
// This is a large component due to the complex state management.
import React, { useState, useEffect, useRef, useReducer } from 'react';
import { useLoaderData, useFetcher, Link, useNavigate, useParams } from 'react-router-dom';
import { BoundingBox, Controls } from '../components'; // We'll create these small components

// --- Types ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[] } }
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
type TextState = { [key: string]: string };
type HistoryState = { transforms: TransformState; texts: TextState; };

// --- Loader & Action for react-router ---
export async function loader({ params }: { params: { id?: string } }) {
  const res = await fetch(`http://localhost:5173/api/documents/${params.id}`);
  if (!res.ok) {
    if (res.status === 404) return { status: 404, error: 'Document not found' };
    throw new Error('Failed to fetch validation data');
  }
  return res.json();
}

export async function action({ request, params }: { request: Request, params: { id?: string } }) {
    const formData = await request.formData();
    const actionType = formData.get('action');

    if (actionType === 'commit') {
        const res = await fetch(`http://localhost:5173/api/documents/${params.id}/commit`, {
            method: 'POST',
            body: formData,
        });
        return res.json();
    }
    // Handle other actions like autosave if needed (though we do it via fetcher)
    return { ok: false, error: 'Invalid action' };
}

// --- Main Component ---
export default function ValidatePage() {
    const initialData = useLoaderData() as DocumentData;
    const fetcher = useFetcher();
    const navigate = useNavigate();
    const { id } = useParams();

    // Flatten words for easier management
    const initialAnnotations = initialData.currentData.lines.flatMap(line => line.words);

    // --- State Management ---
    const [texts, setTexts] = useState<TextState>(() =>
        Object.fromEntries(initialAnnotations.map(word => [`text_${word.id}`, word.text]))
    );
    const [transforms, setTransforms] = useState<TransformState>({ offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 });
    const [history, dispatchHistory] = useReducer(historyReducer, { past: [], present: { transforms, texts }, future: [] });
    const [status, setStatus] = useState<{ msg: string, type: string }>({ msg: '', type: '' });

    // Refs for dragging logic
    const isDragging = useRef(false);
    const startPos = useRef({ x: 0, y: 0 });
    const overlayRef = useRef<HTMLDivElement>(null);

    // --- Effects ---

    // Debounced Autosave Effect
    useEffect(() => {
        const handler = setTimeout(() => {
            if (history.past.length > 0) { // Don't save on initial load
                autoSaveState();
            }
        }, 1500); // 1.5 second debounce
        return () => clearTimeout(handler);
    }, [history.present]);

    // Commit navigation effect
    useEffect(() => {
        if (fetcher.state === 'idle' && fetcher.data) {
            const { nextDocumentId } = fetcher.data as any;
            if (nextDocumentId) {
                navigate(`/validate/${nextDocumentId}`);
            } else {
                navigate('/');
            }
        }
    }, [fetcher.data, fetcher.state, navigate]);

    // Dragging effect
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            const newOffsetX = e.clientX - startPos.current.x;
            const newOffsetY = e.clientY - startPos.current.y;
            setTransforms(prev => ({ ...prev, offsetX: newOffsetX, offsetY: newOffsetY }));
        };
        const handleMouseUp = () => {
            if (!isDragging.current) return;
            isDragging.current = false;
            if (overlayRef.current) overlayRef.current.classList.remove('dragging');
            dispatchHistory({ type: 'SET', payload: { transforms, texts } }); // Push state on mouse up
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [transforms, texts]); // Depend on transforms and texts to capture the latest state

    // --- Handlers ---
    const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
        e.preventDefault();
        isDragging.current = true;
        startPos.current = {
            x: e.clientX - transforms.offsetX,
            y: e.clientY - transforms.offsetY,
        };
        if (overlayRef.current) overlayRef.current.classList.add('dragging');
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setTexts(prev => ({ ...prev, [name]: value }));
    };


    const handleTextBlur = () => {
        dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    };

    const handleTransformChange = (newTransforms: Partial<TransformState>) => {
        const updatedTransforms = { ...transforms, ...newTransforms };
        setTransforms(updatedTransforms);
    };

    const handleTransformCommit = () => {
        dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    };

    const autoSaveState = async () => {
        setStatus({ msg: 'Saving...', type: 'status-progress' });
        const formData = createFormData();

        try {
            const res = await fetch(`/api/documents/${id}/autosave`, { method: 'POST', body: formData });
            if (res.ok) {
                setStatus({ msg: 'Draft Saved ✓', type: 'status-validated' });
            } else {
                throw new Error('Save failed');
            }
        } catch (error) {
            setStatus({ msg: 'Save Failed!', type: 'status-error' });
        }
    };

    const handleRevert = async () => {
        if (!confirm('Are you sure you want to revert to the original source file?')) return;
        setStatus({ msg: 'Reverting...', type: 'status-progress' });
        try {
            const res = await fetch(`/api/documents/${id}/revert`, { method: 'POST' });
            if (!res.ok) throw new Error('Revert failed on server');
            const { data } = await res.json();

            const revertedAnnotations = data.lines.flatMap((line: any) => line.words);
            const revertedTexts = Object.fromEntries(revertedAnnotations.map((w: Word) => [`text_${w.id}`, w.text]));
            const revertedTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };

            setTexts(revertedTexts);
            setTransforms(revertedTransforms);
            dispatchHistory({ type: 'RESET', payload: { transforms: revertedTransforms, texts: revertedTexts } });
            setStatus({ msg: 'Reverted successfully. Saving...', type: 'status-validated' });
            // Trigger an immediate save of the reverted state
            const revertedFormData = new FormData();
            revertedFormData.append('json_data', JSON.stringify(data));
            Object.entries(revertedTransforms).forEach(([key, value]) => revertedFormData.append(key, String(value)));
            Object.entries(revertedTexts).forEach(([key, value]) => revertedFormData.append(key, value));
            await fetch(`/api/documents/${id}/autosave`, { method: 'POST', body: revertedFormData });
            setStatus({ msg: 'Reverted & Saved ✓', type: 'status-validated' });

        } catch (error) {
            setStatus({ msg: 'Revert Failed!', type: 'status-error' });
        }
    };

    const createFormData = () => {
        const formData = new FormData();
        formData.append('json_data', JSON.stringify(initialData.currentData));
        Object.entries(history.present.transforms).forEach(([key, value]) => formData.append(key, String(value)));
        Object.entries(history.present.texts).forEach(([key, value]) => formData.append(key, value));
        return formData;
    };

    if (initialData.error) {
        return <div className="container"><h2>{initialData.error}</h2><Link to="/">Back to List</Link></div>;
    }

    return (
        <div className="container validation-container">
            <div className="image-pane">
                <h2>{initialData.filename}</h2>
                <Controls
                    transforms={transforms}
                    onTransformChange={handleTransformChange}
                    onCommit={handleTransformCommit}
                    onUndo={() => dispatchHistory({ type: 'UNDO' })}
                    onRedo={() => dispatchHistory({ type: 'REDO' })}
                    onRevert={handleRevert}
                    canUndo={history.past.length > 0}
                    canRedo={history.future.length > 0}
                />
                <div className="image-wrapper">
                    <img src={`/static/images/${initialData.currentData.image_source}`} alt="Base" />
                    <div
                        id="bbox-overlay"
                        ref={overlayRef}
                        style={{ transform: `translate(${transforms.offsetX}px, ${transforms.offsetY}px) rotate(${transforms.rotation}deg) scale(${transforms.scale})`, transformOrigin: 'center center' }}
                        onMouseDown={handleMouseDown}
                    >
                        {initialAnnotations.map(word => (
                            <BoundingBox key={word.id} word={word} />
                        ))}
                    </div>
                </div>
            </div>
            <div className="form-pane">
                <h3>Word Transcriptions <span id="autosave-status" className={status.type}>{status.msg}</span></h3>
                <fetcher.Form method="post" onSubmit={(e) => {
                    const formData = createFormData();
                    formData.append('action', 'commit');
                    fetcher.submit(formData, { method: 'post' });
                    e.preventDefault();
                }}>
                    <div style={{ flexGrow: 1, overflowY: 'auto' }}>
                        {initialAnnotations.map(word => (
                            <div className="form-group" key={word.id}>
                                <label htmlFor={`text_${word.id}`}>Word {word.display_id}:</label>
                                <input
                                    type="text"
                                    id={`text_${word.id}`}
                                    name={`text_${word.id}`}
                                    value={texts[`text_${word.id}`] || ''}
                                    onChange={handleTextChange}
                                    onBlur={handleTextBlur}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="buttons">
                        <button type="submit" name="action" value="commit" className="approve-btn" disabled={fetcher.state !== 'idle'}>
                            {fetcher.state !== 'idle' ? 'Committing...' : 'Commit & Next'}
                        </button>
                    </div>
                </fetcher.Form>
                <Link to="/" className="back-link">← Back to List</Link>
            </div>
        </div>
    );
}

// --- Undo/Redo Reducer ---
type Action = { type: 'UNDO' } | { type: 'REDO' } | { type: 'SET', payload: HistoryState } | { type: 'RESET', payload: HistoryState };
interface State {
    past: HistoryState[];
    present: HistoryState;
    future: HistoryState[];
}

function historyReducer(state: State, action: Action): State {
    const { past, present, future } = state;
    switch (action.type) {
        case 'UNDO':
            if (past.length === 0) return state;
            const previous = past[past.length - 1];
            const newPast = past.slice(0, past.length - 1);
            return { past: newPast, present: previous, future: [present, ...future] };
        case 'REDO':
            if (future.length === 0) return state;
            const next = future[0];
            const newFuture = future.slice(1);
            return { past: [...past, present], present: next, future: newFuture };
        case 'SET':
            if (JSON.stringify(action.payload) === JSON.stringify(present)) return state;
            return { past: [...past, present], present: action.payload, future: [] };
        case 'RESET':
            return { past: [], present: action.payload, future: [] };
        default:
            return state;
    }
}
```

**`./client/src/components/BoundingBox.tsx`**

```tsx
// client/src/components/BoundingBox.tsx
import React from 'react';
interface Word { id: string; display_id: number; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; } }

export const BoundingBox: React.FC<{ word: Word }> = ({ word }) => {
    const { bounding_box: bbox, display_id } = word;
    return (
        <div
            className="bounding-box"
            style={{
                left: `${bbox.x_min}px`,
                top: `${bbox.y_min}px`,
                width: `${bbox.x_max - bbox.x_min}px`,
                height: `${bbox.y_max - bbox.y_min}px`,
            }}
        >
            <span className="box-label">{display_id}</span>
        </div>
    );
};
```

**`./client/src/components/Controls.tsx`**

```tsx
// client/src/components/Controls.tsx
import React from 'react';
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };

interface ControlsProps {
    transforms: TransformState;
    onTransformChange: (newTransforms: Partial<TransformState>) => void;
    onCommit: () => void;
    onUndo: () => void;
    onRedo: () => void;
    onRevert: () => void;
    canUndo: boolean;
    canRedo: boolean;
}

export const Controls: React.FC<ControlsProps> = ({
    transforms, onTransformChange, onCommit, onUndo, onRedo, onRevert, canUndo, canRedo
}) => {
    return (
        <div className="controls">
            <div className="control-group">
                <label>Rotate:</label>
                <input type="range" min="-45" max="45" value={transforms.rotation} step="0.1"
                    onChange={e => onTransformChange({ rotation: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.rotation.toFixed(1)} step="0.1"
                    onChange={e => onTransformChange({ rotation: parseFloat(e.target.value) })}
                    onBlur={onCommit}/>°
            </div>
            <div className="control-group">
                <label>Scale:</label>
                <input type="range" min="0.1" max="2.0" value={transforms.scale} step="0.01"
                    onChange={e => onTransformChange({ scale: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.scale.toFixed(2)} step="0.01"
                    onChange={e => onTransformChange({ scale: parseFloat(e.target.value) })}
                    onBlur={onCommit} />x
            </div>
            <div className="control-group">
                <label>Translate:</label>
                <input type="number" value={Math.round(transforms.offsetX)} placeholder="X"
                    onChange={e => onTransformChange({ offsetX: parseInt(e.target.value, 10) })}
                    onBlur={onCommit} />
                <input type="number" value={Math.round(transforms.offsetY)} placeholder="Y"
                    onChange={e => onTransformChange({ offsetY: parseInt(e.target.value, 10) })}
                    onBlur={onCommit} />px
            </div>
            <div className="control-group action-buttons">
                <button onClick={onUndo} className="secondary-btn" disabled={!canUndo}>Undo</button>
                <button onClick={onRedo} className="secondary-btn" disabled={!canRedo}>Redo</button>
                <button onClick={onRevert} className="danger-btn">Revert to Original</button>
            </div>
            <p>Then, click and drag the red boxes to align them.</p>
        </div>
    );
};
```

---

### Step 6: How to Run the Application

1. **Install Dependencies:**
    Open three terminals.
    * In the root (`modern-validator-app`): `npm install`
    * In `client`: `npm install`
    * In `server`: `npm install`

2. **Seed the Database:**
    In the root directory, run the seed script once to populate your database from the files in `./data/source_json/`.

    ```bash
    npm run seed
    ```

    This will create a `database.sqlite` file in the root directory.

3. **Start the Development Server:**
    In the root directory, run the main dev script. This single command starts the Vite dev server and the Express backend with SSR enabled.

    ```bash
    npm run dev
    ```

4. **Access the App:**
    Open your browser and navigate to **`http://localhost:5173`**.

You now have a fully functional, modern full-stack application that replicates and enhances the original Flask app's capabilities
