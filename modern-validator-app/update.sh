#!/bin/bash

echo "🚀 Pivoting to a simpler Client-Side Rendering (CSR) data-fetching model..."

# --- 1. Simplify server/src/server.ts ---
# It no longer needs to know about data loaders.
echo "✅ 1/5: Simplifying server/src/server.ts..."
cat << 'EOF' > server/src/server.ts
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
EOF

# --- 2. Simplify client/src/entry-server.tsx ---
# It no longer needs to handle any data.
echo "✅ 2/5: Simplifying client/src/entry-server.tsx..."
cat << 'EOF' > client/src/entry-server.tsx
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
  const fetchRequest = new Request(`http://localhost:5173${url}`);
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

  return { appHtml };
}
EOF

# --- 3. Remove loaders from client/src/App.tsx ---
echo "✅ 3/5: Removing loaders from client/src/App.tsx..."
cat << 'EOF' > client/src/App.tsx
// client/src/App.tsx
import { Outlet } from 'react-router-dom';
import IndexPage from './routes/IndexPage';
import ValidatePage, { action as validateAction } from './routes/ValidatePage';

// We remove the `loader` prop entirely. Data fetching is now done inside the components.
export const routes = [
  {
    id: 'root',
    path: '/',
    element: <Layout />,
    children: [
      {
        id: 'index',
        index: true,
        element: <IndexPage />,
      },
      {
        id: 'validate',
        path: 'validate/:id',
        action: validateAction, // Actions still work perfectly!
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

# --- 4. Refactor client/src/routes/IndexPage.tsx for client-side fetching ---
echo "✅ 4/5: Refactoring client/src/routes/IndexPage.tsx..."
cat << 'EOF' > client/src/routes/IndexPage.tsx
// client/src/routes/IndexPage.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export interface DocumentInfo {
  id: number;
  filename: string;
  status: 'source' | 'in_progress' | 'validated';
}

export default function IndexPage() {
  const [files, setFiles] = useState<DocumentInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // This effect runs once when the component mounts in the browser.
    fetch('/api/documents')
      .then(res => {
        if (!res.ok) {
          throw new Error('Failed to fetch documents from server.');
        }
        return res.json();
      })
      .then(data => setFiles(data))
      .catch(err => {
        console.error(err);
        setError(err.message);
      });
  }, []); // The empty dependency array means it runs only once.

  if (error) {
    return <div className="container"><h1>Error</h1><p>{error}</p></div>;
  }

  if (files === null) {
    return <div className="container"><h1>Loading...</h1></div>;
  }

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
          <li>No JSON files found in the database. Run `pnpm run seed` to populate it.</li>
        )}
      </ul>
    </div>
  );
}
EOF

# --- 5. Refactor client/src/routes/ValidatePage.tsx for client-side fetching ---
echo "✅ 5/5: Refactoring client/src/routes/ValidatePage.tsx..."
# This is a big one. We replace the `useLoaderData` with a `useState`/`useEffect` pattern.
# First, let's back it up just in case.
cp client/src/routes/ValidatePage.tsx client/src/routes/ValidatePage.tsx.bak

cat << 'EOF' > client/src/routes/ValidatePage.tsx
// client/src/routes/ValidatePage.tsx
import React, { useState, useEffect, useRef, useReducer } from 'react';
import { useFetcher, Link, useNavigate, useParams } from 'react-router-dom';
import { BoundingBox } from '../components/BoundingBox';
import { Controls } from '../components/Controls';

// --- Types (remain the same) ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface CurrentData { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[]; [key: string]: any }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: CurrentData, error?: string, status?: number }
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
type TextState = { [key:string]: string };
type HistoryState = { transforms: TransformState; texts: TextState; };

// The action function is for form submissions and still works perfectly.
export async function action({ request, params }: { request: Request, params: { id?: string } }) {
    const formData = await request.formData();
    const res = await fetch(`/api/documents/${params.id}/commit`, {
        method: 'POST', body: formData,
    });
    return res.json();
}

// --- Main Component ---
export default function ValidatePage() {
    const { id } = useParams<{ id: string }>();
    const fetcher = useFetcher();
    const navigate = useNavigate();

    // --- NEW: State for holding data, loading, and errors ---
    const [documentData, setDocumentData] = useState<DocumentData | null>(null);
    const [error, setError] = useState<string | null>(null);

    // --- NEW: useEffect to fetch data on mount or when ID changes ---
    useEffect(() => {
        if (!id) return;
        setDocumentData(null); // Reset on ID change
        setError(null);

        fetch(`/api/documents/${id}`)
            .then(res => {
                if (!res.ok) throw new Error(`Failed to fetch document ${id}`);
                return res.json();
            })
            .then(data => setDocumentData(data))
            .catch(err => setError(err.message));
    }, [id]);

    const getInitialAnnotations = () => documentData?.currentData?.lines.flatMap(line => line.words) || [];

    // State management needs to be initialized safely
    const [texts, setTexts] = useState<TextState>({});
    const [transforms, setTransforms] = useState<TransformState>({ offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 });
    const [history, dispatchHistory] = useReducer(historyReducer, { past: [], present: { transforms, texts }, future: [] });
    const [status, setStatus] = useState<{ msg: string, type: string }>({ msg: '', type: '' });

    const isDragging = useRef(false);
    const startPos = useRef({ x: 0, y: 0 });
    const overlayRef = useRef<HTMLDivElement>(null);
    const initialDataRef = useRef(documentData?.currentData);

    // Effect to reset state when new data arrives
    useEffect(() => {
        if (!documentData || !documentData.currentData) return;
        initialDataRef.current = documentData.currentData;
        const newAnnotations = getInitialAnnotations();
        const newTexts = Object.fromEntries(newAnnotations.map(w => [`text_${w.id}`, w.text]));
        const newTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
        setTexts(newTexts);
        setTransforms(newTransforms);
        dispatchHistory({ type: 'RESET', payload: { transforms: newTransforms, texts: newTexts } });
        setStatus({ msg: '', type: '' });
    }, [documentData]);

    // ... (The rest of the effects and handlers are largely the same) ...
    // Debounced Autosave Effect
    useEffect(() => {
        if (!documentData) return; // Don't save if no data
        const handler = setTimeout(() => {
            if (history.past.length > 0) autoSaveState();
        }, 1500);
        return () => clearTimeout(handler);
    }, [history.present, documentData]);

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
            initialDataRef.current = data;
            const revertedAnnotations = data.lines.flatMap((line: any) => line.words);
            const revertedTexts = Object.fromEntries(revertedAnnotations.map((w: Word) => [`text_${w.id}`, w.text]));
            const revertedTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
            setTexts(revertedTexts);
            setTransforms(revertedTransforms);
            dispatchHistory({ type: 'RESET', payload: { transforms: revertedTransforms, texts: revertedTexts } });
            autoSaveState(data);
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

    if (error) return <div className="container"><h1>Error</h1><p>{error}</p></div>;
    if (!documentData) return <div className="container"><h1>Loading document...</h1></div>;

    const annotations = getInitialAnnotations();

    return (
        <div className="container validation-container">
            <div className="image-pane">
                <h2>{documentData.filename}</h2>
                <Controls {...{ transforms, onTransformChange: handleTransformChange, onCommit: handleTransformCommit,
                    onUndo: () => dispatchHistory({ type: 'UNDO' }), onRedo: () => dispatchHistory({ type: 'REDO' }), onRevert: handleRevert,
                    canUndo: history.past.length > 0, canRedo: history.future.length > 0 }} />
                <div className="image-wrapper">
                    <img src={`/static/images/${documentData.currentData.image_source}`} alt="Base" />
                    <div id="bbox-overlay" ref={overlayRef} onMouseDown={handleMouseDown}
                        style={{ transform: `translate(${transforms.offsetX}px, ${transforms.offsetY}px) rotate(${transforms.rotation}deg) scale(${transforms.scale})`, transformOrigin: 'center' }}>
                        {annotations.map(word => <BoundingBox key={word.id} word={word} />)}
                    </div>
                </div>
            </div>
            <div className="form-pane">
                <h3>Word Transcriptions <span id="autosave-status" className={status.type}>{status.msg}</span></h3>
                <fetcher.Form method="post" onSubmit={e => { fetcher.submit(createFormData(), { method: 'post' }); e.preventDefault(); }}>
                    <div className='form-scroll-area'>
                        {annotations.map(word => (
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

echo "🎉 All files updated for the new client-side data-fetching architecture!"
echo "➡️  Please restart your dev servers. The application should now work reliably."
echo "   - In one terminal: pnpm run dev:server"
echo "   - In another terminal: pnpm run dev:client"
