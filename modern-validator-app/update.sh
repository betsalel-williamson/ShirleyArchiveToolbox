#!/bin/bash

echo "🚀 Upgrading code to match new package versions (React Router v6, Redux Thunk)..."
git add -A && git commit -m "pre-v6-api-upgrade" || echo "No changes to commit, proceeding."

# --- 1. Fix Redux Thunk import in the store ---
echo "✅ 1/6: Fixing Redux Thunk import..."
cat << 'EOF' > src/store/createStore.ts
import { createStore, applyMiddleware, Store } from 'redux';
import { thunk } from 'redux-thunk'; // Use named import
import rootReducer from '../client/reducers';

export default (): Store => {
  const store = createStore(rootReducer, {}, applyMiddleware(thunk));
  return store;
};
EOF

# --- 2. Fix Webpack's module resolution ---
echo "✅ 2/6: Fixing Webpack module resolution..."
cat << 'EOF' > webpack.config.js
'use strict';
const path = require('path');
const TerserPlugin = require("terser-webpack-plugin");
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const devMode = process.env.NODE_ENV !== 'production';

module.exports = {
  devtool: devMode ? 'source-map' : false,
  mode: devMode ? 'development' : 'production',
  entry: {
    'app': './src/client/client.tsx',
    'app.min': './src/client/client.tsx'
  },
  output: {
    path: path.resolve(__dirname, './dist/js'),
    filename: '[name].js'
  },
  resolve: {
    // THIS IS THE FIX: Tell Webpack to try these extensions when resolving modules
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.scss'],
    alias: {
      '@/components': path.resolve(__dirname, './src/client/components'),
      '@/views': path.resolve(__dirname, './src/client/views'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    }
  },
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({ test: /\.min\.js$/i }),
      new MiniCssExtractPlugin({ filename: '../css/[name].css' }),
      new CssMinimizerPlugin({ test: /\.min\.css$/i }),
    ],
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.(sa|sc|c)ss$/,
        use: [
          MiniCssExtractPlugin.loader,
          { loader: "css-loader", options: { sourceMap: true } },
          { loader: 'sass-loader', options: { sourceMap: true } },
        ]
      },
      {
        test: /\.(png|jpe?g|gif|ttf|eot|svg|woff(2)?)(\?[a-z0-9=&.]+)?$/,
        loader: 'file-loader',
        options: {
          outputPath: '../images/',
          name: '[name].[ext]'
        }
      }
    ],
  },
  plugins: [
    new CleanWebpackPlugin({
      cleanOnceBeforeBuildPatterns: [
          path.join(__dirname, 'dist/js/*'),
          path.join(__dirname, 'dist/css/*')
      ],
    }),
  ]
};
EOF

# --- 3. Remove obsolete react-router-config ---
echo "✅ 3/6: Removing obsolete router files..."
rm -f src/client/router/RoutesConfig.ts
rm -f src/client/router/App.js # This logic moves into App.tsx
rm -f src/client/router/index.js # This logic moves into client.tsx

# --- 4. Refactor client entry point ---
echo "✅ 4/6: Refactoring src/client/client.tsx..."
cat << 'EOF' > src/client/client.tsx
import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import createNewStore from '../store/createStore';
import App from './views/App';
import './index.scss';

// Grab the initial state from a global variable injected into the server-rendered HTML
const preloadedState = window.__PRELOADED_STATE__;
delete window.__PRELOADED_STATE__;

const store = createNewStore();

ReactDOM.hydrate(
  <Provider store={store}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Provider>,
  document.querySelector('#app')
);

declare global {
  interface Window {
    __PRELOADED_STATE__?: any;
  }
}
EOF

# --- 5. Refactor main App component with React Router v6 ---
echo "✅ 5/6: Refactoring src/client/views/App.tsx with modern React Router v6..."
cat << 'EOF' > src/client/views/App.tsx
import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import IndexPage from './IndexPage';
import ValidatePage from './ValidatePage';

const App = () => {
    return (
        <div>
            <nav>
                <ul>
                    <li>
                        <NavLink to="/" className={({ isActive }) => isActive ? "active" : ""}>Home</NavLink>
                    </li>
                    {/* Other main navigation links can go here */}
                </ul>
            </nav>

            <Routes>
                <Route path="/" element={<IndexPage />} />
                <Route path="/validate/:id" element={<ValidatePage />} />
                {/* <Route path="*" element={<NotFoundPage />} /> */}
            </Routes>
        </div>
    );
};

export default App;
EOF

# --- 6. Refactor server-side rendering logic for React Router v6 ---
echo "✅ 6/6: Updating server renderer for React Router v6..."
cat << 'EOF' > src/server/renderer.tsx
import React from 'react';
import { renderToString } from 'react-dom/server';
import { Provider } from 'react-redux';
import { StaticRouter } from 'react-router-dom/server';
import App from '../client/views/App';
import { Store } from 'redux';

export default (pathname: string, store: Store, context: object, template: string) => {
    const content = renderToString(
        <Provider store={store}>
            <StaticRouter location={pathname}>
                <App />
            </StaticRouter>
        </Provider>
    );

    // Replace placeholders in the HTML template
    if (template) {
        return template
            .replace('<!--app-html-->', content)
            .replace('"{{preloadedState}}"', JSON.stringify(store.getState()).replace(/</g, '\\u003c'));
    }
    return 'Error: HTML template not found.';
};
EOF
cat << 'EOF' > src/server/app.ts
import express from 'express';
import { matchPath } from 'react-router-dom';
import compression from 'compression';
import fs from 'fs';
import path from 'path';
import cors from 'cors';

import render from './renderer';
import createNewStore from '../store/createStore';
import apiRouter from './api';
import RoutesConfig from '../client/router/LegacyRoutes'; // We'll create a temp legacy config for data fetching

const port = process.env.PORT || 3000;
const app = express();

app.use(compression());
app.use(cors({ origin: '*' }));
app.use(express.static('public'));
app.use(express.static('dist'));

app.use('/api', apiRouter);
app.use('/static/images', express.static(path.resolve(__dirname, '../../data/images')));

app.get('*', (req, res) => {
    const store = createNewStore();

    // Find matching routes to trigger data fetching
    const matchedRoute = RoutesConfig.find(route => matchPath(req.path, route));
    const promises = matchedRoute && (matchedRoute.component as any).appSyncRequestFetching
        ? (matchedRoute.component as any).appSyncRequestFetching({ ...store, path: req.path })
        : [];

    Promise.all(promises.filter(Boolean)).then(() => {
        const indexFile = path.resolve('./public/index.html');
        fs.readFile(indexFile, 'utf8', (err, template) => {
            if (err) {
                console.error('HTML template read error:', err);
                return res.status(500).send('Oops, something went wrong.');
            }
            const context: { notFound?: boolean } = {};
            const content = render(req.path, store, context, template);

            if (context.notFound) {
                res.status(404);
            }
            res.send(content);
        });
    }).catch(e => {
        console.error("Data fetching error:", e);
        res.status(500).send("Error fetching data for SSR.");
    });
});

app.listen(port, () => {
    console.log(`✅ Server is running on port ${port}`);
});
EOF

# Create a temporary legacy routes file just for the server's data fetching logic
cat << 'EOF' > src/client/router/LegacyRoutes.ts
import IndexPage from '../views/IndexPage';
import ValidatePage from '../views/ValidatePage';

// This file is ONLY used by the server to identify which data to fetch.
// It is NOT used for client-side routing.
const LegacyRoutes = [
    {
      path: "/",
      component: IndexPage,
      exact: true
    },
    {
      path: "/validate/:id",
      component: ValidatePage,
    }
];
export default LegacyRoutes;
EOF


echo
echo "🎉 Project successfully upgraded to modern APIs!"
echo
echo "➡️  Run 'pnpm run build' to confirm the fixes, then 'pnpm run dev' to start."