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
