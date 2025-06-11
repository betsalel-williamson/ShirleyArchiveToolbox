# Script to create the modern-validator-app project structure and files

# --- Create Root Directory ---
mkdir modern-validator-app
cd modern-validator-app

echo "Creating project structure inside 'modern-validator-app/'..."

# --- Create Root Files ---

# .gitignore
cat << 'EOF' > .gitignore
# Dependencies
/node_modules
/client/node_modules
/server/node_modules

# Build artifacts
/dist
/client/dist
/server/dist

# Data and logs
*.sqlite
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*
EOF

# README.md
cat << 'EOF' > README.md
# Modern Full-Stack Validator App

This is a modern full-stack application built with Vite, React, SSR, Express, and Sequelize (SQLite). It's a conversion from an original Python Flask application.

## Project Structure

- **`/`**: Root of the project, contains the main server entrypoint (`server.ts`) and configs.
- **`/client`**: The Vite + React frontend application.
- **`/server`**: The Express.js backend API and database logic.
- **`/data`**: Contains the initial source JSON files and images.

## How to Run

1.  **Install All Dependencies:**
    - `npm install` (in the root directory)
    - `cd client && npm install && cd ..`
    - `cd server && npm install && cd ..`

2.  **Seed the Database:**
    Run this command from the root directory to populate the SQLite database from the files in `/data/source_json`.
    \`\`\`bash
    npm run seed
    \`\`\`

3.  **Start the Development Server:**
    Run this command from the root directory. It will start the backend and the Vite server with SSR.
    \`\`\`bash
    npm run dev
    \`\`\`

4.  **Access the App:**
    Open your browser and navigate to `http://localhost:5173`.
EOF

# Root package.json
cat << 'EOF' > package.json
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
EOF

# server.ts
cat << 'EOF' > server.ts
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
EOF

# --- Create Data Directory ---
mkdir -p data/images data/source_json

# data/source_json/doc1.json
cat << 'EOF' > data/source_json/doc1.json
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
EOF
# Note: Create a placeholder image.
# On macOS/Linux you can use:
command -v convert >/dev/null 2>&1 && convert -size 800x600 xc:lightgray -pointsize 72 -gravity center -draw "text 0,0 'Sample Image'" data/images/sample_image_1.png
# If you don't have ImageMagick, this will fail silently. A manual step is needed.
if [ ! -f data/images/sample_image_1.png ]; then
    echo "NOTE: Please place an image at 'data/images/sample_image_1.png'"
fi

# --- Create Server Directory ---
mkdir -p server/src/models

# server/package.json
cat << 'EOF' > server/package.json
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
EOF

# server/tsconfig.json
cat << 'EOF' > server/tsconfig.json
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
EOF

# server/src/database.ts
cat << 'EOF' > server/src/database.ts
// server/src/database.ts
import { Sequelize, Op } from 'sequelize';
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

// Export Op for use in queries
export { Op };
EOF

# server/src/models/Document.ts
cat << 'EOF' > server/src/models/Document.ts
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
EOF

# server/src/api.ts
cat << 'EOF' > server/src/api.ts
// server/src/api.ts
import express, { Request, Response } from 'express';
import Document from './models/Document.js';
import { applyTransformationsToData } from './utils.js';
import { Op } from './database.js';

const router = express.Router();

// GET /api/documents - List all documents
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

// GET /api/documents/:id - Get a single document's data for validation
router.get('/documents/:id', async (req: Request, res: Response) => {
  try {
    const document = await Document.findByPk(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found', status: 404 });
    }
    res.json(document);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch document' });
  }
});

// GET /api/documents/:id/source - Get original source data
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

// POST /api/documents/:id/autosave
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

// POST /api/documents/:id/commit
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

// POST /api/documents/:id/revert
router.post('/documents/:id/revert', async (req: Request, res: Response) => {
    try {
        const document = await Document.findByPk(req.params.id);
        if (!document) {
            return res.status(404).json({ error: 'Document not found' });
        }
        document.currentData = document.sourceData;
        if (document.status === 'validated') {
          document.status = 'in_progress';
        }
        await document.save();
        res.json({ status: 'ok', message: 'Reverted to source.', data: document.currentData });
    } catch (error) {
        res.status(500).json({ error: 'Failed to revert document' });
    }
});

export default router;
EOF

# server/src/utils.ts
cat << 'EOF' > server/src/utils.ts
interface BoundingBox {
  x_min: number; y_min: number; x_max: number; y_max: number;
}
interface Word {
  id: string; text: string; bounding_box: BoundingBox;
}
interface Line { words: Word[]; }
interface Data {
  image_dimensions: { width: number; height: number }; lines: Line[]; [key: string]: any;
}
interface FormData {
  json_data: string; offsetX: string; offsetY: string; rotation: string; scale: string; [key: string]: string;
}

export function applyTransformationsToData(formData: any): Data {
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
      if (word.id) allWords.set(word.id, word);
    });
  });

  for (const key in formData) {
    if (key.startsWith('text_')) {
      const wordId = key.replace('text_', '');
      const word = allWords.get(wordId);
      if (word) word.text = formData[key];
    }
  }

  if (isTransformed) {
    for (const word of allWords.values()) {
      if (!word.bounding_box) continue;
      const bbox = word.bounding_box;
      const corners = [
        { x: bbox.x_min, y: bbox.y_min }, { x: bbox.x_max, y: bbox.y_min },
        { x: bbox.x_max, y: bbox.y_max }, { x: bbox.x_min, y: bbox.y_max },
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
EOF


# server/src/seed.ts
cat << 'EOF' > server/src/seed.ts
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

    // Add unique IDs to the data
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
      currentData: data,
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
EOF

# --- Create Client Directory ---
mkdir -p client/public client/src/components client/src/routes

# client/package.json
cat << 'EOF' > client/package.json
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
EOF

# client/tsconfig.json
cat << 'EOF' > client/tsconfig.json
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
EOF

# client/tsconfig.node.json (Needed by Vite)
cat << 'EOF' > client/tsconfig.node.json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
EOF


# client/vite.config.ts
cat << 'EOF' > client/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5173',
      '/static': 'http://localhost:5173'
    }
  }
})
EOF

# client/index.html
cat << 'EOF' > client/index.html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React SSR Validator</title>
  </head>
  <body>
    <div id="root"><!--ssr-outlet--></div>
    <script type="module" src="/src/entry-client.tsx"></script>
  </body>
</html>
EOF

# client/src/main.css
cat << 'EOF' > client/src/main.css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f4f4f9;
  color: #333;
  margin: 0;
  padding: 0;
}
.container {
  max-width: 1200px;
  margin: 20px auto;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgb(0 0 0 / 10%);
}
h1, h2, h3 { color: #0056b3; }
ul { list-style-type: none; padding: 0; }
li { padding: 10px; border-bottom: 1px solid #eee; }
li a { text-decoration: none; color: #007bff; font-weight: bold; }
li a:hover { text-decoration: underline; }
.validated-check, .status-validated { color: #28a745; font-weight: bold; margin-left: 10px; }
.status-progress { color: #ffc107; margin-left: 10px; }
.status-error { color: #dc3545; margin-left: 10px; }

.validation-container {
  display: flex; gap: 30px; height: calc(100vh - 40px);
  max-height: calc(100vh - 40px); box-sizing: border-box;
}
.image-pane { flex: 2; overflow: auto; display: flex; flex-direction: column; }
.image-pane img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }
.form-pane { flex: 1; display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.form-pane h3 { flex-shrink: 0; }
.form-pane form, .form-pane .form-scroll-area { flex-grow: 1; overflow-y: auto; padding-right: 15px; }

.form-group { margin-bottom: 15px; }
.form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
.form-group input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
.buttons { margin-top: 20px; display: flex; gap: 10px; }
button { padding: 10px 15px; border: none; border-radius: 4px; color: white; background-color: #007bff; cursor: pointer; font-size: 16px; }
button:hover { background-color: #0056b3; }
button:disabled { background-color: #c0c4c8; cursor: not-allowed; }
.approve-btn { background-color: #28a745; }
.approve-btn:hover { background-color: #218838; }
.back-link { display: inline-block; margin-top: 20px; }
.image-wrapper { position: relative; display: inline-block; overflow: hidden; margin-top: 15px; }
.image-wrapper img { display: block; }
#bbox-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; cursor: grab; }
#bbox-overlay.dragging { cursor: grabbing; }
.bounding-box { position: absolute; box-sizing: border-box; border: 2px solid red; background-color: rgb(255 0 0 / 10%); }
.box-label { position: absolute; top: -18px; left: 0; background-color: red; color: white; font-size: 12px; padding: 1px 4px; border-radius: 3px; font-weight: bold; }
.controls { background-color: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px; margin-bottom: 15px; }
.control-group { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.control-group label { font-weight: bold; width: 60px; flex-shrink: 0; }
.control-group input[type="range"] { flex-grow: 1; }
.control-group input[type="number"] { width: 80px; }
.control-group.action-buttons { margin-top: 15px; border-top: 1px solid #ddd; padding-top: 15px; }
.secondary-btn { background-color: #6c757d; padding: 8px 12px; font-size: 14px; }
.secondary-btn:hover { background-color: #5a6268; }
.danger-btn { background-color: #dc3545; padding: 8px 12px; font-size: 14px; }
.danger-btn:hover { background-color: #c82333; }
EOF

# client/src/vite-env.d.ts
cat << 'EOF' > client/src/vite-env.d.ts
/// <reference types="vite/client" />
EOF

# client/src/entry-client.tsx
cat << 'EOF' > client/src/entry-client.tsx
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
EOF

# client/src/entry-server.tsx
cat << 'EOF' > client/src/entry-server.tsx
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
  const fetchRequest = new Request(`http://localhost:5173${url}`);
  const { query, dataRoutes } = createStaticHandler(routes);
  const context = await query(fetchRequest);

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
EOF

# client/src/App.tsx
cat << 'EOF' > client/src/App.tsx
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
    <div className="app-layout">
      <Outlet />
    </div>
  );
}
EOF

# client/src/routes/IndexPage.tsx
cat << 'EOF' > client/src/routes/IndexPage.tsx
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
          <li>No JSON files found in the database. Run `npm run seed` to populate it.</li>
        )}
      </ul>
    </div>
  );
}
EOF

# client/src/routes/ValidatePage.tsx
cat << 'EOF' > client/src/routes/ValidatePage.tsx
import React, { useState, useEffect, useRef, useReducer } from 'react';
import { useLoaderData, useFetcher, Link, useNavigate, useParams } from 'react-router-dom';
import { BoundingBox } from '../components/BoundingBox';
import { Controls } from '../components/Controls';

// --- Types ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface CurrentData { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[]; [key: string]: any }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: CurrentData, error?: string, status?: number }
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
type TextState = { [key: string]: string };
type HistoryState = { transforms: TransformState; texts: TextState; };

// --- Loader & Action for react-router ---
export async function loader({ params }: { params: { id?: string } }) {
  const res = await fetch(`http://localhost:5173/api/documents/${params.id}`);
  return res.json();
}
export async function action({ request, params }: { request: Request, params: { id?: string } }) {
    const formData = await request.formData();
    const res = await fetch(`http://localhost:5173/api/documents/${params.id}/commit`, {
        method: 'POST', body: formData,
    });
    return res.json();
}

// --- Main Component ---
export default function ValidatePage() {
    const initialData = useLoaderData() as DocumentData;
    const fetcher = useFetcher();
    const navigate = useNavigate();
    const { id } = useParams();

    const getInitialAnnotations = () => initialData.currentData?.lines.flatMap(line => line.words) || [];

    // --- State Management ---
    const [texts, setTexts] = useState<TextState>(() => Object.fromEntries(getInitialAnnotations().map(w => [`text_${w.id}`, w.text])));
    const [transforms, setTransforms] = useState<TransformState>({ offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 });
    const [history, dispatchHistory] = useReducer(historyReducer, { past: [], present: { transforms, texts }, future: [] });
    const [status, setStatus] = useState<{ msg: string, type: string }>({ msg: '', type: '' });

    // Refs
    const isDragging = useRef(false);
    const startPos = useRef({ x: 0, y: 0 });
    const overlayRef = useRef<HTMLDivElement>(null);
    const initialDataRef = useRef(initialData.currentData);

    // --- Effects ---
    // Reset state when navigating to a new document
    useEffect(() => {
        initialDataRef.current = initialData.currentData;
        const newAnnotations = getInitialAnnotations();
        const newTexts = Object.fromEntries(newAnnotations.map(w => [`text_${w.id}`, w.text]));
        const newTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
        setTexts(newTexts);
        setTransforms(newTransforms);
        dispatchHistory({ type: 'RESET', payload: { transforms: newTransforms, texts: newTexts } });
        setStatus({ msg: '', type: '' });
    }, [id, initialData]);

    // Debounced Autosave Effect
    useEffect(() => {
        const handler = setTimeout(() => {
            if (history.past.length > 0) autoSaveState();
        }, 1500);
        return () => clearTimeout(handler);
    }, [history.present]);

    // Commit navigation effect
    useEffect(() => {
        if (fetcher.state === 'idle' && fetcher.data) {
            const { nextDocumentId } = fetcher.data as any;
            if (nextDocumentId) navigate(`/validate/${nextDocumentId}`);
            else navigate('/');
        }
    }, [fetcher.data, fetcher.state, navigate]);

    // Dragging effect
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            setTransforms(prev => ({ ...prev, offsetX: e.clientX - startPos.current.x, offsetY: e.clientY - startPos.current.y }));
        };
        const handleMouseUp = () => {
            if (!isDragging.current) return;
            isDragging.current = false;
            overlayRef.current?.classList.remove('dragging');
            dispatchHistory({ type: 'SET', payload: { transforms, texts } });
        };
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [transforms, texts]);

    // --- Handlers ---
    const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
        e.preventDefault();
        isDragging.current = true;
        startPos.current = { x: e.clientX - transforms.offsetX, y: e.clientY - transforms.offsetY };
        overlayRef.current?.classList.add('dragging');
    };
    const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => setTexts(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const handleTextBlur = () => dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    const handleTransformChange = (newT: Partial<TransformState>) => setTransforms({ ...transforms, ...newT });
    const handleTransformCommit = () => dispatchHistory({ type: 'SET', payload: { transforms, texts } });

    const handleRevert = async () => {
        if (!confirm('Revert to original? This will overwrite your current draft.')) return;
        setStatus({ msg: 'Reverting...', type: 'status-progress' });
        try {
            const res = await fetch(`/api/documents/${id}/revert`, { method: 'POST' });
            const { data } = await res.json();
            initialDataRef.current = data; // Update the base data
            const revertedAnnotations = data.lines.flatMap((line: any) => line.words);
            const revertedTexts = Object.fromEntries(revertedAnnotations.map((w: Word) => [`text_${w.id}`, w.text]));
            const revertedTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
            setTexts(revertedTexts);
            setTransforms(revertedTransforms);
            dispatchHistory({ type: 'RESET', payload: { transforms: revertedTransforms, texts: revertedTexts } });
            autoSaveState(data); // Immediately save the reverted state
        } catch (error) { setStatus({ msg: 'Revert Failed!', type: 'status-error' }); }
    };

    const createFormData = (baseData?: CurrentData) => {
        const formData = new FormData();
        formData.append('json_data', JSON.stringify(baseData || initialDataRef.current));
        Object.entries(history.present.transforms).forEach(([k, v]) => formData.append(k, String(v)));
        Object.entries(history.present.texts).forEach(([k, v]) => formData.append(k, v));
        return formData;
    };

    const autoSaveState = async (baseData?: CurrentData) => {
        setStatus({ msg: 'Saving...', type: 'status-progress' });
        try {
            const res = await fetch(`/api/documents/${id}/autosave`, { method: 'POST', body: createFormData(baseData) });
            if (res.ok) setStatus({ msg: 'Draft Saved ✓', type: 'status-validated' });
            else throw new Error('Save failed');
        } catch (error) { setStatus({ msg: 'Save Failed!', type: 'status-error' }); }
    };

    if (initialData.status === 404) {
        return <div className="container"><h2>{initialData.error}</h2><Link to="/">Back to List</Link></div>;
    }

    return (
        <div className="container validation-container">
            <div className="image-pane">
                <h2>{initialData.filename}</h2>
                <Controls {...{ transforms, onTransformChange: handleTransformChange, onCommit: handleTransformCommit,
                    onUndo: () => dispatchHistory({ type: 'UNDO' }), onRedo: () => dispatchHistory({ type: 'REDO' }), onRevert: handleRevert,
                    canUndo: history.past.length > 0, canRedo: history.future.length > 0 }} />
                <div className="image-wrapper">
                    <img src={`/static/images/${initialData.currentData.image_source}`} alt="Base" />
                    <div id="bbox-overlay" ref={overlayRef} onMouseDown={handleMouseDown}
                        style={{ transform: `translate(${transforms.offsetX}px, ${transforms.offsetY}px) rotate(${transforms.rotation}deg) scale(${transforms.scale})`, transformOrigin: 'center' }}>
                        {getInitialAnnotations().map(word => <BoundingBox key={word.id} word={word} />)}
                    </div>
                </div>
            </div>
            <div className="form-pane">
                <h3>Word Transcriptions <span id="autosave-status" className={status.type}>{status.msg}</span></h3>
                <fetcher.Form method="post" onSubmit={e => { fetcher.submit(createFormData(), { method: 'post' }); e.preventDefault(); }}>
                    <div className='form-scroll-area'>
                        {getInitialAnnotations().map(word => (
                            <div className="form-group" key={word.id}>
                                <label htmlFor={`text_${word.id}`}>Word {word.display_id}:</label>
                                <input id={`text_${word.id}`} name={`text_${word.id}`} value={texts[`text_${word.id}`] || ''}
                                    onChange={handleTextChange} onBlur={handleTextBlur} />
                            </div>
                        ))}
                    </div>
                    <div className="buttons">
                        <button type="submit" className="approve-btn" disabled={fetcher.state !== 'idle'}>
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
interface State { past: HistoryState[]; present: HistoryState; future: HistoryState[]; }
function historyReducer(state: State, action: Action): State {
    const { past, present, future } = state;
    switch (action.type) {
        case 'UNDO': {
            if (past.length === 0) return state;
            const previous = past[past.length - 1];
            return { past: past.slice(0, past.length - 1), present: previous, future: [present, ...future] };
        }
        case 'REDO': {
            if (future.length === 0) return state;
            const next = future[0];
            return { past: [...past, present], present: next, future: future.slice(1) };
        }
        case 'SET':
            if (JSON.stringify(action.payload) === JSON.stringify(present)) return state;
            return { past: [...past, present], present: action.payload, future: [] };
        case 'RESET':
            return { past: [], present: action.payload, future: [] };
    }
}
EOF

# client/src/components/BoundingBox.tsx
cat << 'EOF' > client/src/components/BoundingBox.tsx
import React from 'react';
interface Word { id: string; display_id: number; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; } }

export const BoundingBox: React.FC<{ word: Word }> = ({ word }) => {
    const { bounding_box: bbox, display_id } = word;
    return (
        <div
            className="bounding-box"
            style={{
                left: `${bbox.x_min}px`, top: `${bbox.y_min}px`,
                width: `${bbox.x_max - bbox.x_min}px`, height: `${bbox.y_max - bbox.y_min}px`,
            }}
        >
            <span className="box-label">{display_id}</span>
        </div>
    );
};
EOF

# client/src/components/Controls.tsx
cat << 'EOF' > client/src/components/Controls.tsx
import React from 'react';
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
interface ControlsProps {
    transforms: TransformState;
    onTransformChange: (newTransforms: Partial<TransformState>) => void;
    onCommit: () => void; onUndo: () => void; onRedo: () => void; onRevert: () => void;
    canUndo: boolean; canRedo: boolean;
}

export const Controls: React.FC<ControlsProps> = ({
    transforms, onTransformChange, onCommit, onUndo, onRedo, onRevert, canUndo, canRedo
}) => {
    const handleNumChange = (key: keyof TransformState, value: string) => {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) onTransformChange({ [key]: numValue });
    };
    return (
        <div className="controls">
            <div className="control-group">
                <label>Rotate:</label>
                <input type="range" min="-45" max="45" value={transforms.rotation} step="0.1"
                    onChange={e => onTransformChange({ rotation: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.rotation.toFixed(1)} step="0.1"
                    onChange={e => handleNumChange('rotation', e.target.value)} onBlur={onCommit}/>°
            </div>
            <div className="control-group">
                <label>Scale:</label>
                <input type="range" min="0.1" max="2.0" value={transforms.scale} step="0.01"
                    onChange={e => onTransformChange({ scale: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.scale.toFixed(2)} step="0.01"
                    onChange={e => handleNumChange('scale', e.target.value)} onBlur={onCommit} />x
            </div>
            <div className="control-group">
                <label>Translate:</label>
                <input type="number" value={Math.round(transforms.offsetX)} placeholder="X"
                    onChange={e => handleNumChange('offsetX', e.target.value)} onBlur={onCommit} />
                <input type="number" value={Math.round(transforms.offsetY)} placeholder="Y"
                    onChange={e => handleNumChange('offsetY', e.target.value)} onBlur={onCommit} />px
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
EOF


echo "✅ Project 'modern-validator-app' created successfully."
echo "➡️  Next steps:"
echo "1. cd modern-validator-app"
echo "2. npm install"
echo "3. (cd client && npm install)"
echo "4. (cd server && npm install)"
echo "5. npm run seed"
echo "6. npm run dev"