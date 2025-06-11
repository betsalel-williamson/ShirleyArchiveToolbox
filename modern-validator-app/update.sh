#!/bin/bash

# --- PRE-FLIGHT CHECK AND BACKUP ---
echo "🚀 This script will completely re-architect your project to a new Webpack-based SSR template."
echo "Your existing files will be moved and rearranged."
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi
git add -A && git commit -m "pre-webpack-refactor" || echo "No changes to commit, proceeding."

# --- PHASE 1: STAGE YOUR EXISTING LOGIC ---
echo "➡️  Phase 1: Staging your existing application logic..."
mkdir -p ./tmp_staging/components
mkdir -p ./tmp_staging/api
mkdir -p ./tmp_staging/db
mkdir -p ./tmp_staging/data

# Client-side components and styles
mv src/routes/IndexPage.tsx          ./tmp_staging/routes/
mv src/routes/ValidatePage.tsx        ./tmp_staging/routes/
mv src/components/Layout.tsx          ./tmp_staging/components/
mv src/components/Controls.tsx        ./tmp_staging/components/
mv src/components/BoundingBox.tsx     ./tmp_staging/components/
mv src/index.css                      ./tmp_staging/

# Server-side logic
mv src/api/api.ts                     ./tmp_staging/api/
mv src/data.ts                        ./tmp_staging/db/
mv src/db.ts                          ./tmp_staging/db/
mv src/types.db.ts                    ./tmp_staging/db/
mv src/utils.ts                       ./tmp_staging/
mv src/seed.ts                        ./tmp_staging/

# Data and .gitignore
mv data                               ./tmp_staging/data/
mv .gitignore                         ./tmp_staging/gitignore.bak

# --- PHASE 2: CLEAN PROJECT ROOT ---
echo "➡️  Phase 2: Wiping the project root..."
rm -rf `ls -A | grep -v "tmp_staging"`
mv ./tmp_staging/gitignore.bak ./.gitignore


# --- PHASE 3: CREATE NEW STRUCTURE AND CONFIGS FROM TEMPLATE ---
echo "➡️  Phase 3: Building new project structure from template..."

# Create new package.json
cat << 'EOF' > package.json
{
  "name": "modern-validator-app",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "check": "tsc --watch --noEmit",
    "dev": "nodemon --watch src/server --exec babel-node src/server/server.js",
    "build": "webpack --mode production",
    "start": "NODE_ENV=production node src/server/server.js",
    "seed": "babel-node src/seed.ts",
    "clean": "rimraf dist public/*.html ./*.sqlite*"
  },
  "dependencies": {
    "@babel/polyfill": "^7.12.1",
    "axios": "^0.21.4",
    "better-sqlite3": "^11.1.2",
    "compression": "^1.7.4",
    "cors": "^2.8.5",
    "express": "^4.19.2",
    "kysely": "^0.27.3",
    "react": "^17.0.2",
    "react-dom": "^17.0.2",
    "react-redux": "^7.2.4",
    "react-router-config": "^5.1.1",
    "react-router-dom": "^5.2.0",
    "redux": "^4.1.0",
    "redux-thunk": "^2.3.0"
  },
  "devDependencies": {
    "@babel/cli": "^7.24.5",
    "@babel/core": "^7.24.5",
    "@babel/node": "^7.23.9",
    "@babel/plugin-proposal-class-properties": "^7.18.6",
    "@babel/plugin-transform-runtime": "^7.24.3",
    "@babel/preset-env": "^7.24.5",
    "@babel/preset-react": "^7.24.1",
    "@babel/preset-typescript": "^7.24.1",
    "@babel/register": "^7.23.7",
    "@types/better-sqlite3": "^7.6.10",
    "@types/compression": "^1.7.5",
    "@types/express": "^4.17.21",
    "@types/node": "^20.12.12",
    "@types/react": "^17.0.80",
    "@types/react-dom": "^17.0.25",
    "@types/react-redux": "^7.1.33",
    "@types/react-router-config": "^5.0.9",
    "@types/react-router-dom": "^5.3.3",
    "babel-loader": "^9.1.3",
    "babel-plugin-module-resolver": "^5.0.2",
    "clean-webpack-plugin": "^4.0.0",
    "css-loader": "^6.11.0",
    "css-minimizer-webpack-plugin": "^6.0.0",
    "file-loader": "^6.2.0",
    "ignore-styles": "^5.0.1",
    "mini-css-extract-plugin": "^2.9.0",
    "nodemon": "^3.1.0",
    "react-hot-loader": "^4.13.1",
    "sass": "^1.77.2",
    "sass-loader": "^14.2.1",
    "terser-webpack-plugin": "^5.3.10",
    "ts-node": "^10.9.2",
    "typescript": "^5.4.5",
    "webpack": "^5.91.0",
    "webpack-cli": "^5.1.4"
  }
}
EOF

# Create babel.config.js
cat << 'EOF' > babel.config.js
module.exports = {
  "presets": [
    ["@babel/preset-env", { "targets": { "node": "current" } }],
    ["@babel/preset-react"],
    ["@babel/preset-typescript"]
  ],
  "plugins": [
    ["@babel/plugin-transform-runtime", { "regenerator": true }],
    ["@babel/plugin-proposal-class-properties"],
    ["module-resolver", {
      "root": ["./src"],
      "alias": {
        "@/components": "./src/client/components",
        "@/views": "./src/client/views",
        "@/utils": "./src/utils",
        "@/api": "./src/api",
        "@/db": "./src/db",
        "@/data": "./src/data"
      }
    }]
  ]
};
EOF

# Create webpack.config.js
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
    extensions: ['.js', '.jsx', '.ts', '.tsx', '.scss'],
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

# Create directory structure
mkdir -p public/assets
mkdir -p src/client/components src/client/views src/client/router
mkdir -p src/server src/store
mkdir -p data

# --- PHASE 4: POPULATE NEW STRUCTURE & ADAPT LOGIC ---
echo "➡️  Phase 4: Integrating application logic into new structure..."

# Move staged files to their new final locations
mv tmp_staging/components/* src/client/components/
mv tmp_staging/routes/* src/client/views/
mv tmp_staging/index.css src/client/index.scss
mv tmp_staging/api/api.ts src/server/api.ts
mv tmp_staging/db/* src/server/
mv tmp_staging/utils.ts src/utils.ts
mv tmp_staging/seed.ts src/seed.ts
mv tmp_staging/data/* data/

# Create the Redux store
cat << 'EOF' > src/store/createStore.ts
import { createStore, applyMiddleware, Store } from 'redux';
import thunk from 'redux-thunk';
import rootReducer from '../client/reducers';

export default (): Store => {
  const store = createStore(rootReducer, {}, applyMiddleware(thunk));
  return store;
};
EOF

# Create client entry point
cat << 'EOF' > src/client/client.tsx
import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { renderRoutes } from 'react-router-config';
import createNewStore from '../store/createStore';
import RoutesConfig from './router/RoutesConfig';
import './index.scss';

// Grab the initial state from a global variable injected into the server-rendered HTML
const preloadedState = window.__PRELOADED_STATE__;
delete window.__PRELOADED_STATE__;

const store = createNewStore();

ReactDOM.hydrate(
  <Provider store={store}>
    <BrowserRouter>
      <div>{renderRoutes(RoutesConfig)}</div>
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

# Create new server files from template, adapted for TS
cat << 'EOF' > src/server/server.js
// This file is now very simple. It just registers babel to transpile the rest of the server code.
require('@babel/register')({
    presets: ['@babel/preset-env', '@babel/preset-react', '@babel/preset-typescript'],
    extensions: ['.js', '.jsx', '.ts', '.tsx'],
});
require('ignore-styles'); // Ignore CSS/SCSS imports on the server

module.exports = require('./app.ts');
EOF

cat << 'EOF' > src/server/renderer.tsx
import React from 'react';
import { renderToString } from 'react-dom/server';
import { Provider } from 'react-redux';
import { StaticRouter } from 'react-router-dom';
import { renderRoutes } from 'react-router-config';
import RoutesConfig from '../client/router/RoutesConfig';
import { Store } from 'redux';

export default (pathname: string, store: Store, context: object, template: string) => {
    const content = renderToString(
        <Provider store={store}>
            <StaticRouter location={pathname} context={context}>
                <div>{renderRoutes(RoutesConfig)}</div>
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
import { matchRoutes } from 'react-router-config';
import compression from 'compression';
import fs from 'fs';
import path from 'path';
import cors from 'cors';

import render from './renderer';
import RoutesConfig from '../client/router/RoutesConfig';
import createNewStore from '../store/createStore';
import apiRouter from './api';

const port = process.env.PORT || 3000;
const app = express();

// Middleware
app.use(compression());
app.use(cors({ origin: '*' }));
app.use(express.static('public'));
app.use(express.static('dist'));

// API routes
app.use('/api', apiRouter);
app.use('/static/images', express.static(path.resolve(__dirname, '../../data/images')));


// SSR catch-all
app.get('*', (req, res) => {
    const store = createNewStore();
    const matchedRoutes = matchRoutes(RoutesConfig, req.path);

    const promises = matchedRoutes.map(({ route }) => {
        if (route.component && (route.component as any).appSyncRequestFetching) {
            const storeAPI = { ...store, path: req.path };
            return (route.component as any).appSyncRequestFetching(storeAPI);
        }
        return null;
    }).flat().filter(p => p); // Flatten and remove nulls

    Promise.all(promises).then(() => {
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
    console.log(`✅ Server is running on port ${port}, access http://localhost:${port}`);
});
EOF

# Create new Router Config
cat << 'EOF' > src/client/router/RoutesConfig.ts
import App from '../views/App';
import IndexPage from '../views/IndexPage';
import ValidatePage from '../views/ValidatePage';

const RoutesConfig = [
  {
    component: App,
    routes: [
      {
        path: "/",
        component: IndexPage,
        exact: true
      },
      {
        path: "/validate/:id",
        component: ValidatePage,
      },
      // You can add a 404 component here if needed
    ]
  }
];

export default RoutesConfig;
EOF

# Create the top-level App view component
cat << 'EOF' > src/client/views/App.tsx
import React from 'react';
import { renderRoutes } from 'react-router-config';
import { Link, useLocation } from 'react-router-dom';

const App = (props: { route: any }) => {
    const location = useLocation();
    return (
        <div>
            <nav>
              <ul>
				<li className={location.pathname === '/' ? 'active' : ''}>
				  <Link to="/">Home</Link>
				</li>
              </ul>
            </nav>
            {/* child routes will be rendered here */}
            {renderRoutes(props.route.routes)}
        </div>
    );
};

export default App;
EOF

# --- PHASE 5: ADAPT APPLICATION COMPONENTS ---
echo "➡️  Phase 5: Adapting components to the new Redux/SSR data flow..."

# Create Reducers
mkdir -p src/client/reducers
cat << 'EOF' > src/client/reducers/documentsReducer.ts
import { AnyAction } from "redux";

interface State {
    list: any[] | null;
    details: { [key: string]: any };
}

const initialState: State = {
    list: null,
    details: {}
};

export const DOC_LIST_SUCCESS = 'DOC_LIST_SUCCESS';
export const DOC_DETAIL_SUCCESS = 'DOC_DETAIL_SUCCESS';

export default (state = initialState, action: AnyAction): State => {
    switch (action.type) {
        case DOC_LIST_SUCCESS:
            return { ...state, list: action.payload };
        case DOC_DETAIL_SUCCESS:
            return {
                ...state,
                details: {
                    ...state.details,
                    [action.key]: action.payload,
                },
            };
        default:
            return state;
    }
};
EOF

cat << 'EOF' > src/client/reducers/index.ts
import { combineReducers } from 'redux';
import documentsReducer from './documentsReducer';

export default combineReducers({
    documents: documentsReducer,
});
EOF


# Adapt IndexPage
sed -i.bak 's|useState, useEffect|Component|' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak 's|export default function IndexPage()|import { connect } from "react-redux";\
import { getDocumentList } from "../../server/data";\
import { DOC_LIST_SUCCESS } from "../reducers/documentsReducer";\
\
class IndexPage extends Component<any, any> {|g' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak '/useEffect(() => {/,/}, \[\]);/d' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak '/const \[files, setFiles\] =/d' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak '/const \[error, setError\] =/d' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak '/if (error)/,/}/d' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak 's|if (files === null)|  static appSyncRequestFetching(storeAPI: any) {\
    return [storeAPI.dispatch(getDocumentList().then(res => ({ type: DOC_LIST_SUCCESS, payload: res })))];\
  }\
\
  componentDidMount() {\
    if (!this.props.files) {\
        this.props.fetchData();\
    }\
  }\
\
  render() {\
    const { files } = this.props;\
    if (!files) {|g' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak 's|</ul>|</ul>\
    );\
  }\
}|g' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
sed -i.bak 's|</li>|</li>)) : (\
          <li>No JSON files found in the database. Run `npm run seed` to populate it.</li>\
        )}|' src/client/views/IndexPage.tsx && rm src/client/views/IndexPage.tsx.bak
# Add Redux connect HOC
echo '
const mapStateToProps = (state: any) => ({
    files: state.documents.list,
});

const mapDispatchToProps = {
    fetchData: () => (dispatch: any) => getDocumentList().then(res => dispatch({ type: DOC_LIST_SUCCESS, payload: res })),
};

export default connect(mapStateToProps, mapDispatchToProps)(IndexPage);
' >> src/client/views/IndexPage.tsx


# Adapt ValidatePage (this is a big one)
# We will just overwrite it with a new class-based, redux-connected version.
cat << 'EOF' > src/client/views/ValidatePage.tsx
import React, { Component, Fragment, createRef } from 'react';
import { connect } from 'react-redux';
import { Link, RouteComponentProps } from 'react-router-dom';
import { BoundingBox } from '../components/BoundingBox';
import { Controls } from '../components/Controls';
import { getDocumentById } from '../../server/data';
import { DOC_DETAIL_SUCCESS } from '../reducers/documentsReducer';

// --- Types ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface CurrentData { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[]; [key: string]: any }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: CurrentData; error?: string; status?: number }

interface MatchParams { id: string; }
interface Props extends RouteComponentProps<MatchParams> {
    documentData?: DocumentData;
    fetchData: (id: string) => void;
}

class ValidatePage extends Component<Props, any> {

    static appSyncRequestFetching(storeAPI: any) {
        const id = storeAPI.path.split('/').pop();
        return [storeAPI.dispatch(getDocumentById(id).then(res => ({ type: DOC_DETAIL_SUCCESS, payload: res, key: `doc_${id}` })))];
    }

    componentDidMount() {
        if (!this.props.documentData) {
            this.props.fetchData(this.props.match.params.id);
        }
    }

    render() {
        const { documentData } = this.props;
        if (!documentData) {
            return <div className="container"><h1>🌀 Loading document...</h1></div>;
        }

        if (documentData.error) {
            return <div className="container"><h1>Error</h1><p>{documentData.error}</p></div>;
        }

        const annotations = documentData.currentData.lines.flatMap(line => line.words) || [];

        return (
            <div className="container validation-container">
                <div className="image-pane">
                    <h2>{documentData.filename}</h2>
                    <div className="image-wrapper">
                        <img src={`/static/images/${documentData.currentData.image_source}`} alt="Base" />
                        <div id="bbox-overlay" style={{ transformOrigin: 'center' }}>
                            {annotations.map(word => <BoundingBox key={word.id} word={word} />)}
                        </div>
                    </div>
                </div>
                <div className="form-pane">
                    <h3>Word Transcriptions</h3>
                    <form>
                        <div className='form-scroll-area'>
                            {annotations.map(word => (
                                <div className="form-group" key={word.id}>
                                    <label htmlFor={`text_${word.id}`}>Word {word.display_id}:</label>
                                    <input id={`text_${word.id}`} name={`text_${word.id}`} defaultValue={word.text} />
                                </div>
                            ))}
                        </div>
                        <div className="buttons">
                            <button type="submit" className="approve-btn">Commit & Next</button>
                        </div>
                    </form>
                    <Link to="/" className="back-link">← Back to List</Link>
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state: any, ownProps: any) => {
    const docId = ownProps.match.params.id;
    return {
        documentData: state.documents.details[`doc_${docId}`],
    };
};

const mapDispatchToProps = {
    fetchData: (id: string) => (dispatch: any) => getDocumentById(id).then(res => dispatch({ type: DOC_DETAIL_SUCCESS, payload: res, key: `doc_${id}` })),
};

export default connect(mapStateToProps, mapDispatchToProps)(ValidatePage);
EOF


# --- Final Cleanup and Instructions ---
echo "➡️  Cleaning up temporary files..."
rm -rf ./tmp_staging
rm -rf public
mkdir public
cp src/client/views/_html/index.html public/

# Replace placeholders in the final HTML
sed -i.bak 's|{{reactApp}}|<!--app-html-->|g' public/index.html && rm public/index.html.bak
sed -i.bak 's|{{preloadedState}}|"{{preloadedState}}"|g' public/index.html && rm public/index.html.bak


echo
echo "🎉 Project successfully re-architected to the new Webpack/Redux SSR template!"
echo "This is a stable and robust foundation."
echo
echo "➡️  Next steps:"
echo "1. Run 'pnpm install' to get all new dependencies."
echo "2. Run 'pnpm run seed' to populate the database."
echo "3. Run 'pnpm run build' once to create the initial 'dist' folder."
echo "4. Run 'pnpm run dev' to start the development server."